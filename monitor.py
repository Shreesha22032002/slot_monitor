import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

# ===============================
# ENV VARIABLES
# ===============================
PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Department / Course filter
TARGET_DEPARTMENT = "data science"

SEEN_FILE = "seen_requests.txt"


# ===============================
# TELEGRAM FUNCTION
# ===============================
def send_telegram_message(message):
    print("Sending Telegram notification...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=payload)
    print("Telegram response:", response.status_code)


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
    print("\n" + "=" * 70)
    print("RUN STARTED:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    seen_requests = load_seen_requests()
    print(f"Loaded {len(seen_requests)} previously seen requests.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # -------------------------------
            # OPEN PORTAL
            # -------------------------------
            print("Opening portal...")
            page.goto(PORTAL_URL, timeout=60000)

            page.wait_for_selector("select", timeout=60000)

            print("Selecting Student from dropdown...")
            page.select_option("select", label="Student")

            print("Clicking Continue...")
            page.click("#btncontinue")

            # -------------------------------
            # LOGIN
            # -------------------------------
            print("Waiting for login form...")
            page.wait_for_selector("input[type='password']", timeout=60000)

            print("Entering credentials...")
            page.fill("input[type='text']", PORTAL_USER)
            page.fill("input[type='password']", PORTAL_PASS)

            print("Submitting login...")
            page.click("input[type='submit'], button")

            page.wait_for_load_state("networkidle")
            print("Login successful.")

            # -------------------------------
            # CLICK MORE (I7 PAGE)
            # -------------------------------
            print("Clicking More (I7 page)...")
            page.click("a[href='I7']")
            page.wait_for_load_state("networkidle")

            # -------------------------------
            # WAIT FOR TABLE
            # -------------------------------
            print("Waiting for Upcoming Consultations table...")
            page.wait_for_selector("#Panel1 table", timeout=60000)

            rows = page.query_selector_all("#Panel1 table tbody tr")
            print(f"Total rows found (including header/pagination): {len(rows)}")

            new_found = False

            # -------------------------------
            # PROCESS ROWS
            # -------------------------------
            for index, row in enumerate(rows):

                cols = row.query_selector_all("td")

                # Skip header or pagination rows
                if len(cols) < 12:
                    continue

                request_no = cols[1].inner_text().strip()
                course = cols[6].inner_text().strip()

                if not request_no.startswith("STAT"):
                    continue

                print("\n-----------------------------------")
                print(f"Checking Row {index}")
                print(f"Request: {request_no}")
                print(f"Course: {course}")

                # -------------------------------
                # FILTER: DATA SCIENCE ONLY
                # -------------------------------
                if TARGET_DEPARTMENT not in course.lower():
                    print("Not Data Science → Skipping")
                    continue

                print("Data Science row detected!")

                # -------------------------------
                # DUPLICATE CHECK
                # -------------------------------
                if request_no in seen_requests:
                    print("Already processed before → Skipping duplicate")
                    continue

                # -------------------------------
                # CHECK CHECKBOX STATE
                # -------------------------------
                checkbox_cell = cols[0]

                disabled_span = checkbox_cell.query_selector(".aspNetDisabled")

                if disabled_span:
                    print("Checkbox is DISABLED → No action taken")
                    continue

                print("Checkbox is ENABLED → Clicking")

                checkbox = checkbox_cell.query_selector("input[type='checkbox']")

                if checkbox:
                    checkbox.click()
                    print("Checkbox clicked successfully")

                    send_telegram_message(
                        f"🚨 NEW DATA SCIENCE CONSULTATION 🚨\n\n"
                        f"Request: {request_no}\n"
                        f"Course: {course}"
                    )

                    seen_requests.add(request_no)
                    new_found = True
                else:
                    print("Checkbox not found (unexpected DOM structure)")

            if not new_found:
                print("\nNo new enabled Data Science consultations found.")

            save_seen_requests(seen_requests)

        except TimeoutError:
            print("Timeout occurred while loading elements.")
        except Exception as e:
            print("Unexpected error:", e)
        finally:
            browser.close()

    print("=" * 70)
    print("RUN FINISHED")
    print("=" * 70)


# ===============================
# ENTRY POINT
# ===============================
if __name__ == "__main__":
    check_slots()
