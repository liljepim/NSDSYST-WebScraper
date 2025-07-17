import re
import warnings
from multiprocessing import Lock, Manager, Process, Queue

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def worker(email_list, link_queue, visited_list, email_lock, visited_lock, worker_id):
    def email_collection(soup):
        def decode_cfemail(cfemail):
            r = int(cfemail[:2], 16)
            return "".join(
                chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2)
            )

        for tag in soup.find_all("a", class_="__cf_email__"):
            cfemail = tag.get("data-cfemail")
            if cfemail:
                decoded = decode_cfemail(cfemail)
                if decoded not in email_list:
                    print(decoded)
                    email_list.append(decoded)

    def page_finder(response):
        # print(response.status_code)
        found_links = re.findall(
            r"https?://(?:[a-zA-Z0-9.-]+\.)?dlsu[^\s\"'>)]+", response.text
        )
        # print("Number of links found: ", len(found_links))
        # print("Links found:")
        for link in found_links:
            if link not in visited_list:
                if link[-1] == "/":
                    link_queue.put(link)

    while True:
        try:
            curr_url = link_queue.get(timeout=3)
        except:
            break

        with visited_lock:
            if curr_url not in visited_list:
                visited_list.append(curr_url)
                try:
                    # print(f"Process {worker_id} visiting {curr_url}")
                    response = requests.get(curr_url, timeout=5, allow_redirects=False)
                    soup = BeautifulSoup(response.text, "lxml")
                    with email_lock:
                        email_collection(soup)
                    page_finder(response)
                except Exception as e:
                    print(f"Process {worker_id} encountered error: {e}")


def main():
    manager = Manager()
    email_list = manager.list()
    link_queue = Queue()
    link_queue.put("https://www.dlsu.edu.ph/")
    visited_list = manager.list()

    email_lock = Lock()
    visited_lock = Lock()

    processes = []

    for i in range(15):
        p = Process(
            target=worker,
            args=(email_list, link_queue, visited_list, email_lock, visited_lock, i),
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


try:
    main()
except:
    print("Process Terminated")
