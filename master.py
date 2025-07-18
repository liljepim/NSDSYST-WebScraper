import json
import socket
from multiprocessing import Lock, Manager, Process

HOST = "localhost"
PORT = 9090


def handle_worker(
    conn,
    addr,
    email_list,
    visited_list,
    link_queue,
    email_lock,
    visited_lock,
    queue_lock,
):
    print(f"[Master] Connected to {addr}")
    try:
        while True:
            # Batch of 5 links cause why not
            batch = []
            with visited_lock:
                with queue_lock:
                    while not link_queue.empty() and len(batch) < 5:
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


def start_master():
    manager = Manager()
    email_list = manager.list()
    visited_list = manager.list()
    link_queue = manager.Queue()

    email_lock = Lock()
    visited_lock = Lock()
    queue_lock = Lock()

    link_queue.put("https://www.dlsu.edu.ph")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()

        print(f"[Master] Listening on {HOST}:{PORT}")

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
                ),
            )
            p.start()


if __name__ == "__main__":
    start_master()
