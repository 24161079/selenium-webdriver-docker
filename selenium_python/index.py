import os
from typing import Callable

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .config import CONFIG
from .constants import MESSAGES, SELECTORS
from .steps.download_all_templates import download_all_templates
from .steps.login import login
from .steps.process_data import process_data
from .steps.upload_files import upload_files
from .utils.select_input_helper import SelectStep, select_input


def select_score_input(driver) -> None:
    select_input(
        driver,
        [
            SelectStep(SELECTORS["menu_input"], MESSAGES.SELECT_INPUT, MESSAGES.SELECT_INPUT_CLICKED),
            SelectStep(SELECTORS["menu_score_input"], MESSAGES.SELECT_SCORE_INPUT, MESSAGES.SELECT_SCORE_INPUT_CLICKED),
            SelectStep(
                SELECTORS["menu_subject_score_input"],
                MESSAGES.SELECT_SUBJECT_SCORE_INPUT,
                MESSAGES.SELECT_SUBJECT_SCORE_INPUT_CLICKED,
            ),
            SelectStep(
                SELECTORS["button_excel_subject_score_input"],
                MESSAGES.SELECT_EXCEL_SUBJECT_SCORE_INPUT,
                MESSAGES.SELECT_EXCEL_SUBJECT_SCORE_INPUT_CLICKED,
            ),
            SelectStep(
                SELECTORS["button_class_excel_subject_score_input"],
                MESSAGES.SELECT_CLASS_EXCEL_SUBJECT_SCORE_INPUT,
                MESSAGES.SELECT_CLASS_EXCEL_SUBJECT_SCORE_INPUT_CLICKED,
            ),
        ],
    )


def select_comment_input(driver) -> None:
    select_input(
        driver,
        [
            SelectStep(SELECTORS["menu_input"], MESSAGES.SELECT_INPUT, MESSAGES.SELECT_INPUT_CLICKED),
            SelectStep(SELECTORS["menu_score_input"], MESSAGES.SELECT_SCORE_INPUT, MESSAGES.SELECT_SCORE_INPUT_CLICKED),
            SelectStep(
                SELECTORS["menu_comment_score_input"],
                MESSAGES.SELECT_COMMENT_SCORE_INPUT,
                MESSAGES.SELECT_COMMENT_SCORE_INPUT_CLICKED,
            ),
            SelectStep(
                SELECTORS["button_excel_comment_score_input"],
                MESSAGES.SELECT_EXCEL_COMMENT_SCORE_INPUT,
                MESSAGES.SELECT_EXCEL_COMMENT_SCORE_INPUT_CLICKED,
            ),
        ],
    )


def build_driver() -> webdriver.Remote:
    options = Options()
    if CONFIG["browser_options"]["headless"]:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")

    for arg in CONFIG["browser_options"]["args"]:
        options.add_argument(arg)

    selenium_url = os.environ.get("SELENIUM_REMOTE_URL", "http://selenium:4444/wd/hub")
    driver = webdriver.Remote(command_executor=selenium_url, options=options)
    driver.maximize_window()
    return driver


def run_pipeline(stop_event=None, on_driver_ready: Callable | None = None) -> None:
    def ensure_not_stopped() -> None:
        if stop_event and stop_event.is_set():
            raise RuntimeError("Automation was stopped.")

    ensure_not_stopped()
    driver = build_driver()
    if on_driver_ready:
        on_driver_ready(driver)

    try:
        ensure_not_stopped()
        login(driver)

        ensure_not_stopped()
        print("\\n========== FLOW 1: SCORE INPUT (5.4.1) ==========")
        select_score_input(driver)
        # # download_all_templates(driver, "score-templates")
        # process_data()
        # # upload_files(driver, "score-templates")

        # ensure_not_stopped()
        # print("\\n========== FLOW 2: COMMENT INPUT (5.4.2) ==========")
        # # select_comment_input(driver)
        # # download_all_templates(driver, "comment-templates")
        # process_data()
        # # upload_files(driver, "comment-templates")

        # print(MESSAGES.ALL_DONE)
    except Exception as exc:
        if stop_event and stop_event.is_set():
            print("[INFO] Automation stopped by request.")
            return
        print(f"Error: {exc}")


if __name__ == "__main__":
    run_pipeline()
