import os
from pathlib import Path
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

    download_root = os.environ.get("DOWNLOAD_ROOT", "/home/seluser/Downloads")
    Path(download_root).mkdir(parents=True, exist_ok=True)
    try:
        # Shared volume can be created with restrictive perms on cloud hosts.
        os.chmod(download_root, 0o777)
    except Exception as exc:
        print(f"[WARN] Could not chmod download root {download_root}: {exc}")

    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_root,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "profile.default_content_settings.popups": 0,
            "safebrowsing.enabled": True,
        },
    )

    selenium_url = os.environ.get("SELENIUM_REMOTE_URL", "http://selenium:4444/wd/hub")
    driver = webdriver.Remote(command_executor=selenium_url, options=options)

    try:
        driver.execute_cdp_cmd(
            "Browser.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": download_root,
                "eventsEnabled": True,
            },
        )
    except Exception:
        try:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": download_root,
                },
            )
        except Exception as exc:
            print(f"[WARN] Could not set download behavior: {exc}")

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
        download_all_templates(driver, "score-templates")
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
    finally:
        # Clean up downloaded files after automation completes
        download_root = Path(os.environ.get("DOWNLOAD_ROOT", "/downloads"))
        if download_root.exists():
            for item in download_root.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        print(f"Cleaned: {item.name}")
                    except Exception as e:
                        print(f"Failed to clean {item.name}: {e}")


if __name__ == "__main__":
    run_pipeline()
