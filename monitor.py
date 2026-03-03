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

SEEN_FILE = "seen_requests.txt"
CHECK_INTERVAL = 5  # seconds

# ===============================
# TELEGRAM
# ===============================
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload, timeout=15)
        print(f"Telegram alert sent. Status: {response.status_code}")
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ---------------------------
            # LOGIN & NAVIGATION
            # ---------------------------
            page.goto(PORTAL_URL, timeout=60000)
            page.wait_for_selector("select", timeout=60000)
            page.select_option("select", label="Student")
            page.click("#btncontinue")

            page.wait_for_selector("input[type='password']", timeout=60000)
            page.fill("input[type='text']", PORTAL_USER)
            page.fill("input[type='password']", PORTAL_PASS)
            page.click("input[type='submit'], button")

            page.wait_for_load_state("networkidle")
            page.click("a[href='I7']")
            page.wait_for_load_state("networkidle")

            # ---------------------------
            # TABLE SCANNING
            # ---------------------------
            page.wait_for_selector("#Panel1 table", timeout=60000)
            rows = page.query_selector_all("#Panel1 table tbody tr")

            new_found_this_cycle = False

            for row in rows:
                cols = row.query_selector_all("td")
                if len(cols) < 12:
                    continue

                request_no = cols[1].inner_text().strip()
                course_name = cols[6].inner_text().strip()

                # Filter: Only process if it's a new Request ID
                if request_no in seen_requests:
                    continue

                # --- NEW ROW DISCOVERED ---
                new_found_this_cycle = True
                print(f"NEW ITEM DETECTED: {request_no} - {course_name}")

                checkbox_cell = cols[0]
                disabled_span = checkbox_cell.query_selector(".aspNetDisabled")

                # CASE 1: NEW BUT CANNOT BOOK (DISABLED)
                if disabled_span:
                    print(f"Outcome: Detected but disabled.")
                    send_telegram_message(
                        f"⚠️ *NEW ROW DETECTED (LOCKED)*\n\n"
                        f"🆔 *ID:* `{request_no}`\n"
                        f"📚 *Course:* {course_name}\n"
                        f"❌ *Status:* Cannot book (Greyed out/Full)"
                    )
                
                # CASE 2: NEW AND ATTEMPTING BOOKING
                else:
                    checkbox = checkbox_cell.query_selector("input[type='checkbox']")
                    try:
                        checkbox.click()
                        print("Outcome: Booked successfully.")
                        send_telegram_message(
                            f"✅ *NEW ROW DETECTED & BOOKED*\n\n"
                            f"🆔 *ID:* `{request_no}`\n"
                            f"📚 *Course:* {course_name}\n"
                            f"🚀 *Status:* Clicked Successfully"
                        )
                    except Exception as e:
                        print(f"Outcome: Click failed: {e}")
                        send_telegram_message(
                            f"🚨 *NEW ROW FOUND BUT BOOKING FAILED*\n\n"
                            f"🆔 *ID:* `{request_no}`\n"
                            f"📚 *Course:* {course_name}\n"
                            f"❌ *Error:* {str(e)}"
                        )

                # Save ID immediately so we don't alert twice
                seen_requests.add(request_no)

            if not new_found_this_cycle:
                print("No new updates found.")

            save_seen_requests(seen_requests)

        except Exception as e:
            print(f"Process Error: {e}")
        finally:
            browser.close()

# ===============================
# CONTINUOUS LOOP
# ===============================
if __name__ == "__main__":
    while True:
        try:
            check_slots()
        except Exception as e:
            print("Loop Error:", e)
        time.sleep(CHECK_INTERVAL)
