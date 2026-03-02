import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

# ===============================
# CONFIG
# ===============================
PORTAL_URL = os.getenv("PORTAL_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TARGET_DEPARTMENT = "data science"
SEEN_FILE = "seen_requests.txt"

CHECK_INTERVAL = 60  # seconds


# ===============================
# TELEGRAM
# ===============================
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        response = requests.post(url, data=payload, timeout=15)
        print("Telegram response:", response.status_code)
    except Exception as e:
        print("Telegram error:", e)


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
# MAIN CHECK FUNCTION
# ===============================
def check_slots():
    print("\n" + "=" * 70)
    print("CHECK STARTED:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    seen_requests = load_seen_requests()
    print(f"Seen requests loaded: {len(seen_requests)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ---------------------------
            # OPEN PORTAL
            # ---------------------------
            print("Opening portal...")
            page.goto(PORTAL_URL, timeout=60000)
            page.wait_for_selector("select", timeout=60000)

            print("Selecting Student...")
            page.select_option("select", label="Student")
            page.click("#btncontinue")

            # ---------------------------
            # LOGIN
            # ---------------------------
            page.wait_for_selector("input[type='password']", timeout=60000)
            page.fill("input[type='text']", PORTAL_USER)
            page.fill("input[type='password']", PORTAL_PASS)
            page.click("input[type='submit'], button")

            page.wait_for_load_state("networkidle")
            print("Login successful.")

            # ---------------------------
            # GO TO I7 PAGE
            # ---------------------------
            page.click("a[href='I7']")
            page.wait_for_load_state("networkidle")

            # ---------------------------
            # WAIT FOR TABLE
            # ---------------------------
            page.wait_for_selector("#Panel1 table", timeout=60000)
            rows = page.query_selector_all("#Panel1 table tbody tr")

            print(f"Rows detected: {len(rows)}")

            new_found = False

            for index, row in enumerate(rows):
                cols = row.query_selector_all("td")

                if len(cols) < 12:
                    continue

                request_no = cols[1].inner_text().strip()
                course = cols[6].inner_text().strip()

                if not request_no.startswith("STAT"):
                    continue

                print("\n-----------------------------------")
                print(f"Checking: {request_no}")
                print(f"Course: {course}")

                if TARGET_DEPARTMENT not in course.lower():
                    print("Not Data Science → Skipping")
                    continue

                print("Data Science detected!")

                if request_no in seen_requests:
                    print("Already processed → Skipping")
                    continue

                checkbox_cell = cols[0]
                disabled_span = checkbox_cell.query_selector(".aspNetDisabled")

                # ==========================
                # CASE 1: DISABLED
                # ==========================
                if disabled_span:
                    print("Checkbox DISABLED → Cannot book")

                    send_telegram_message(
                        f"🔴 DATA SCIENCE DETECTED BUT CANNOT BOOK\n\n"
                        f"Request: {request_no}\n"
                        f"Course: {course}\n"
                        f"Status: Already booked / Disabled"
                    )

                    seen_requests.add(request_no)
                    new_found = True
                    continue

                # ==========================
                # CASE 2: ENABLED
                # ==========================
                print("Checkbox ENABLED → Attempting booking")

                checkbox = checkbox_cell.query_selector("input[type='checkbox']")

                try:
                    checkbox.click()
                    print("Checkbox clicked successfully")

                    send_telegram_message(
                        f"🟢 DATA SCIENCE DETECTED & BOOKED\n\n"
                        f"Request: {request_no}\n"
                        f"Course: {course}\n"
                        f"Status: Successfully booked"
                    )

                except Exception as e:
                    print("Booking failed:", e)

                    send_telegram_message(
                        f"⚠ DATA SCIENCE DETECTED BUT BOOKING FAILED\n\n"
                        f"Request: {request_no}\n"
                        f"Course: {course}\n"
                        f"Error: {str(e)}"
                    )

                seen_requests.add(request_no)
                new_found = True

            if not new_found:
                print("No new Data Science rows this cycle.")

            save_seen_requests(seen_requests)

        except TimeoutError:
            print("Timeout occurred during navigation.")
        except Exception as e:
            print("Unexpected error:", e)
        finally:
            browser.close()

    print("=" * 70)
    print("CHECK FINISHED")
    print("=" * 70)


# ===============================
# CONTINUOUS LOOP
# ===============================
if __name__ == "__main__":
    print("Starting Continuous Monitor...")
    print(f"Checking every {CHECK_INTERVAL} seconds.\n")

    while True:
        try:
            check_slots()
        except Exception as e:
            print("Critical loop error:", e)

        print(f"\nSleeping for {CHECK_INTERVAL} seconds...\n")
        time.sleep(CHECK_INTERVAL)
