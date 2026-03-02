import json
import os
from playwright.sync_api import sync_playwright

PORTAL_URL = "https://portal.manipal.edu"

USERNAME = os.getenv("PORTAL_USERNAME")
PASSWORD = os.getenv("PORTAL_PASSWORD")

SEEN_FILE = "seen_requests.json"


# -------------------------------
# Persistent Storage
# -------------------------------

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(data), f)


# -------------------------------
# Notification
# -------------------------------

def send_notification(request_no):
    print(f"🚨 NEW MSc Data Science Consultation Found: {request_no}")
    # Later we can add Telegram/Email here


# -------------------------------
# Main Logic
# -------------------------------

def check_slots():
    seen_requests = load_seen()
    current_requests = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Opening portal...")
        page.goto(PORTAL_URL, timeout=60000)

        # -------------------------------
        # LOGIN FLOW (Keep your working logic)
        # -------------------------------

        print("Selecting Student from dropdown...")
        page.select_option("select", label="Student")

        print("Clicking Continue...")
        page.click("button:has-text('Continue')")

        print("Waiting for login form...")
        page.wait_for_selector("input[type='password']")

        print("Entering credentials...")
        page.fill("input[type='text']", USERNAME)
        page.fill("input[type='password']", PASSWORD)

        print("Submitting login...")
        page.click("button:has-text('Login')")

        page.wait_for_load_state("networkidle")
        print("Login successful.")

        # -------------------------------
        # CLICK "more" (I7)
        # -------------------------------

        print("Clicking 'more' button...")
        page.wait_for_selector("a[href='I7']")
        page.click("a[href='I7']")

        # Wait until Consultation Details page loads
        page.wait_for_url("**/statistics/I7")
        page.wait_for_selector("#Griddets")

        print("Consultation page loaded.")

        # -------------------------------
        # PARSE TABLE
        # -------------------------------

        rows = page.query_selector_all("#Griddets tbody tr")

        for row in rows[1:]:  # Skip header
            cells = row.query_selector_all("td")

            # Skip pagination row
            if len(cells) < 5:
                continue

            request_no = cells[1].inner_text().strip()
            department = cells[4].inner_text().strip().lower()

            # Filter MSc Data Science
            if "msc data science" in department:
                current_requests.add(request_no)

                if request_no not in seen_requests:
                    send_notification(request_no)

        # -------------------------------
        # SAVE STATE
        # -------------------------------

        seen_requests.update(current_requests)
        save_seen(seen_requests)

        browser.close()

    print("Slot check completed.")


# -------------------------------
# Run Script
# -------------------------------

if __name__ == "__main__":
    check_slots()
