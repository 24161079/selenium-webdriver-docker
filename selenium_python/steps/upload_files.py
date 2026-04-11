import time
import os
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..app_types import Selection
from ..constants import (
    COMBO_ID_PATTERNS,
    FRAMES,
    MESSAGES,
    SELECTORS,
    TIMEOUTS,
    msg_upload_complete,
    msg_upload_dir,
    msg_upload_failed,
    msg_upload_file_count,
    msg_upload_file_selected,
    msg_upload_processing,
    msg_upload_selecting,
    msg_upload_success,
)
from ..utils.combobox_helper import ComboBoxHelper


def _resolve_data_root() -> Path:
    configured_root = os.environ.get("AUTOMATION_DATA_DIR", "").strip()
    if configured_root:
        return Path(configured_root)
    return Path(__file__).resolve().parent.parent


def upload_files(driver, folder_name: str) -> None:
    print(MESSAGES.UPLOAD_START)

    processed_dir = _resolve_data_root() / folder_name
    processed_dir.mkdir(parents=True, exist_ok=True)
    print(msg_upload_dir(processed_dir))

    files = [p for p in processed_dir.iterdir() if p.suffix.lower() in {".xls", ".xlsx"}]
    print(msg_upload_file_count(len(files)))

    if not files:
        print("⚠ No files to upload")
        return

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

        success_count = 0
        for index, file_path in enumerate(files, start=1):
            print(msg_upload_processing(index, len(files), file_path.name))

            parsed = _parse_filename(file_path.name)
            if not parsed:
                print(f"  ⚠ Cannot parse filename: {file_path.name}")
                continue

            print(msg_upload_selecting(parsed.grade, parsed.class_room, parsed.subject))
            success = _upload_single_file(driver, combo_box_ids, parsed, file_path)

            if success:
                success_count += 1
                print(msg_upload_success(file_path.name))
            else:
                print(msg_upload_failed(file_path.name, "See log above"))

            time.sleep(TIMEOUTS["between_uploads"])

        print(msg_upload_complete(success_count, len(files)))
    finally:
        driver.switch_to.default_content()
        _close_modal(driver)


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
    return ComboBoxHelper.find_combo_box_ids(combo_box_info, COMBO_ID_PATTERNS)


def _upload_single_file(driver, combo_box_ids, selections: Selection, file_path: Path) -> bool:
    helper = ComboBoxHelper(driver)

    try:
        helper.select_item(combo_box_ids.grade, selections.grade)
        time.sleep(TIMEOUTS["after_select"])

        helper.select_item(combo_box_ids.class_room, selections.class_room)
        time.sleep(TIMEOUTS["after_select"])

        helper.select_item(combo_box_ids.subject, selections.subject)
        time.sleep(TIMEOUTS["before_upload"])

        file_input = driver.find_element(By.CSS_SELECTOR, SELECTORS["choose_file_input"])
        file_input.send_keys(str(file_path.resolve()))
        print(msg_upload_file_selected(file_path.name))

        upload_button = _find_button(driver, SELECTORS["upload_button"])
        if not upload_button:
            print(f"  {MESSAGES.UPLOAD_NO_BUTTON}")
            return False

        upload_button.click()
        time.sleep(TIMEOUTS["upload_wait"])

        update_button = _find_button(driver, SELECTORS["update_button"])
        if update_button:
            update_button.click()
            time.sleep(TIMEOUTS["after_upload"])
            try:
                alert = driver.switch_to.alert
                print(f"  📢 Confirm dialog: {alert.text}")
                alert.accept()
            except Exception:
                pass

        return True
    except Exception as exc:
        print(f"  ✗ Error: {exc}")
        return False


def _find_button(driver, selectors: list[str]) -> Optional[object]:
    for selector in selectors:
        try:
            return driver.find_element(By.XPATH, selector)
        except Exception:
            continue
    return None


def _close_modal(driver) -> None:
    close_selectors = [
        (By.CSS_SELECTOR, ".rwCommandButton.rwCloseButton"),
        (By.CSS_SELECTOR, ".rwCloseButton"),
        (By.CSS_SELECTOR, "[title='Close']"),
        (By.CSS_SELECTOR, "[title='Đóng']"),
    ]

    for by, selector in close_selectors:
        try:
            driver.find_element(by, selector).click()
            print("  ✓ Modal closed")
            return
        except Exception:
            continue


def _parse_filename(filename: str) -> Optional[Selection]:
    name_without_ext = filename.rsplit(".", 1)[0]

    import re

    match = re.search(r"lop_(\d+)_(\d+)_mon_(.+)$", name_without_ext)
    if match:
        grade_num, class_num, subject_slug = match.group(1), match.group(2), match.group(3)
    else:
        match = re.search(r"lop_(\d{2})_mon_(.+)$", name_without_ext)
        if not match:
            return None
        grade_class, subject_slug = match.group(1), match.group(2)
        grade_num, class_num = grade_class[0], grade_class[1]

    subject_map = {
        "ngu_van": "Ngữ văn",
        "toan": "Toán",
        "anh": "Tiếng Anh",
        "ly": "Vật lý",
        "hoa": "Hóa học",
        "sinh": "Sinh học",
        "su": "Lịch sử",
        "dia": "Địa lý",
        "gdcd": "GDCD",
        "hdtn": "HĐTN",
        "tin": "Tin học",
        "td": "Thể dục",
        "am_nhac": "Âm nhạc",
        "my_thuat": "Mỹ thuật",
        "cong_nghe": "Công nghệ",
    }

    subject_name = subject_map.get(subject_slug, subject_slug.replace("_", " "))

    return Selection(
        grade=f"Khối {grade_num}",
        class_room=f"{grade_num}/{class_num}",
        subject=subject_name,
    )
