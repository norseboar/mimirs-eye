import time

from readability import Document
from selenium import webdriver
from selenium.webdriver import Chrome

SLEEP_TIME = 2

options = webdriver.ChromeOptions()
options.add_argument("--headless")

options.page_load_strategy = "eager"


# Pass the defined options objects to initialize the web driver
driver = Chrome(options=options)


def get_readable_html(url):
    driver.get(url)
    time.sleep(SLEEP_TIME)
    html = driver.page_source
    readable_html = Document(html).summary()
    return readable_html
