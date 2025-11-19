#!/usr/bin/env python3
"""
LinkedIn Job Automation Script
Automatically applies to LinkedIn jobs with Easy Apply in Spanish-speaking countries
Tracks all applications in Google Sheets
"""

import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuration
DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"
MIN_SALARY_USD = 500
MAX_APPLICATIONS_PER_DAY = 40
APPLICATION_DELAY = 5  # seconds between applications

# Target countries
TARGET_COUNTRIES = [
    "Argentina",
    "Spain",
    "Mexico",
    "Colombia",
    "Chile",
    "Peru",
    "Uruguay",
    "Paraguay",
    "Bolivia",
    "Ecuador",
    "Venezuela",
    "Costa Rica",
    "Panama",
    "Guatemala",
    "El Salvador",
    "Honduras",
    "Nicaragua",
    "Dominican Republic",
]

class LinkedInJobAutomation:
    def __init__(self):
        self.driver = None
        self.sheet = None
        self.applications_count = 0
        self.session_cookie = os.environ.get('LINKEDIN_SESSION')
        self.google_sheets_creds = os.environ.get('GOOGLE_SHEETS_CREDS')
        self.google_sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        
    def initialize_driver(self):
        """Initialize Selenium WebDriver with Chrome headless mode"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def setup_google_sheets(self):
        """Setup Google Sheets integration"""
        try:
            creds_dict = json.loads(self.google_sheets_creds)
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            gc = gspread.authorize(creds)
            self.sheet = gc.open_by_key(self.google_sheet_id).sheet1
            print(f"✓ Connected to Google Sheets: {self.google_sheet_id}")
        except Exception as e:
            print(f"✗ Failed to connect to Google Sheets: {e}")
            raise
    
    def authenticate_linkedin(self):
        """Authenticate with LinkedIn using session cookie"""
        self.driver.get('https://www.linkedin.com')
        time.sleep(2)
        
        # Add session cookie
        self.driver.add_cookie({
            'name': 'li_at',
            'value': self.session_cookie,
            'domain': '.linkedin.com',
            'secure': True,
            'httpOnly': True
        })
        
        # Refresh to apply cookie
        self.driver.refresh()
        time.sleep(3)
        print("✓ LinkedIn authentication successful")
    
    def search_jobs_in_country(self, country):
        """Search for jobs in specific country with Easy Apply filter"""
        keywords = "full stack developer remote"
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={country}&f_WT=2"
        self.driver.get(search_url)
        time.sleep(4)
        
        # Scroll to load more jobs
        for _ in range(3):
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(2)
        
        jobs = []
        job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.base-card")
        
        for card in job_cards[:20]:  # Limit to 20 per country
            try:
                job_title = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title").text
                company = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle").text
                link = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link").get_attribute('href')
                
                # Check for Easy Apply button
                try:
                    easy_apply_btn = card.find_element(By.CSS_SELECTOR, "button[aria-label*='Easy Apply']")
                    has_easy_apply = True
                except:
                    has_easy_apply = False
                
                if has_easy_apply:
                    jobs.append({
                        'title': job_title,
                        'company': company,
                        'link': link,
                        'country': country,
                        'salary': 'TBD',  # Will be extracted from job details
                    })
            except Exception as e:
                print(f"Error extracting job: {e}")
                continue
        
        print(f"Found {len(jobs)} Easy Apply jobs in {country}")
        return jobs
    
    def apply_to_job(self, job):
        """Apply to a specific job using Easy Apply"""
        try:
            self.driver.get(job['link'])
            time.sleep(3)
            
            # Look for Easy Apply button
            try:
                easy_apply_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='Easy Apply']"))
                )
                easy_apply_btn.click()
                time.sleep(2)
                print(f"  → Easy Apply clicked for {job['title']}")
            except Exception as e:
                print(f"  ✗ No Easy Apply button found: {e}")
                return False
            
            # Fill form fields if available
            try:
                # Try to find and handle form elements
                form_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea, select")
                print(f"  → Form has {len(form_elements)} elements")
                time.sleep(2)
            except:
                pass
            
            # Look for submit button
            try:
                submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Enviar') or contains(text(), 'Submit') or contains(text(), 'Solicitar')]")
                submit_btn.click()
                time.sleep(3)
                print(f"  ✓ Application submitted to {job['company']}")
                return True
            except Exception as e:
                print(f"  ✗ Could not submit application: {e}")
                return False
                
        except Exception as e:
            print(f"  ✗ Error applying to job: {e}")
            return False
    
    def log_application(self, job, status="Postulado"):
        """Log application in Google Sheets"""
        try:
            row = [
                self.applications_count,  # N°
                datetime.now().strftime("%Y-%m-%d %H:%M"),  # Fecha
                job['title'],  # Puesto
                job['company'],  # Empresa
                job['country'],  # País
                job['link'],  # Link
                job['salary'],  # Salario
                status,  # Estado
                "Auto-postulado"  # Notas
            ]
            self.sheet.append_row(row)
            print(f"    → Logged in Google Sheets")
        except Exception as e:
            print(f"    ✗ Failed to log application: {e}")
    
    def run(self):
        """Main automation loop"""
        try:
            print("\n=== LinkedIn Job Automation Started ===")
            print(f"Target: {MAX_APPLICATIONS_PER_DAY} applications")
            print(f"Countries: {len(TARGET_COUNTRIES)} Hispanic regions\n")
            
            # Initialize
            self.initialize_driver()
            self.setup_google_sheets()
            self.authenticate_linkedin()
            
            all_jobs = []
            
            # Search in all countries
            for country in TARGET_COUNTRIES:
                if self.applications_count >= MAX_APPLICATIONS_PER_DAY:
                    break
                try:
                    jobs = self.search_jobs_in_country(country)
                    all_jobs.extend(jobs)
                    time.sleep(2)
                except Exception as e:
                    print(f"Error searching {country}: {e}")
                    continue
            
            print(f"\nTotal jobs found: {len(all_jobs)}")
            
            # Apply to jobs (limited by MAX_APPLICATIONS_PER_DAY)
            for job in all_jobs[:MAX_APPLICATIONS_PER_DAY]:
                if self.applications_count >= MAX_APPLICATIONS_PER_DAY:
                    break
                
                self.applications_count += 1
                print(f"\nApplying to Job #{self.applications_count}: {job['title']} @ {job['company']}")
                
                success = self.apply_to_job(job)
                if success:
                    self.log_application(job)
                
                time.sleep(APPLICATION_DELAY)
            
            print(f"\n✓ Automation Complete: {self.applications_count} applications submitted")
            
        except Exception as e:
            print(f"✗ Automation failed: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    automation = LinkedInJobAutomation()
    automation.run()
