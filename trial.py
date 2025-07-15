import requests
from bs4 import BeautifulSoup


def decode_cfemail(cfemail):
    r = int(cfemail[:2], 16)
    return "".join(
        chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2)
    )


url = "https://www.dlsu.edu.ph/university-fellows/"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

emails = []

for tag in soup.find_all("a", class_="__cf_email__"):
    cfemail = tag.get("data-cfemail")
    if cfemail:
        decoded = decode_cfemail(cfemail)
        emails.append(decoded)

print("Decoded emails:", emails)
