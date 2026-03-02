import os
import requests
from playwright.sync_api import sync_playwright

PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": message})


def check_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://portal.manipal.edu/statistics/I11")

        # --- Step 1: Select "Student" from dropdown ---
        page.select_option("select", label="Student")

        # --- Step 2: Login ---
        page.fill("input[name='username']", PORTAL_USER)
        page.fill("input[name='password']", PORTAL_PASS)
        page.click("button[type='submit']")

        page.wait_for_load_state("networkidle")

        # --- Step 3: Check table content ---
        page_content = page.content()

        if "MSc Data Science" in page_content:
            send_telegram("🚨 New MSc Data Science entry detected!")

        browser.close()


if __name__ == "__main__":
    check_slots()
