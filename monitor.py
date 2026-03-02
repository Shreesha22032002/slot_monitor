import os
import requests
from playwright.sync_api import sync_playwright, TimeoutError

# ===============================
# ENV VARIABLES
# ===============================
PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Department to monitor (change here if needed)
TARGET_DEPARTMENT = "data science"

SEEN_FILE = "seen_requests.txt"


# ===============================
# TELEGRAM FUNCTION
# ===============================
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=payload)
    print("Telegram response:", response.text)


# ===============================
# FILE HANDLING
# ===============================
def load_seen_requests():
    if not os.path.exists(SEEN_FILE):
        return set()

    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_seen_requests(seen):
    with open(SEEN_FILE, "w") as f:
        for req in seen:
            f.write(req + "\n")


# ===============================
# MAIN MONITOR FUNCTION
# ===============================
def check_slots():
    seen_requests = load_seen_requests()

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

        # ===============================
        # CLICK MORE (I7 PAGE)
        # ===============================
        print("Clicking More...")
        page.click("a[href='I7']")
        page.wait_for_load_state("networkidle")

        # ===============================
        # CHECK UPCOMING CONSULTATIONS
        # ===============================
        print("Waiting for Upcoming Consultations table...")
        page.wait_for_selector("#Panel1 table", timeout=60000)

        rows = page.query_selector_all("#Panel1 table tbody tr")
        print(f"Upcoming rows found: {len(rows)}")

        new_found = False

        for row in rows:
            cols = row.query_selector_all("td")

            # Skip invalid rows
            if len(cols) < 5:
                continue

            request_no = cols[1].inner_text().strip()
            department = cols[4].inner_text().strip()

            # Ignore pagination rows
            if not request_no.startswith("STAT"):
                continue

            print(f"Checking → {request_no} | {department}")

            # ===============================
            # FILTER FOR DATA SCIENCE
            # ===============================
            if TARGET_DEPARTMENT not in department.lower():
                continue

            # ===============================
            # DUPLICATE CHECK
            # ===============================
            if request_no not in seen_requests:

                print("🚨 NEW DATA SCIENCE CONSULTATION FOUND!")
                print(f"Request No: {request_no}")
                print(f"Department: {department}")
                print("-" * 40)

                send_telegram_message(
                    f"🚨 NEW DATA SCIENCE CONSULTATION\n"
                    f"Request: {request_no}\n"
                    f"Department: {department}"
                )

                seen_requests.add(request_no)
                new_found = True

        if not new_found:
            print("No new Data Science upcoming consultations.")

        save_seen_requests(seen_requests)
        browser.close()


# ===============================
# ENTRY POINT
# ===============================
if __name__ == "__main__":
    try:
        check_slots()
    except TimeoutError:
        print("Timeout occurred.")
        raise
