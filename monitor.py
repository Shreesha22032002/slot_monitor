from playwright.sync_api import sync_playwright
import os

PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")

def check_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://portal.manipal.edu/statistics/I11")

        # Wait for dropdown
        page.wait_for_selector("select")

        # Select Student
        page.select_option("select", label="Student")

        # IMPORTANT: Wait for postback reload
        page.wait_for_load_state("networkidle")

        # Wait for username field (type=text usually)
        page.wait_for_selector("input[type='text']")

        # Fill username
        page.fill("input[type='text']", PORTAL_USER)

        # Fill password (usually type=password)
        page.fill("input[type='password']", PORTAL_PASS)

        # Click login button
        page.click("input[type='submit'], button")

        page.wait_for_load_state("networkidle")

        print("Login successful")

        browser.close()

if __name__ == "__main__":
    check_slots()
