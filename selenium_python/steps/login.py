import time

from selenium.webdriver.support.ui import WebDriverWait

from ..config import CONFIG
from ..constants import MESSAGES, TIMEOUTS, URLS


def login(driver) -> None:
    print(MESSAGES.LOGIN_START)
    driver.get(CONFIG["login_url"])
    print(f"Opened: {driver.current_url}")

    print(MESSAGES.LOGIN_WAIT_USER)
    print(MESSAGES.LOGIN_WAIT_REDIRECT)

    wait = WebDriverWait(driver, 24 * 60 * 60)
    wait.until(lambda d: URLS["LOGIN_PAGE_INDICATOR"] not in d.current_url)

    print(MESSAGES.LOGIN_SUCCESS)
    time.sleep(TIMEOUTS["after_network_idle"])
