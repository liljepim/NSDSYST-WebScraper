import socket
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.scraper import Scraper
from urllib.parse import urlparse, urljoin

DLSU_DOMAINS = ["dlsu.edu.ph"]

def is_dlsu_url(url):
    try:
        netloc = urlparse(url).netloc.lower()
        return any(domain in netloc for domain in DLSU_DOMAINS)
    except Exception:
        return False

class Worker:
    def __init__(self, master_host, master_port, sub_nodes=3):
        self.master_host = master_host
        self.master_port = master_port
        self.scraper = Scraper()
        self.sub_nodes = sub_nodes  # Number of sub-nodes for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=sub_nodes)
        self.worker_id = f"{master_host}:{master_port}"

    def scrape_url_with_sub_nodes(self, url):
        """Scrape a single URL using sub-nodes for parallel processing"""
        try:
            print(f"[WORKER-{self.worker_id}] Scraping: {url}")
            results = self.scraper.scrape_page(url)
            
            # Find additional links for further scraping
            try:
                import requests
                from bs4 import BeautifulSoup
                resp = requests.get(url, timeout=10)
                soup = BeautifulSoup(resp.text, 'html.parser')
                links = []
                for a in soup.find_all('a', href=True):
                    try:
                        href = a['href']
                        if isinstance(href, str):
                            link = urljoin(url, href)
                            if is_dlsu_url(link):
                                links.append(link)
                    except (KeyError, TypeError):
                        continue
                return {"results": results, "links": links}
            except Exception:
                return {"results": results, "links": []}
        except Exception as ex:
            print(f"[WORKER-{self.worker_id}] Error scraping {url}: {ex}")
            return {"results": [], "links": []}

    def process_url_batch(self, urls_batch):
        """Process a batch of URLs using sub-nodes for parallel scraping"""
        print(f"[WORKER-{self.worker_id}] Processing batch of {len(urls_batch)} URLs with {self.sub_nodes} sub-nodes")
        
        # Submit URLs to sub-nodes for parallel processing
        future_to_url = {}
        for url in urls_batch:
            future = self.executor.submit(self.scrape_url_with_sub_nodes, url)
            future_to_url[future] = url
        
        # Collect results from all sub-nodes
        all_results = []
        all_links = []
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                all_results.extend(result["results"])
                all_links.extend(result["links"])
                print(f"[WORKER-{self.worker_id}] Completed: {url} ({len(result['results'])} emails)")
            except Exception as ex:
                print(f"[WORKER-{self.worker_id}] Error processing {url}: {ex}")
        
        # Remove duplicate links
        unique_links = list(set(all_links))
        
        return {
            "results": all_results,
            "links": unique_links,
            "batch_stats": {
                "urls_processed": len(urls_batch),
                "emails_found": len(all_results),
                "new_links_found": len(unique_links)
            }
        }

    def run(self):
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.master_host, self.master_port))
                print(f"[WORKER-{self.worker_id}] Connected to master")
                
                while True:
                    # Receive batch data
                    data = s.recv(8192).decode().strip()
                    if data == "NOURL" or not data:
                        print(f"[WORKER-{self.worker_id}] No more URLs, disconnecting")
                        s.close()
                        return
                    elif data == "WAIT":
                        print(f"[WORKER-{self.worker_id}] Waiting for more URLs...")
                        continue
                    
                    try:
                        batch_info = json.loads(data)
                        urls_batch = batch_info.get("urls", [])
                        batch_id = batch_info.get("batch_id", 0)
                        
                        if not urls_batch:
                            continue
                        
                        print(f"[WORKER-{self.worker_id}] Received batch {batch_id} with {len(urls_batch)} URLs")
                        
                        # Process the batch using sub-nodes
                        start_time = time.time()
                        batch_results = self.process_url_batch(urls_batch)
                        processing_time = time.time() - start_time
                        
                        # Add timing information
                        batch_results["processing_time"] = processing_time
                        batch_results["worker_id"] = self.worker_id
                        batch_results["batch_id"] = batch_id
                        
                        # Send results back to master
                        payload = json.dumps(batch_results)
                        payload_bytes = payload.encode()
                        length = len(payload_bytes)
                        s.sendall(length.to_bytes(4, 'big') + payload_bytes)
                        
                        print(f"[WORKER-{self.worker_id}] Batch {batch_id} completed in {processing_time:.2f}s")
                        
                    except json.JSONDecodeError:
                        print(f"[WORKER-{self.worker_id}] Invalid JSON received from master")
                        continue
                        
            except Exception as ex:
                print(f"[WORKER-{self.worker_id}] Error: {ex}")
                time.sleep(2)
                continue
            finally:
                try:
                    s.close()
                except:
                    pass

def main():
    import argparse
    parser = argparse.ArgumentParser(description='DLSU Distributed Email Scraper Worker')
    parser.add_argument('--host', type=str, required=True, help='Master host')
    parser.add_argument('--port', type=int, default=5000, help='Master port')
    parser.add_argument('--sub-nodes', type=int, default=3, help='Number of sub-nodes for parallel processing')
    args = parser.parse_args()
    
    print(f"[WORKER] Starting worker with {args.sub_nodes} sub-nodes")
    worker = Worker(args.host, args.port, sub_nodes=args.sub_nodes)
    worker.run()

if __name__ == "__main__":
    main() 