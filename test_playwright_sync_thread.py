import threading
import traceback

BROWSER_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:3001/chapter-1.html"

def run_browser():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=BROWSER_PATH
            )
            page = browser.new_page()
            page.goto(URL, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1000)
            print("TITLE:", page.title())
            print("URL:", page.url)
            html = page.content()
            print("HTML_LENGTH:", len(html))
            browser.close()
    except Exception:
        traceback.print_exc()

def main():
    thread = threading.Thread(target=run_browser)
    thread.start()
    thread.join()


if __name__ == "__main__":
    main()
