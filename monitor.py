import os
import time
from playwright.sync_api import sync_playwright, TimeoutError

PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")

SEEN_FILE = "seen_requests.txt"


def load_seen_requests():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_seen_requests(seen):
    with open(SEEN_FILE, "w") as f:
        for req in seen:
            f.write(req + "\n")


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

        # -------------------------
        # CLICK "MORE"
        # -------------------------
        print("Clicking More...")
        page.click("a[href='I7']")
        page.wait_for_load_state("networkidle")

        print("Waiting for consultation table...")
        page.wait_for_selector("#Griddets", timeout=60000)

        rows = page.query_selector_all("#Griddets tbody tr")

        print(f"Total rows found: {len(rows)-1}")

        new_found = False

        # Skip header row (first row)
        for row in rows[1:]:
            cols = row.query_selector_all("td")
            if len(cols) < 5:
                continue

            request_no = cols[1].inner_text().strip()
            department = cols[4].inner_text().strip().lower()

            if department == "msc data science":
                if request_no not in seen_requests:
                    print("🚨 NEW CONSULTATION FOUND!")
                    print(f"Request No: {request_no}")
                    print(f"Department: {department}")
                    print("-" * 40)

                    seen_requests.add(request_no)
                    new_found = True

        if not new_found:
            print("No new Msc Data Science consultations.")

        save_seen_requests(seen_requests)

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
