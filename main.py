from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.launch(headless=False)
page = browser.new_page()
page.goto("https://www.gsmarena.com/samsung_galaxy_s25-13610.php", timeout=60_000, wait_until='load')


"""
phone model | price| specs
"""

# start data mining
def _get_phonename():
    element=page.query_selector("#body > div > div.review-header > div > div.article-info-line.page-specs.light.border-bottom > h1")
    return element.inner_text()

print(_get_phonename())


# end data mining
browser.close()
