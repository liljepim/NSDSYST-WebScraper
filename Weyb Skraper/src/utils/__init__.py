def log_statistics(url, pages_scraped, emails_found, unique_emails=None):
    # Function to log the scraping statistics
    print(f"Scraping statistics for {url}:")
    print(f"Pages scraped: {pages_scraped}")
    print(f"Emails found: {emails_found}")
    if unique_emails is not None:
        print(f"Unique emails found: {unique_emails}")
    # Also write to a text file
    with open('scraping_statistics.txt', 'w', encoding='utf-8') as f:
        f.write(f"Website: {url}\n")
        f.write(f"Pages scraped: {pages_scraped}\n")
        f.write(f"Emails found: {emails_found}\n")
        if unique_emails is not None:
            f.write(f"Unique emails found: {unique_emails}\n")

def save_to_csv(data, filename):
    # Function to save scraped email data in CSV format
    import csv
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['email', 'name', 'office', 'department'])
        for entry in data:
            writer.writerow([entry.get('email', ''), entry.get('name', ''), entry.get('office', ''), entry.get('department', '')])