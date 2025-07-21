import asyncio
import json
import re
import socket
import time
import warnings

import aiohttp
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
LINK_REGEX = r"https?://(?:[a-zA-Z0-9.-]+\.)?dlsu[^\s\"'>)]+"


class WorkerNode:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def decode_cfemail(self, cfemail):
        r = int(cfemail[:2], 16)
        return "".join(
            chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2)
        )

    def collect_emails(self, html):
        soup = BeautifulSoup(html, "lxml")
        emails = set()

        # First with cloudflare protected ones
        for tag in soup.find_all("a", class_="__cf_email__"):
            cfemail = tag.get("data-cfemail")
            if cfemail:
                emails.add(self.decode_cfemail(cfemail))

        # Next the plain texts
        emails.update(re.findall(EMAIL_REGEX, html))
        return list(emails)

    def extract_links(self, html):
        found_links = re.findall(LINK_REGEX, html)
        final_links = set()
        for link in found_links:
            if link[-1] == "/":
                final_links.add(link)
        return list(final_links)

    async def fetch_url(self, session, url):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    return html
        except Exception as e:
            print(f"[Error] {url}: {e}")
        return ""

    async def worker_loop(self):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.host, self.port))

                    data = s.recv(4)
                    duration = int.from_bytes(data, byteorder="big", signed=True) * 60

                    start_time = time.time()
                    while time.time() - start_time < duration:
                        # We gotta get the batch of links first bruv
                        data = b""
                        while not data.endswith(b"\n"):
                            data += s.recv(4096)
                        urls = json.loads(data.decode())["links"]

                        if not urls:
                            await asyncio.sleep(2)
                            continue

                        emails_found = set()
                        links_found = set()

                        async with aiohttp.ClientSession() as session:
                            tasks = [self.fetch_url(session, url) for url in urls]
                            html_pages = await asyncio.gather(*tasks)

                            for html in html_pages:
                                emails_found.update(self.collect_emails(html))
                                links_found.update(self.extract_links(html))

                        result = (
                            json.dumps(
                                {
                                    "emails": list(emails_found),
                                    "links": list(links_found),
                                }
                            ).encode()
                            + b"\n"
                        )

                        s.sendall(result)

                    end_time = time.time()
                    print(f"Total time ran: {end_time - start_time}")
                    return
            except Exception as e:
                print(f"[Worker] Disconnected or error: {e}")
                await asyncio.sleep(3)

    def start(self):
        asyncio.run(self.worker_loop())


if __name__ == "__main__":
    worker = WorkerNode("localhost", 9090)
    worker.start()
