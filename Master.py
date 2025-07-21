import argparse
import csv
import json
import socket
import struct
import time
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
        # Set the duration of the connection
        conn.sendall(struct.pack("!i", duration))

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


def process_emails(email_list):
    processed_emails = []
    for email in email_list:
        status = ""
        email_parts = email.split("@")
        email_name = ""
        office = ""
        department = ""
        unit = ""
        if email_parts[1] == "dlsu.edu.ph":
            first_part = email_parts[0].split(".")
            if len(first_part) >= 2:
                status = "name"
            if status == "name":
                for name in first_part:
                    email_name += name.capitalize()
            else:
                department = first_part[0].capitalize()
            processed_emails.append([email, email_name, office, department, unit])

    return processed_emails


def create_csv(email_list, csv_name):
    with open(csv_name, "w", newline="") as file:
        writer = csv.writer(file)
        # Write the header [Name, Office Departmer, Unit]
        writer.writerow(["Email", "Name", "Office", "Department", "Unit"])
        processed_emails = process_emails(email_list)
        for email in processed_emails:
            writer.writerow(email)


def start_master(host, port, nodes, csv_name, seed, duration):
    manager = Manager()
    email_list = manager.list()
    visited_list = manager.list()
    link_queue = manager.Queue()

    is_started = False
    start_time = 0
    email_lock = Lock()
    visited_lock = Lock()
    queue_lock = Lock()

    process_list = []
    link_queue.put(seed)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        s.settimeout(1)

        print(f"[Master] Listening on {host}:{port}")

        while True:
            if is_started and time.time() - start_time > (duration * 60):
                print("[Master] Search Finished")
                print(
                    f"[Master] Total Elapsed Time: {
                        ((time.time() - start_time) / 60):.2f}"
                )
                break

            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue

            if not is_started:
                is_started = True
                start_time = time.time()

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
            process_list.append(p)

        for p in process_list:
            p.terminate()
            p.join()

        print(f"Total Number of Emails Found: {len(email_list)}")
        print("Exporting to CSV...")
        create_csv(email_list, csv_name)
        print(f"Results successfully exported to {csv_name}")

        return


def main(args):
    start_master(args.host, args.port, args.nodes, args.csv, args.seed, args.time)


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
        type=int,
    )
    parser.add_argument(
        "-n",
        "--nodes",
        help="Specify the Maximum Number of nodes [Default=5]",
        default=5,
        type=int,
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
        type=int,
    )

    main(parser.parse_args())
