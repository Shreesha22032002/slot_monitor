from playwright.sync_api import sync_playwright
import os
import requests

PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

URL = "https://portal.manipal.edu/statistics/I11"


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing")
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    requests.post(telegram_url, data=payload)


def check_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Opening portal...")
        page.goto(URL, timeout=60000)

        # Wait for dropdown
        page.wait_for_selector("select", timeout=30000)

        print("Selecting Student from dropdown...")

        # Proper ASP.NET postback handling
        with page.expect_navigation():
            page.select_option("select", label="Student")

        print("Waiting for login fields...")

        # Wait for login fields after postback
        page.wait_for_selector("input[type='text']", timeout=30000)
        page.wait_for_selector("input[type='password']", timeout=30000)

        print("Filling login details...")

        page.fill("input[type='text']", PORTAL_USER)
        page.fill("input[type='password']", PORTAL_PASS)

        print("Submitting login...")

        with page.expect_navigation():
            page.click("input[type='submit'], button")

        print("Login successful. Checking page content...")

        page.wait_for_load_state("networkidle")

        content = page.content()

        if "Msc Data Science" in content:
            print("Msc Data Science FOUND!")
            send_telegram("🚨 New update found for Msc Data Science!")
        else:
            print("No new MSc Data Science updates.")

        browser.close()


if __name__ == "__main__":
    check_slots()
