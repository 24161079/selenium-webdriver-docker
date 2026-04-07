import time
from dataclasses import dataclass
from typing import List

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..config import CONFIG
from ..constants import TIMEOUTS


@dataclass
class SelectStep:
    selector: str
    message_before_click: str
    message_after_click: str


def select_input(driver, steps: List[SelectStep]) -> None:
    wait = WebDriverWait(driver, TIMEOUTS["default_wait"])
    time.sleep(CONFIG["delays"]["after_navigation"])

    for step in steps:
        print(step.message_before_click)
        wait.until(EC.element_to_be_clickable((By.XPATH, step.selector))).click()
        print(step.message_after_click)
        time.sleep(CONFIG["delays"]["after_click"])
