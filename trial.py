import re

import requests
from bs4 import BeautifulSoup

links_to_visit = ["https://www.dlsu.edu.ph/"]
visited = []
emails = []


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
            if decoded not in emails:
                print(decoded)
                emails.append(decoded)


def page_finder(response):
    # print(response.status_code)
    found_links = re.findall(
        r"https?://(?:[a-zA-Z0-9.-]+\.)?dlsu[^\s\"'>)]+", response.text
    )
    # print("Number of links found: ", len(found_links))
    # print("Links found:")
    for link in found_links:
        if link not in visited and link not in links_to_visit:
            if link[-1] == "/":
                links_to_visit.append(link)


def main():
    for link in links_to_visit:
        if link not in visited:
            visited.append(link)
            print("Current link: ", link)
            try:
                response = requests.get(link)
                soup = BeautifulSoup(response.text, "lxml")
                email_collection(soup)
                page_finder(response)
            except:
                print("Error encountered when visiting!")


main()
