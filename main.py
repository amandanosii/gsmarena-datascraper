import logging
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel
from rich import print
from rich.logging import RichHandler

BRAVE_PATH = "c:\\Users\\sipho\\AppData\\Local\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
URL = "https://www.gsmarena.com/samsung_galaxy_s25-13610.php"
TIMEOUT = 60_000

# configure logging
logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger("rich")


class GSMArenaProcessor:
    def __init__(self, page):
        self.page = page

    def execute(self):
        phone_name = self._get_phone_name()
        return phone_name

    def _get_phone_name(self):
        try:
            element = self.page.query_selector(
                "#body > div > div.review-header > div > div.article-info-line.page-specs.light.border-bottom > h1"
            )
            return element.inner_text() if element else "Element not found"
        except PlaywrightTimeoutError:
            return "Timeout while fetching phone name"


# init playwright and launch browser
def launch_browser():
    executable_path = Path(BRAVE_PATH)
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=False, executable_path=str(executable_path)
    )
    return browser, playwright


def main():
    browser, playwright = launch_browser()
    page = browser.new_page()

    try:
        page.goto(URL, timeout=TIMEOUT, wait_until="domcontentloaded")
        processor = GSMArenaProcessor(page)
        data = processor.execute()
        print(data)
    except PlaywrightTimeoutError:
        print("Timeout while loading the page")
    finally:
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    main()
