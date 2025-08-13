import argparse
import json
import queue
import threading
import time
from urllib.parse import urlparse

import pika

from src.scraper import Scraper
from src.utils import log_statistics, save_to_csv

# Default output file name for scraped emails
OUTPUT_FILENAME = "scraped_emails.csv"

DLSU_DOMAINS = ["dlsu.edu.ph"]
URL_QUEUE = "url_queue"
RESULT_QUEUE = "result_queue"


def is_dlsu_url(url):
    try:
        netloc = urlparse(url).netloc.lower()
        return any(domain in netloc for domain in DLSU_DOMAINS)
    except Exception:
        return False


class Master:
    def __init__(self, seed_urls, port=5000, time_limit_minutes=1, urls_per_batch=5):
        self.seed_urls = [u for u in seed_urls if is_dlsu_url(u)]
        self.port = port
        self.time_limit = time_limit_minutes * 60  # store as seconds internally
        self.url_queue = queue.Queue()
        self.urls_per_batch = urls_per_batch  # URLs to assign per worker batch
        for url in self.seed_urls:
            self.url_queue.put(url)
        self.visited = set()
        self.results = []
        self.lock = threading.Lock()
        self.urls_provessed = 0
        self.start_time = None
        self.scraper = Scraper()
        self.running = True
        self.active_workers = 0
        self.worker_stats = {}  # Track worker performance

        self.credentials = pika.PlainCredentials(
            "rabbituser", "rabbit1234"
        )  # Credentials for connecting to RabbitMQ

        # Setup default channel for sending URL data
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters("localhost", 5672, "/", self.credentials)
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=URL_QUEUE)
        self.channel.queue_declare(queue=RESULT_QUEUE)

        # Purge Queues to ensure clean start
        self.channel.queue_purge(queue=URL_QUEUE)
        self.channel.queue_purge(queue=RESULT_QUEUE)

        # Setup secondary channel for receiving RESULT data from workers
        self.result_connection = pika.BlockingConnection(
            pika.ConnectionParameters("localhost", 5672, "/", self.credentials)
        )
        self.result_channel = self.result_connection.channel()
        self.result_channel.queue_declare(queue=URL_QUEUE)
        self.result_channel.queue_declare(queue=RESULT_QUEUE)

        # Setup control channel for sending stop signal
        self.control_connection = pika.BlockingConnection(
            pika.ConnectionParameters("localhost", 5672, "/", self.credentials)
        )
        self.control_channel = self.control_connection.channel()
        self.control_channel.exchange_declare(
            exchange="control_exchange", exchange_type="fanout"
        )

    def result_callback(self, ch, method, properties, body):
        try:
            # Parse results
            results = json.loads(body.decode())

            # Use lock to ensure thread safety
            with self.lock:
                if isinstance(results, dict) and "results" in results:
                    # Go over every email scraped and append to results list
                    for entry in results["results"]:
                        if entry["email"] not in {r["email"] for r in self.results}:
                            self.results.append(entry)

                    # Add new discovered links to queue
                    if "links" in results and isinstance(results["links"], list):
                        for link in results["links"]:
                            if is_dlsu_url(link) and link not in self.visited:
                                self.url_queue.put(link)
                                print(f"[MASTER] Added new URL to queue: {link}")
                elif isinstance(results, list):
                    for entry in results:
                        if entry["email"] not in {r["email"] for r in self.results}:
                            self.results.append(entry)

        except Exception as e:
            print(f"[ERROR] {e}")

    def stop_consume(self):
        if hasattr(self, "result_channel") and self.result_channel.is_open:
            self.result_channel.connection.add_callback_threadsafe(
                self.result_channel.stop_consuming
            )

    def get_results(self):
        self.result_channel.basic_consume(
            queue=RESULT_QUEUE, on_message_callback=self.result_callback, auto_ack=True
        )
        try:
            self.result_channel.start_consuming()
        except pika.exceptions.ChannelClosedByBroker:
            print("[MASTER] Result consumer stopped.")

    def start(self):
        self.start_time = time.time()
        sub_thread = threading.Thread(target=self.get_results, daemon=True)
        sub_thread.start()
        while (time.time() - (self.start_time or 0)) < self.time_limit:
            q = self.channel.queue_declare(queue=URL_QUEUE, passive=True)
            if q.method.message_count == 0:
                if not self.url_queue.empty():
                    batch = []
                    while (
                        not self.url_queue.empty() and len(batch) < self.urls_per_batch
                    ):
                        curr_url = self.url_queue.get()
                        if curr_url not in self.visited:
                            self.visited.add(curr_url)
                            batch.append(curr_url)

                    if batch:
                        message = json.dumps(
                            {"urls": batch, "batch_id": len(self.visited)}
                        )
                        self.channel.basic_publish(
                            exchange="", routing_key=URL_QUEUE, body=message.encode()
                        )

                    if not batch:
                        # Check if time limit is reached
                        if (time.time() - (self.start_time or 0)) >= self.time_limit:
                            self.channel.queue_purge(URL_QUEUE)
                            self.control_channel.basic_publish(
                                exchange="control_exchange",
                                routing_key="",
                                body=b"NOURL",
                            )
                            break
                        # Otherwise wait and check again
                        self.channel.basic_publish(
                            exchange="", routing_key=URL_QUEUE, body=b"WAIT\n"
                        )
                        time.sleep(2)  # Wait 2 seconds before checking again
                        continue
        try:
            self.control_channel.basic_publish(
                exchange="control_exchange", routing_key="", body=b"NOURL"
            )
        except Exception as e:
            print(e)
        self.running = False
        self.stop_consume()
        sub_thread.join()
        self.result_connection.close()
        self.finish()

    def finish(self):
        if self.start_time is None:
            print("[MASTER] Error: start_time is not set.")
            minutes = 0
        else:
            minutes = (time.time() - self.start_time) / 60

        print(f"\n[MASTER] Scraping finished in {minutes:.2f} minutes.")
        print(f"[MASTER] {len(self.results)} unique emails found.")
        print(f"[MASTER] {len(self.visited)} pages scraped.")

        # Print worker statistics
        print("\n[MASTER] Worker Statistics:")
        for worker_id, stats in self.worker_stats.items():
            duration = time.time() - stats["start_time"]
            urls_per_min = (
                (stats["urls_processed"] / duration * 60) if duration > 0 else 0
            )
            print(
                f"  {worker_id}: {stats['urls_processed']} URLs, {stats['emails_found']} emails, {urls_per_min:.1f} URLs/min"
            )

        save_to_csv(self.results, OUTPUT_FILENAME)
        # Calculate total emails found (including duplicates)
        total_emails_found = sum(1 for r in self.results)
        unique_emails_found = len({r["email"] for r in self.results})
        log_statistics(
            ",".join(self.seed_urls),
            len(self.visited),
            total_emails_found,
            unique_emails_found,
        )


def main():
    parser = argparse.ArgumentParser(
        description="DLSU Distributed Email Scraper Master"
    )
    parser.add_argument(
        "--urls", nargs="+", required=True, help="Seed URLs (DLSU only)"
    )
    parser.add_argument("--port", type=int, default=5672, help="Port to listen on")
    parser.add_argument("--time", type=int, default=1, help="Time limit in minutes")
    parser.add_argument(
        "--batch-size", type=int, default=5, help="URLs per batch per worker"
    )
    args = parser.parse_args()
    master = Master(
        args.urls,
        port=args.port,
        time_limit_minutes=args.time,
        urls_per_batch=args.batch_size,
    )
    master.start()


if __name__ == "__main__":
    main()
