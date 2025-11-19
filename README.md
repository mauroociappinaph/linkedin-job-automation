# LinkedIn Job Automation

Automated job application system for LinkedIn with GitHub Actions

## Features
- ✅ Automatic daily job searches across Spanish-speaking countries
- ✅ Easy Apply submissions with intelligent form handling
- ✅ Google Sheets integration for tracking applications
- ✅ Runs daily at 08:00 AM GMT-3

## Setup

1. Clone this repository
2. Configure GitHub Secrets (see below)
3. GitHub Actions will run automatically

## Required Secrets

- `LINKEDIN_SESSION`: Your LinkedIn `li_at` session cookie
- `GOOGLE_SHEETS_CREDS`: Google Service Account JSON
- `GOOGLE_SHEET_ID`: Your Google Sheet ID

## Countries Supported
- Argentina
- Spain
- Mexico
- Colombia
- Chile
- Peru

Made with ❤️ by Mauro
