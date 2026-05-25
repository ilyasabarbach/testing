import asyncio

BROWSER_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:3001/chapter-1.html"

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=BROWSER_PATH
        )
        page = await browser.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        print("TITLE:", await page.title())
        print("URL:", page.url)
        html = await page.content()
        print("HTML_LENGTH:", len(html))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
