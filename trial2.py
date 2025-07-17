import re
from multiprocessing import Lock, Manager, Process, Queue

import requests
from bs4 import BeautifulSoup


def worker(email_list, link_queue, visited_list, email_lock, worker_id):
    def decode_cfemail(cfemail):
        r = int(cfemail[:2], 16)
        return "".join(
            chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2)
        )

    def email_collection(soup):
        for tag in soup.find_all("a", class_="__cf_email__"):
            cfemail = tag.get("data-cfemail")
            if cfemail:
                decoded = decode_cfemail(cfemail)
                if decoded not in email_list:
                    print(f"[{worker_id}] Email found: {decoded}")
                    email_list.append(decoded)

    def page_finder(response):
        found_links = re.findall(
            r"https?://(?:[a-zA-Z0-9.-]+\.)?dlsu[^\s\"'>)]+", response.text
        )
        for link in found_links:
            if link.endswith("/") and link not in visited_list:
                link_queue.put(link)

    while True:
        try:
            curr_url = link_queue.get(timeout=3)
        except:
            break  # Timeout -> no more links to process

        if curr_url not in visited_list:
            visited_list.append(curr_url)
            try:
                print(f"[{worker_id}] Visiting: {curr_url}")
                response = requests.get(curr_url, timeout=5)
                soup = BeautifulSoup(response.text, "lxml")
                with email_lock:
                    email_collection(soup)
                page_finder(response)
            except Exception as e:
                print(f"[{worker_id}] Error: {e}")


def main():
    manager = Manager()
    email_list = manager.list()
    visited_list = manager.list()
    link_queue = Queue()
    link_queue.put("https://www.dlsu.edu.ph/")

    email_lock = Lock()

    processes = []
    for i in range(5):
        p = Process(
            target=worker,
            args=(email_list, link_queue, visited_list, email_lock, i),
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("\nCollected Emails:")
    for email in email_list:
        print(email)


if __name__ == "__main__":
    try:
        main()
    except:
        print("Process Terminated")
