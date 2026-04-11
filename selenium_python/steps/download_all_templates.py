import time
import os
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..constants import (
    COMBO_ID_PATTERNS,
    FRAMES,
    MESSAGES,
    SELECTORS,
    TIMEOUTS,
    msg_complete,
    msg_download_dir,
    msg_download_error,
    msg_downloaded,
)
from ..utils.combobox_helper import ComboBoxHelper


STEPS_LOG_FILE = os.environ.get("AUTOMATION_STEPS_LOG_FILE", "/app/logs/automation_steps.log")


def _resolve_data_root() -> Path:
    configured_root = os.environ.get("AUTOMATION_DATA_DIR", "").strip()
    if configured_root:
        return Path(configured_root)
    return Path(__file__).resolve().parent.parent


def _write_step_log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    try:
        os.makedirs(os.path.dirname(STEPS_LOG_FILE), exist_ok=True)
        with open(STEPS_LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except Exception:
        pass


def download_all_templates(driver, folder_name: str) -> None:
    print(MESSAGES.START_DOWNLOAD)

    download_dir = _resolve_data_root() / folder_name
    download_dir.mkdir(parents=True, exist_ok=True)
    print(msg_download_dir(download_dir))
    _write_step_log(f"DOWNLOAD_START folder={folder_name} dir={download_dir}")

    _set_download_dir(driver, download_dir)
    _wait_for_modal_load(driver)

    frame = _find_rad_window_frame(driver)
    if not frame:
        print(MESSAGES.IFRAME_NOT_FOUND)
        return

    driver.switch_to.frame(frame)
    try:
        _wait_for_combo_boxes(driver)
        combo_box_ids = _find_combo_box_ids(driver)

        if not combo_box_ids.grade or not combo_box_ids.class_room or not combo_box_ids.subject:
            print(MESSAGES.COMBO_NOT_ENOUGH)
            return

        print(f"Grade ComboBox ID: {combo_box_ids.grade}")
        print(f"Class ComboBox ID: {combo_box_ids.class_room}")
        print(f"Subject ComboBox ID: {combo_box_ids.subject}")

        total_downloaded = _download_all_combinations(driver, combo_box_ids, download_dir)
        print(msg_complete(total_downloaded))
        _write_step_log(f"DOWNLOAD_COMPLETE folder={folder_name} count={total_downloaded} dir={download_dir}")
    finally:
        driver.switch_to.default_content()


def _set_download_dir(driver, download_dir: Path) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": str(download_dir),
            },
        )
    except Exception:
        # Remote drivers may not support CDP in all setups.
        pass


def _wait_for_modal_load(driver) -> None:
    print(MESSAGES.WAIT_MODAL)
    time.sleep(TIMEOUTS["modal_load"])
    try:
        WebDriverWait(driver, TIMEOUTS["modal_loading_hidden"]).until_not(
            EC.presence_of_element_located((By.XPATH, SELECTORS["loading_text"]))
        )
        print(MESSAGES.MODAL_LOADED)
    except Exception:
        print(MESSAGES.MODAL_TIMEOUT)
    time.sleep(TIMEOUTS["modal_load"])


def _find_rad_window_frame(driver):
    print(MESSAGES.FIND_IFRAME)
    for frame in driver.find_elements(By.TAG_NAME, "iframe"):
        if frame.get_attribute("name") == FRAMES["rad_window"]:
            print(MESSAGES.IFRAME_FOUND)
            return frame
    return None


def _wait_for_combo_boxes(driver) -> None:
    try:
        WebDriverWait(driver, TIMEOUTS["combo_box_wait"]).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["rad_combo_box"]))
        )
        print(MESSAGES.COMBO_APPEARED)
    except Exception:
        print(MESSAGES.COMBO_NOT_FOUND)


def _find_combo_box_ids(driver):
    combo_box_info = driver.execute_script(
        """
        const boxes = document.querySelectorAll('.RadComboBox');
        return Array.from(boxes).map((box, i) => ({
          index: i,
          id: box.id,
          className: box.className,
          inputValue: box.querySelector('.rcbInput')?.getAttribute('value') || '',
          hasDropdown: !!box.querySelector('.rcbSlide')
        }));
        """
    )
    print(f"RadComboBox info in iframe: {combo_box_info}")
    return ComboBoxHelper.find_combo_box_ids(combo_box_info, COMBO_ID_PATTERNS)


def _download_all_combinations(driver, combo_box_ids, download_dir: Path) -> int:
    helper = ComboBoxHelper(driver)
    total_downloaded = 0

    grade_items = helper.get_items(combo_box_ids.grade)
    print(f"Found {len(grade_items)} grades")

    for grade in grade_items:
        print(f"\\n--- Grade: {grade['text']} ---")
        helper.select_item(combo_box_ids.grade, grade["text"])

        time.sleep(TIMEOUTS["after_select"])
        class_items = helper.get_items(combo_box_ids.class_room)
        print(f"  Found {len(class_items)} classes")

        for class_item in class_items:
            print(f"  Class: {class_item['text']}")
            helper.select_item(combo_box_ids.class_room, class_item["text"])

            time.sleep(TIMEOUTS["after_select"])
            subject_items = helper.get_items(combo_box_ids.subject)
            print(f"    Found {len(subject_items)} subjects")

            for subject in subject_items:
                print(f"    Subject: {subject['text']}")
                helper.select_item(combo_box_ids.subject, subject["text"])

                time.sleep(TIMEOUTS["before_download"])
                if _download_file(driver, download_dir):
                    total_downloaded += 1
                time.sleep(TIMEOUTS["between_downloads"])

    return total_downloaded


def _download_file(driver, download_dir: Path) -> bool:
    before_files = {p.name for p in download_dir.glob('*')}

    try:
        button = _find_download_button(driver)
        if not button:
            print(f"      {MESSAGES.NO_BUTTON}")
            return False

        button.click()
        print(f"      {MESSAGES.DOWNLOADING}")

        deadline = time.time() + TIMEOUTS["download_event"]
        while time.time() < deadline:
            current_files = {p.name for p in download_dir.glob('*') if not p.name.endswith('.crdownload')}
            new_files = current_files - before_files
            if new_files:
                newest = sorted(new_files)[-1]
                print(f"      {msg_downloaded(newest)}")
                _write_step_log(f"DOWNLOAD_OK file={newest} dir={download_dir}")
                return True
            time.sleep(0.2)

        print(f"      {MESSAGES.NO_FILE}")
        _write_step_log(f"DOWNLOAD_TIMEOUT dir={download_dir}")
        return False
    except Exception as exc:
        print(f"      {msg_download_error(str(exc))}")
        _write_step_log(f"DOWNLOAD_ERROR error={exc} dir={download_dir}")
        return False


def _find_download_button(driver) -> Optional[object]:
    for selector in SELECTORS["download_button"]:
        try:
            return driver.find_element(By.XPATH, selector)
        except Exception:
            continue
    return None
