import socket
import threading
import time
import argparse
import queue
from src.scraper import Scraper
from src.utils import save_to_csv, log_statistics
from urllib.parse import urlparse
import json

# Default output file name for scraped emails
OUTPUT_FILENAME = 'scraped_emails.csv'

DLSU_DOMAINS = ["dlsu.edu.ph"]

def is_dlsu_url(url):
    try:
        netloc = urlparse(url).netloc.lower()
        return any(domain in netloc for domain in DLSU_DOMAINS)
    except Exception:
        return False

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

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
        self.start_time = None
        self.scraper = Scraper()
        self.running = True
        self.active_workers = 0
        self.worker_stats = {}  # Track worker performance

    def start(self):
        self.start_time = time.time()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", self.port))
        server.listen(50)  # Increased backlog for unlimited workers
        print(f"[MASTER] Listening on port {self.port}...")
        print(f"[MASTER] URLs per batch: {self.urls_per_batch}")
        print(f"[MASTER] Accepting unlimited workers for maximum scalability")
        threads = []
        while (time.time() - (self.start_time or 0)) < self.time_limit:
            server.settimeout(1)
            try:
                client, addr = server.accept()
                print(f"[MASTER] Worker connected from {addr}")
                self.active_workers += 1
                t = threading.Thread(target=self.handle_worker, args=(client, addr))
                t.start()
                threads.append(t)
            except socket.timeout:
                continue
        self.running = False
        for t in threads:
            t.join()
        self.finish()

    def handle_worker(self, client, addr):
        client.settimeout(15)  # Increased timeout for batch processing
        worker_id = f"{addr[0]}:{addr[1]}"
        self.worker_stats[worker_id] = {"urls_processed": 0, "emails_found": 0, "start_time": time.time()}
        
        while self.running and (time.time() - (self.start_time or 0)) < self.time_limit:
            try:
                # Assign a batch of URLs
                urls_batch = []
                with self.lock:
                    for _ in range(self.urls_per_batch):
                        if not self.url_queue.empty():
                            candidate = self.url_queue.get()
                            if candidate not in self.visited and is_dlsu_url(candidate):
                                self.visited.add(candidate)
                                urls_batch.append(candidate)
                        else:
                            break
                
                if not urls_batch:
                    # Check if time limit is reached
                    if (time.time() - (self.start_time or 0)) >= self.time_limit:
                        client.sendall(b"NOURL\n")
                        break
                    # Otherwise wait and check again
                    client.sendall(b"WAIT\n")
                    time.sleep(2)  # Wait 2 seconds before checking again
                    continue
                
                # Send batch of URLs
                batch_data = json.dumps({"urls": urls_batch, "batch_id": len(self.visited)})
                client.sendall((batch_data + "\n").encode())
                
                # Receive results
                length_bytes = recv_all(client, 4)
                if not length_bytes:
                    break
                length = int.from_bytes(length_bytes, 'big')
                data = recv_all(client, length)
                if not data:
                    break
                
                try:
                    results = json.loads(data.decode())
                    with self.lock:
                        # Update worker stats
                        self.worker_stats[worker_id]["urls_processed"] += len(urls_batch)
                        
                        # Process results
                        if isinstance(results, dict) and "results" in results:
                            for entry in results["results"]:
                                if entry['email'] not in {r['email'] for r in self.results}:
                                    self.results.append(entry)
                            self.worker_stats[worker_id]["emails_found"] += len(results["results"])
                            
                            # Add new discovered links to queue
                            if 'links' in results and isinstance(results['links'], list):
                                for link in results['links']:
                                    if is_dlsu_url(link) and link not in self.visited:
                                        self.url_queue.put(link)
                                        print(f"[MASTER] Added new URL to queue: {link}")
                        elif isinstance(results, list):
                            for entry in results:
                                if entry['email'] not in {r['email'] for r in self.results}:
                                    self.results.append(entry)
                            self.worker_stats[worker_id]["emails_found"] += len(results)
                            
                except Exception as ex:
                    print(f"[MASTER] Error decoding worker data from {worker_id}: {ex}")
                    
            except Exception as ex:
                print(f"[MASTER] Worker {worker_id} error: {ex}")
                break
                
        self.active_workers -= 1
        client.close()
        print(f"[MASTER] Worker {worker_id} disconnected. Active workers: {self.active_workers}")

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
            urls_per_min = (stats["urls_processed"] / duration * 60) if duration > 0 else 0
            print(f"  {worker_id}: {stats['urls_processed']} URLs, {stats['emails_found']} emails, {urls_per_min:.1f} URLs/min")
        
        save_to_csv(self.results, OUTPUT_FILENAME)
        # Calculate total emails found (including duplicates)
        total_emails_found = sum(1 for r in self.results)
        unique_emails_found = len({r['email'] for r in self.results})
        log_statistics(",".join(self.seed_urls), len(self.visited), total_emails_found, unique_emails_found)

def main():
    parser = argparse.ArgumentParser(description='DLSU Distributed Email Scraper Master')
    parser.add_argument('--urls', nargs='+', required=True, help='Seed URLs (DLSU only)')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--time', type=int, default=1, help='Time limit in minutes')
    parser.add_argument('--batch-size', type=int, default=5, help='URLs per batch per worker')
    args = parser.parse_args()
    master = Master(args.urls, port=args.port, time_limit_minutes=args.time, 
                   urls_per_batch=args.batch_size)
    master.start()

if __name__ == "__main__":
    main() 