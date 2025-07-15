import re

import requests

all_emails = []
links_to_visit = ["https://www.dlsu.edu.ph/university-fellows/"]
visited = []


def email_finder(response):
    # print(response.status_code)
    found_emails = re.findall(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", response.text
    )
    # print("Number of emails found: ", len(found_emails))
    # print("Emails found:")
    for email in found_emails:
        print(email)
        all_emails.append(email)


def page_finder(response):
    # print(response.status_code)
    found_links = re.findall(
        r"https?://(?:[a-zA-Z0-9.-]+\.)?dlsu[^\s\"'>)]+", response.text
    )
    # print("Number of links found: ", len(found_links))
    # print("Links found:")
    for link in found_links:
        if link not in visited:
            if link[-1] == "/":
                links_to_visit.append(link)


def main():
    count = 0
    for link in links_to_visit:
        links_to_visit.remove(link)
        if link not in visited:
            # print("Visiting Link: ", link)
            # print("Remaining Lnks: ", len(links_to_visit))
            visited.append(link)
            try:
                response = requests.get(link)
                email_finder(response)
                page_finder(response)
            except:
                print("Maximum Retries Reached!")


main()
