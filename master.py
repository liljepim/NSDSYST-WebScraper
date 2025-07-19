import argparse
import json
import socket
from multiprocessing import Lock, Manager, Process


def handle_worker(
    conn,
    addr,
    email_list,
    visited_list,
    link_queue,
    email_lock,
    visited_lock,
    queue_lock,
    nodes,
    duration,
):
    print(f"[Master] Connected to {addr}")
    try:
        while True:
            # Batch of 5 links cause why not
            batch = []
            with visited_lock:
                with queue_lock:
                    while not link_queue.empty() and len(batch) < nodes:
                        link = link_queue.get()
                        if link not in visited_list:
                            visited_list.append(link)
                            batch.append(link)

            conn.sendall(json.dumps({"links": batch}).encode() + b"\n")

            # Receive results from EmailWorker
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    return
                data += chunk

            results = json.loads(data.decode())
            new_emails = results.get("emails", [])
            new_links = results.get("links", [])

            with email_lock:
                for email in new_emails:
                    if email not in email_list:
                        email_list.append(email)
                        print(f"[Master] Email : {email}")

            with visited_lock, queue_lock:
                for link in new_links:
                    if link not in visited_list:
                        link_queue.put(link)
    except Exception as e:
        print(f"[Master] Error with {addr}: {e}")
    finally:
        conn.close()


def start_master(host, port, nodes, nodes, csv_name, seed, duration):
    manager = Manager()
    email_list = manager.list()
    visited_list = manager.list()
    link_queue = manager.Queue()

    email_lock = Lock()
    visited_lock = Lock()
    queue_lock = Lock()

    link_queue.put(seed)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()

        print(f"[Master] Listening on {host}:{port}")

        while True:
            conn, addr = s.accept()
            p = Process(
                target=handle_worker,
                args=(
                    conn,
                    addr,
                    email_list,
                    visited_list,
                    link_queue,
                    email_lock,
                    visited_lock,
                    queue_lock,
                    nodes,
                    duration,
                ),
            )
            p.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="WebScraper v1.0")
    parser.add_argument(
        "--host",
        help="Specify the IP Address of the Host Machine [Default = localhost]",
        default="localhost",
    )
    parser.add_argument(
        "--port",
        help="Specify the Port of the Master Node [Default = 9090]",
        default=9090,
    )
    parser.add_argument(
        "-n",
        "--nodes",
        help="Specify the Maximum Number of nodes [Default=5]",
        default=5,
    )
    parser.add_argument(
        "--csv",
        help="Specify the name of the file of the generated CSV [Default=emails.csv]",
        default="email.csv",
    )
    parser.add_argument(
        "-s",
        "--seed",
        help="Specify the starting link [Default=https://www.dlsu.edu.ph/]",
        default="https://www.dlsu.edu.ph",
    )
    parser.add_argument(
        "-t",
        "--time",
        help="Specify the duration that the program will execute in minutes [Default=5]",
        default=5,
    )

    try:
        args = parser.parse_args()
        print("Arguments", args)
    except:
        parser.print_help()

    start_master()
