#!/usr/bin/env python3
"""
LinkedIn Job Automation Script
Automatically applies to LinkedIn jobs with Easy Apply in Spanish-speaking countries
Tracks all applications in Google Sheets
"""

import os
import json
import time
import random
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
MAX_APPLICATIONS_PER_DAY = random.randint(20, 30)
APPLICATION_DELAY = 5

# Target countries
TARGET_COUNTRIES = [
    "Argentina", "Spain", "Mexico", "Colombia", "Chile", "Peru", "Uruguay",
    "Paraguay", "Bolivia", "Ecuador", "Venezuela", "Costa Rica", "Panama",
    "Guatemala", "El Salvador", "Honduras", "Nicaragua", "Dominican Republic"
]

class LinkedInJobAutomation:
    def __init__(self):
        self.driver = None
        self.sheets_client = None
        self.worksheet = None
        self.applications_count = 0

    def initialize_driver(self):
        """Initialize Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)

    def setup_google_sheets(self):
        """Setup Google Sheets connection using service account"""
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDS')
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        
        if not credentials_json or not sheet_id:
            raise ValueError("Missing GOOGLE_SHEETS_CREDS or GOOGLE_SHEET_ID environment variables")
        
        credentials_dict = json.loads(credentials_json)
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        self.sheets_client = gspread.authorize(credentials)
        self.worksheet = self.sheets_client.open_by_key(sheet_id).sheet1

    def authenticate_linkedin_with_cookies(self):
        """Authenticate to LinkedIn using cookies instead of email/password"""
        try:
            # Get cookies from environment variables
            li_at = os.environ.get('LINKEDIN_LI_AT')
            jsessionid = os.environ.get('LINKEDIN_JSESSIONID')
            lidc = os.environ.get('LINKEDIN_LIDC')
            
            if not all([li_at, jsessionid, lidc]):
                raise ValueError("Missing LinkedIn cookies (LINKEDIN_LI_AT, LINKEDIN_JSESSIONID, LINKEDIN_LIDC)")
            
            # Navigate to LinkedIn
            self.driver.get('https://www.linkedin.com/feed/')
            time.sleep(2)
            
            # Add cookies to the browser
            self.driver.add_cookie({
                'name': 'li_at',
                'value': li_at,
                'domain': '.linkedin.com',
                'path': '/'
            })
            self.driver.add_cookie({
                'name': 'JSESSIONID',
                'value': jsessionid,
                'domain': '.linkedin.com',
                'path': '/'
            })
            self.driver.add_cookie({
                'name': 'lidc',
                'value': lidc,
                'domain': '.linkedin.com',
                'path': '/'
            })
            
            # Refresh page to apply cookies
            self.driver.refresh()
            time.sleep(3)
            
            # Verify we're logged in by checking for mynetwork link
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[@href='/mynetwork/']"))
                )
                print("✓ Successfully authenticated to LinkedIn via cookies")
            except:
                print("✗ Failed to verify LinkedIn authentication")
                raise Exception("Authentication verification failed")
                
        except Exception as e:
            print(f"❌ Error during LinkedIn authentication: {str(e)}")
            raise

    def search_jobs_in_country(self, country):
        """Search for jobs in a specific country with Easy Apply filter"""
        try:
            base_url = "https://www.linkedin.com/jobs/search/"
            params = {
                'keywords': 'fullstack developer',
                'location': country,
                'f_WT': '1',
                'f_EA': 'true',
                'salary': f'{MIN_SALARY_USD}000-'
            }
            
            url = base_url + "?" + "&".join([f"{k}={v}" for k, v in params.items()])
            self.driver.get(url)
            time.sleep(3)
            
            return self.get_job_listings()
        except Exception as e:
            print(f"✗ Error searching jobs in {country}: {str(e)}")
            return []

    def get_job_listings(self):
        """Extract job listings from current page"""
        jobs = []
        try:
            job_cards = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "base-card"))
            )
            
            for card in job_cards[:10]:
                try:
                    title = card.find_element(By.CLASS_NAME, "base-search-card__title").text
                    company = card.find_element(By.CLASS_NAME, "base-search-card__subtitle").text
                    link = card.find_element(By.CLASS_NAME, "base-card__full-link").get_attribute("href")
                    jobs.append({
                        'title': title,
                        'company': company,
                        'link': link
                    })
                except:
                    continue
        except:
            pass
        
        return jobs

    def apply_to_job(self, job_url, job_title, company, country):
        """Apply to a specific job"""
        try:
            self.driver.get(job_url)
            time.sleep(2)
            
            # Find and click Easy Apply button
            easy_apply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Easy Apply')]"))
            )
            easy_apply_button.click()
            time.sleep(2)
            
            # Handle any form fields that appear
            self.handle_application_form()
            
            # Submit application
            submit_button = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Enviar')]")[-1]
            submit_button.click()
            
            # Log to Google Sheets
            self.log_application(job_title, company, country, job_url, "Postulado")
            self.applications_count += 1
            print(f"✓ Applied to {job_title} at {company}")
            return True
        except Exception as e:
            print(f"✗ Failed to apply to {job_title}: {str(e)}")
            return False

    def handle_application_form(self):
        """Handle form fields in application modal"""
        try:
            time.sleep(2)
            text_inputs = self.driver.find_elements(By.XPATH, "//input[@type='text']")
            for inp in text_inputs:
                try:
                    inp.send_keys("Automated")
                except:
                    pass
        except:
            pass

    def log_application(self, title, company, country, link, status):
        """Log application to Google Sheets"""
        try:
            today = datetime.now().strftime("%d/%m/%Y")
            row = [
                self.applications_count + 1,
                today,
                title,
                company,
                country,
                link,
                f"${MIN_SALARY_USD}+",
                status,
                "Automated"
            ]
            self.worksheet.append_row(row)
            print(f"✓ Logged to Google Sheets: {title}")
        except Exception as e:
            print(f"✗ Failed to log to sheets: {str(e)}")

    def run(self):
        """Main execution function"""
        try:
            print("🚀 Starting LinkedIn Job Automation...")
            self.initialize_driver()
            self.setup_google_sheets()
            self.authenticate_linkedin_with_cookies()
            
            for country in TARGET_COUNTRIES:
                if self.applications_count >= MAX_APPLICATIONS_PER_DAY:
                    break
                
                print(f"\n🔍 Searching jobs in {country}...")
                jobs = self.search_jobs_in_country(country)
                
                for job in jobs:
                    if self.applications_count >= MAX_APPLICATIONS_PER_DAY:
                        break
                    
                    if self.apply_to_job(job['link'], job['title'], job['company'], country):
                        time.sleep(APPLICATION_DELAY)
            
            print(f"\n✅ Completed! Applied to {self.applications_count} jobs")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    automation = LinkedInJobAutomation()
    automation.run()
