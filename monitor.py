import os
import requests
from playwright.sync_api import sync_playwright, TimeoutError

PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")

def send_telegram_message(message):
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }

    response = requests.post(url, data=payload)
    print("Telegram response:", response.text)


def check_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Opening portal...")
        page.goto(PORTAL_URL, timeout=60000)

        page.wait_for_selector("select", timeout=60000)

        print("Selecting Student from dropdown...")
        page.select_option("select", label="Student")

        print("Clicking Continue...")
        page.click("#btncontinue")

        print("Waiting for login form...")
        page.wait_for_selector("input[type='password']", timeout=60000)

        print("Entering credentials...")
        page.fill("input[type='text']", PORTAL_USER)
        page.fill("input[type='password']", PORTAL_PASS)

        print("Submitting login...")
        page.click("input[type='submit'], button")

        page.wait_for_load_state("networkidle")

        print("Login successful.")

        # CLICK MORE
        print("Clicking More...")
        page.click("a[href='I7']")
        page.wait_for_load_state("networkidle")

        print("Waiting for consultation table...")
        page.wait_for_selector("#Griddets", timeout=60000)

        rows = page.query_selector_all("#Griddets tbody tr")

        print(f"Total rows found: {len(rows)-1}")

        new_found = False

        # ✅ LOOP MUST BE INSIDE FUNCTION
        for row in rows[1:]:  # skip header
            cols = row.query_selector_all("td")
            if len(cols) < 5:
                continue

            request_no = cols[1].inner_text().strip()
            department = cols[4].inner_text().strip()

            print(f"Checking → {request_no} | {department}")

            # TEST CONDITION
            if "M.Sc.RRT&DT" in department.lower():

                print("🚨 TEST MATCH FOUND!")
                print(f"Request No: {request_no}")
                print(f"Department: {department}")
                print("-" * 40)

                send_telegram_message(
                    f"🚨 TEST ALERT\n"
                    f"Request: {request_no}\n"
                    f"Department: {department}"
                )

                new_found = True

        if not new_found:
            print("No Physiology consultations found.")

        browser.close()


if __name__ == "__main__":
    try:
        check_slots()
    except TimeoutError:
        print("Timeout occurred.")
        raise
