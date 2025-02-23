import logging
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel
from rich import print
from rich.logging import RichHandler

URL = "https://www.gsmarena.com"
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
        pass

    def _goto_phone_finder_results(self):
        self.page.goto(
            urljoin(URL, "apple_iphone_13_pro_max-11089.php"),
            timeout=TIMEOUT,
            wait_until="domcontentloaded",
        )


class GSMArenaPhonePageProcessor:
    def __init__(self, page):
        self.page = page

    def execute(self):
        phone_name = self._get_phone_name()
        return phone_name

    def _get_phone_name(self):
        element = self.page.query_selector(
            "#body > div > div.review-header > div > div.article-info-line.page-specs.light.border-bottom > h1"
        )
        if element:
            return element.inner_text()
        else:
            raise ValueError("Element not found")


# init playwright and launch browser
def launch_browser():
    # executable_path = Path()
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=False,
        # executable_path=str(executable_path)
    )
    return browser, playwright


def main():
    browser, playwright = launch_browser()
    page = browser.new_page()

    try:
        page.goto(URL, timeout=TIMEOUT, wait_until="domcontentloaded")
        processor = GSMArenaProcessor(page)
        processor._goto_phone_finder_results()
        processor = GSMArenaPhonePageProcessor(page)
        phone_name = processor.execute()
        print(f"Phone name: {phone_name}")
    except PlaywrightTimeoutError:
        logger.error("Timeout while loading the page")
    except Exception as e:
        logger.error(e)
    finally:
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    main()
