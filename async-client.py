import asyncio

import aiohttp

# from multiprocessing import Process, Manager, Lock, Queue
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


class WorkerNode:
    def __init__(
        self, email_list, visited_list, link_queue, email_lock, visited_lock, worker_id
    ):
        self.email_list = email_list
        self.visited_list = visited_list
        self.link_queue = link_queue
        self.email_lock = email_lock
        self.visited_lock = visited_lock
        self.worker_id = worker_id

    def decode_cfemail(cfemail):
        r = int(cfemail[:2], 16)
        return "".join(
            chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2)
        )

    def collect_emails(self, html):
        soup = BeautifulSoup(html, "lxml")

        # First with cloudflare protected ones
        for tag in soup.find_all("a", class_="__cf_email__"):
            cfemail = tag.get("data-cfemail")
            if cfemail:
                decoded = self.decode_cfemail(cfemail)
                with self.email_lock:
                    if decoded not in self.email_list:
                        self.email_list.append(decoded)
                        print(f"[CFEmail] {decoded}")

        # Next the plain texts
        emails = set(re.findall(EMAIL_REGEX, html))
        with self.email_lock:
            for email in emails:
                if email not in self.email_list:
                    self.email_list.append(email)
                    print(f"[PlainText] {email}")

    def extract_links(self, html):
        pass

    async def fetch_and_process(self, session, url):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    self.collect_emails(html)
                    self.extract_links(html)
        except Exception as e:
            print(f"[Error] {url}: {e}")

    async def worker_loop(self):
        async with aiohttp.ClientSession() as session:
            while True:
                batch = []

                for _ in range(5):
                    try:
                        url = self.link_queue.get_nowait()
                        with self.visit_lock:
                            if url in self.visited_list:
                                continue
                            self.visited_list.append(url)
                        batch.append(url)
                    except:
                        print("Error encountered")

                if not batch:
                    await asyncio.sleep(1)
                    continue

                tasks = [self.fetch_and_process(session, url) for url in batch]
                await asyncio.gather(*tasks)
