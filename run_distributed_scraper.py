#!/usr/bin/env python3
"""
Distributed Email Scraper with Hierarchical Nodes
================================================

This script demonstrates how to run the distributed scraper with:
- Master node that distributes URL batches to workers
- Worker nodes that use sub-nodes for parallel processing
- Configurable number of workers and sub-nodes per worker

Usage:
    python run_distributed_scraper.py --urls "https://www.dlsu.edu.ph" --time 5 --max-workers 3 --batch-size 3
"""

import subprocess
import sys
import time
import argparse
import threading
from pathlib import Path

def run_master(urls, time_limit, batch_size, port=5000):
    """Run the master node"""
    cmd = [
        sys.executable, "-m", "src.distributed.master",
        "--urls"] + urls + [
        "--time", str(time_limit),
        "--batch-size", str(batch_size),
        "--port", str(port)
    ]
    print(f"[MAIN] Starting master: {' '.join(cmd)}")
    return subprocess.Popen(cmd)

def run_worker(host, port, sub_nodes):
    """Run a worker node"""
    cmd = [
        sys.executable, "-m", "src.distributed.worker",
        "--host", host,
        "--port", str(port),
        "--sub-nodes", str(sub_nodes)
    ]
    print(f"[MAIN] Starting worker with {sub_nodes} sub-nodes: {' '.join(cmd)}")
    return subprocess.Popen(cmd)

def main():
    parser = argparse.ArgumentParser(description='Run Distributed Email Scraper with Hierarchical Nodes')
    parser.add_argument('--urls', nargs='+', required=True, help='Seed URLs to scrape')
    parser.add_argument('--time', type=int, default=5, help='Time limit in minutes')
    parser.add_argument('--workers', type=int, default=3, help='Number of workers to start (unlimited supported)')
    parser.add_argument('--batch-size', type=int, default=3, help='URLs per batch per worker')
    parser.add_argument('--sub-nodes', type=int, default=2, help='Sub-nodes per worker')
    parser.add_argument('--port', type=int, default=5000, help='Master port')
    args = parser.parse_args()

    print("=" * 60)
    print("DISTRIBUTED EMAIL SCRAPER WITH HIERARCHICAL NODES")
    print("=" * 60)
    print(f"Seed URLs: {args.urls}")
    print(f"Time limit: {args.time} minutes")
    print(f"Workers to start: {args.workers} (unlimited supported)")
    print(f"Batch size: {args.batch_size}")
    print(f"Sub-nodes per worker: {args.sub_nodes}")
    print(f"Initial parallel processing capacity: {args.workers * args.sub_nodes} nodes")
    print("=" * 60)

    # Start master
    master_process = run_master(args.urls, args.time, args.batch_size, args.port)
    
    # Wait a moment for master to start
    time.sleep(2)
    
    # Start workers
    worker_processes = []
    for i in range(args.workers):
        worker = run_worker("localhost", args.port, args.sub_nodes)
        worker_processes.append(worker)
        time.sleep(1)  # Stagger worker starts
    
    print(f"[MAIN] Started {len(worker_processes)} workers")
    print("[MAIN] Master can accept unlimited additional workers")
    print("[MAIN] Waiting for scraping to complete...")
    
    try:
        # Wait for master to finish
        master_process.wait()
        print("[MAIN] Master finished")
        
        # Terminate workers
        for worker in worker_processes:
            worker.terminate()
            worker.wait()
        print("[MAIN] All workers terminated")
        
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted by user")
        master_process.terminate()
        for worker in worker_processes:
            worker.terminate()
    
    # Check for output files
    if Path("scraped_emails.csv").exists():
        print("[MAIN] Results saved to scraped_emails.csv")
    if Path("scraping_statistics.txt").exists():
        print("[MAIN] Statistics saved to scraping_statistics.txt")
        with open("scraping_statistics.txt", "r") as f:
            print("\n" + f.read())

if __name__ == "__main__":
    main() 