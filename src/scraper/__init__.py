import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from io import BytesIO
from pdfminer.high_level import extract_text
import spacy

# Email regex pattern for matching email addresses
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Load spaCy model once
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None  # If not available, fallback to regex only

# Helper for spaCy-based name extraction
def extract_name_with_spacy(text):
    if nlp is None:
        return ""
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return ""

class Scraper:
    def is_valid_email(self, email):
        # Filter out obvious spam/gibberish emails
        # - Must have at least 2 chars before @
        # - Domain must have at least one dot and at least 2 chars after last dot
        # - No single-char domain or TLD
        # - No all-numeric local part
        if len(email) < 6 or '@' not in email:
            return False
        local, _, domain = email.rpartition('@')
        if len(local) < 2 or '.' not in domain:
            return False
        if len(domain.rsplit('.', 1)[-1]) < 2:
            return False
        if local.isdigit():
            return False
        if re.match(r'^[A-Za-z0-9._%+-]+$', local) is None:
            return False
        # Add more rules as needed
        return True

    def extract_emails(self, text):
        emails = re.findall(EMAIL_REGEX, text)
        return [e for e in set(emails) if self.is_valid_email(e)]

    def extract_emails_from_pdf(self, pdf_bytes):
        try:
            text = extract_text(BytesIO(pdf_bytes))
            return self.extract_emails(text)
        except Exception as ex:
            print(f"    Error extracting emails from PDF: {ex}")
            return []

    def extract_info_from_email(self, email):
        # Split email by '@'
        local_part = email.split('@')[0]
        parts = local_part.split('.')
        name = ''
        office = ''
        department = ''
        office_map = {
            'admission': 'Admissions Office', 'admissions': 'Admissions Office',
            'scholarships': 'Scholarship Office',
            'registrar': 'Registrar',
            'library': 'Library',
            'finance': 'Finance Office',
            'accounting': 'Accounting Office',
            'alumni': 'Alumni Office',
            'guidance': 'Guidance Office',
            'graduate': 'Graduate Studies',
            'president': 'Office of the President',
            'dean': 'Dean Office', 'deancos': 'Dean College of Science Office', 'deancla': 'Dean College of Liberal Arts Office', 'deaneng': 'Dean College of Engineering Office',
            'faculty': 'Faculty Office',
            'student': 'Student Affairs Office',
            'clinic': 'Clinic',
            'security': 'Security Office',
            'maintenance': 'Maintenance Office',
            'stratcom': 'Strategic Communications Office',
            'osd': 'Office of Student Discipline Office',
            'dlsupublishinghouse': 'DLSU Publishing House Office',
            'urco': 'University Research Coordination Office',
            'rgmo': 'Research Grants Management Office',
            'cashiers': 'Cashiers Office',
            'personnel': 'Personnel Office',
            'procurement': 'Procurement Office',
            'sdfo': 'Student Discipline Formation Office',
            'occs': 'Office of Counseling and Career Services Office',
            'itservices': 'IT Services Office',
            'lasallianmission': 'Lasallian Mission Office',
            'acadpublications': 'Academic Publications Office',
            'chaircomm': 'Chair, Communication Office',
            'vicechaircomm': 'Vice Chair Office',
            'manilajournalofscience': 'Manila Journal of Science Office',
            'asiapacificsocialsciencereviewjournal': 'Asia-Pacific Social Science Review Journal Office',
            'yuchengcocenter': 'Yuchengco Center',
            'iechair': 'Chair, Industrial Engineering Office',
            'chairce': 'Chair, Civil Engineering Office',
            'academicservices': 'Academic Services Office',
        }
        department_map = {
            'science': 'Science Department',
            'arts': 'Arts Department',
            'business': 'Business Department',
            'law': 'Law Department',
            'education': 'Education Department',
            'engineering': 'Engineering Department',
            'ict': 'ICT Department',
            'it': 'IT Department',
            'accounting': 'Accounting Department',
            'marketing': 'Marketing Department',
            'research': 'Research Department',
            'mathematics': 'Mathematics Department',
            'english': 'English Department',
            'socialscience': 'Social Science Department',
            'humanities': 'Humanities Department',
            'psychology': 'Psychology Department',
            'biology': 'Biology Department',
            'chemistry': 'Chemistry Department',
            'physics': 'Physics Department',
            'computer': 'Computer Science Department',
            'cs': 'Computer Science Department',
            'ee': 'Electrical Engineering Department',
            'ce': 'Civil Engineering Department',
            'me': 'Mechanical Engineering Department',
            'arch': 'Architecture Department',
            'architecture': 'Architecture Department',
            'pharmacy': 'Pharmacy Department',
            'nursing': 'Nursing Department',
            'medicine': 'Medicine Department',
            'dentistry': 'Dentistry Department',
            'accountancy': 'Accountancy Department',
            'economics': 'Economics Department',
            'politicalscience': 'Political Science Department',
            'philosophy': 'Philosophy Department',
            'history': 'History Department',
            'sociology': 'Sociology Department',
            'anthropology': 'Anthropology Department',
            'geology': 'Geology Department',
            'environmental': 'Environmental Science Department',
            'statistics': 'Statistics Department',
            'ccs': 'College of Computer Studies',
            'cbag': 'College of Business and Accountancy',
            'cba': 'College of Business and Accountancy',
            'coe': 'College of Engineering',
            'cos': 'College of Science',
            'cla': 'College of Liberal Arts',
            'gcoe': 'Gokongwei College of Engineering',
            'stratcom': 'Strategic Communications',
            'osd': 'Office of Student Discipline',
            'dlsupublishinghouse': 'DLSU Publishing House',
            'urco': 'University Research Coordination ',
            'rgmo': 'Research Grants Management',
            'sdfo': 'Student Discipline Formation',
            'occs': 'Office of Counseling and Career Services',
            'itservices': 'IT Services',
            'lasallianmission': 'Lasallian Mission',
            'acadpublications': 'Academic Publications',
            'chaircomm': 'Communication Department',
            'vicechaircomm': 'Communication Department',
            'manilajournalofscience': 'Manila Journal of Science',
            'asiapacificsocialsciencereviewjournal': 'Asia-Pacific Social Science Review Journal',
            'deancos': 'Dean College of Science', 'deancla': 'Dean College of Liberal Arts', 'deaneng': 'Dean College of Engineering',
            'yuchengcocenter': 'Yuchengco Center',
            'ie': 'Industrial Engineering Department',
            'ce': 'Civil Engineering Department',
        }
        if len(parts) > 0:
            local_lower = parts[0].lower()
            # Check for department or office match first
            if local_lower in department_map:
                department = department_map[local_lower]
                name = ''
            elif local_lower in office_map:
                office = office_map[local_lower]
                name = ''
            else:
                # Name extraction: capitalize first and second elements if available
                if len(parts) > 1:
                    name = parts[0].capitalize() + ' ' + parts[1].capitalize()
                elif len(parts) == 1:
                    name = parts[0].capitalize()
        return {'name': name, 'office': office, 'department': department}

    def extract_info(self, text, email=None):
        # If email is provided, use the new extraction logic
        if email:
            return self.extract_info_from_email(email)
        # Otherwise, fallback to old logic
        info = {'name': '', 'office': '', 'department': ''}
        # Name extraction
        name_match = re.search(r'(Name|Contact Person)\s*[:\-]?\s*([A-Z][a-z]+(\s+[A-Z][a-z]+)+)', text)
        if name_match:
            info['name'] = name_match.group(2).strip()
        # Office extraction
        office_match = re.search(r'(Office|Unit)\s*[:\-]?\s*([A-Za-z\s]+)', text)
        if office_match:
            info['office'] = office_match.group(2).strip()
        # Department extraction
        dept_match = re.search(r'(Department|Dept)\s*[:\-]?\s*([A-Za-z\s]+)', text)
        if dept_match:
            info['department'] = dept_match.group(2).strip()
        return info

    def extract_info_pdf(self, text):
        info = {'name': '', 'office': '', 'department': ''}
        name_match = re.search(r'(Name|Contact Person)[:\-\s]*([A-Z][a-zA-Z\s]+)', text)
        if name_match:
            info['name'] = name_match.group(2).strip()
        else:
            # Fallback: use spaCy NER
            info['name'] = extract_name_with_spacy(text)
        office_match = re.search(r'(Office|Unit)[:\-\s]*([A-Za-z\s]+)', text)
        if office_match:
            info['office'] = office_match.group(2).strip()
        dept_match = re.search(r'(Department|Dept)[:\-\s]*([A-Za-z\s]+)', text)
        if dept_match:
            info['department'] = dept_match.group(2).strip()
        if any(info.values()):
            return info
        return {'name': '', 'office': '', 'department': ''}

    def extract_info_near_email(self, soup, email):
        # Use the new extraction logic based on email
        return self.extract_info_from_email(email)

    def clean_info_field(self, value):
        # Only accept if short and single-line
        if not value:
            return ''
        value = value.strip()
        if len(value) > 50 or '\n' in value or '\r' in value:
            return ''
        return value

    def crawl(self, start_url, time_limit=60, max_pages=100):
        visited = set()
        to_visit = [start_url]
        found_emails = set()
        results = []
        start_time = time.time()
        base_netloc = urlparse(start_url).netloc
        while to_visit and (time.time() - start_time) < time_limit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            print(f"Visiting: {url}")
            visited.add(url)
            try:
                if url.lower().endswith('.pdf'):
                    resp = requests.get(url, timeout=15)
                    text = extract_text(BytesIO(resp.content))
                    pdf_emails = self.extract_emails(text)
                    if pdf_emails:
                        print(f"  Found emails in PDF: {pdf_emails}")
                    for e in pdf_emails:
                        if e not in found_emails:
                            found_emails.add(e)
                            info = self.extract_info_from_email(e)
                            results.append({
                                'email': e,
                                'name': self.clean_info_field(info.get('name','')),
                                'office': self.clean_info_field(info.get('office','')),
                                'department': self.clean_info_field(info.get('department',''))
                            })
                    continue
                resp = requests.get(url, timeout=10)
                soup = BeautifulSoup(resp.text, 'html.parser')
                text = soup.get_text()
                emails = self.extract_emails(text)
                if emails:
                    print(f"  Found emails: {emails}")
                for e in emails:
                    if e not in found_emails:
                        found_emails.add(e)
                        info = self.extract_info_near_email(soup, e)
                        results.append({
                            'email': e,
                            'name': self.clean_info_field(info.get('name','')),
                            'office': self.clean_info_field(info.get('office','')),
                            'department': self.clean_info_field(info.get('department',''))
                        })
                # Find internal links and PDFs
                for a in soup.find_all('a', href=True):
                    link = urljoin(url, a['href'])
                    parsed_link = urlparse(link)
                    if parsed_link.netloc == base_netloc and link not in visited and link.startswith('http'):
                        to_visit.append(link)
            except Exception as ex:
                print(f"  Error visiting {url}: {ex}")
                continue
        print(f"Crawling finished. Visited {len(visited)} pages. Found {len(found_emails)} unique emails.")
        return results

    def scrape_page(self, url):
        # For compatibility: scrape a single page or PDF
        try:
            if url.lower().endswith('.pdf'):
                resp = requests.get(url, timeout=15)
                text = extract_text(BytesIO(resp.content))
                emails = self.extract_emails(text)
                results = []
                for e in emails:
                    info = self.extract_info_from_email(e)
                    results.append({
                        'email': e,
                        'name': self.clean_info_field(info.get('name','')),
                        'office': self.clean_info_field(info.get('office','')),
                        'department': self.clean_info_field(info.get('department',''))
                    })
                return results
            else:
                resp = requests.get(url, timeout=10)
                soup = BeautifulSoup(resp.text, 'html.parser')
                text = soup.get_text()
                emails = self.extract_emails(text)
                return [dict(email=e,
                    name=self.clean_info_field(info.get('name','')),
                    office=self.clean_info_field(info.get('office','')),
                    department=self.clean_info_field(info.get('department',''))
                ) for e in emails for info in [self.extract_info_near_email(soup, e)]]
        except Exception as ex:
            print(f"  Error scraping {url}: {ex}")
            return []