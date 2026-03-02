import os
from playwright.sync_api import sync_playwright, TimeoutError

PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")

def check_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Opening portal...")
        page.goto(PORTAL_URL, timeout=60000)

        # Wait for dropdown
        page.wait_for_selector("select", timeout=60000)

        print("Selecting Student from dropdown...")
        page.select_option("select", label="Student")

        print("Clicking Continue...")
        page.click("#btncontinue")

        # ASP.NET postback — wait for login fields instead of navigation
        print("Waiting for login form...")
        page.wait_for_selector("input[type='password']", timeout=60000)

        print("Entering credentials...")
        page.fill("input[type='text']", PORTAL_USER)
        page.fill("input[type='password']", PORTAL_PASS)

        print("Submitting login...")
        page.click("input[type='submit'], button")

        # Wait for dashboard / next page
        page.wait_for_load_state("networkidle")

        print("Login successful. Checking slots...")

        # TODO: Add your slot checking logic here
        # Example:
        # page.wait_for_selector("text=No slots available", timeout=30000)

        print("Slot check completed.")

        browser.close()


if __name__ == "__main__":
    try:
        check_slots()
    except TimeoutError:
        print("Timeout occurred. Saving screenshot for debugging...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.screenshot(path="error.png")
            browser.close()
        raise
