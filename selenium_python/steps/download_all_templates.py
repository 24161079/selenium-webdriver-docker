import os
import time
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
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


def _build_s3_context() -> tuple[Optional[object], str, str]:
    bucket = os.environ.get("S3_BUCKET", "").strip()
    key_prefix = os.environ.get("S3_KEY_PREFIX", "selenium-templates").strip("/")

    if not bucket:
        return None, "", key_prefix

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    client = boto3.client("s3", region_name=region) if region else boto3.client("s3")
    return client, bucket, key_prefix


def _resolve_session_folder() -> str:
    return os.environ.get("SESSION_FOLDER_NAME", "session-unknown").strip() or "session-unknown"


def download_all_templates(driver, folder_name: str) -> None:
    print(MESSAGES.START_DOWNLOAD)

    download_root = Path(os.environ.get("DOWNLOAD_ROOT", "/downloads"))
    download_root.mkdir(parents=True, exist_ok=True)
    print(msg_download_dir(download_root))

    s3_client, s3_bucket, s3_prefix = _build_s3_context()
    session_folder = _resolve_session_folder()

    if s3_client:
        print(f"S3 upload enabled: bucket={s3_bucket}, prefix={s3_prefix}/{session_folder}/{folder_name}")
    else:
        print("S3 upload disabled: missing S3_BUCKET env")

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

        total_downloaded = _download_all_combinations(
            driver,
            combo_box_ids,
            download_root,
            folder_name,
            session_folder,
            s3_client,
            s3_bucket,
            s3_prefix,
        )
        print(msg_complete(total_downloaded))
    finally:
        driver.switch_to.default_content()

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


def _download_all_combinations(
    driver,
    combo_box_ids,
    download_dir: Path,
    folder_name: str,
    session_folder: str,
    s3_client,
    s3_bucket: str,
    s3_prefix: str,
) -> int:
    helper = ComboBoxHelper(driver)
    total_downloaded = 0

    grade_items = helper.get_items(combo_box_ids.grade)
    print(f"Found {len(grade_items)} grades")

    for grade in grade_items:
        print(f"\n--- Grade: {grade['text']} ---")
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
                if _download_file(driver, download_dir, folder_name, session_folder, s3_client, s3_bucket, s3_prefix):
                    total_downloaded += 1
                time.sleep(TIMEOUTS["between_downloads"])

    return total_downloaded


def _download_file(driver, download_dir: Path, folder_name: str, session_folder: str, s3_client, s3_bucket: str, s3_prefix: str) -> bool:
    before_files = {p.name for p in download_dir.glob("*")}

    try:
        button = _find_download_button(driver)
        if not button:
            print(f"      {MESSAGES.NO_BUTTON}")
            return False

        button.click()
        print(f"      {MESSAGES.DOWNLOADING}")

        deadline = time.time() + TIMEOUTS["download_event"]
        while time.time() < deadline:
            current_files = {p.name for p in download_dir.glob("*") if not p.name.endswith(".crdownload")}
            new_files = current_files - before_files
            if new_files:
                newest = sorted(new_files)[-1]
                print(f"      {msg_downloaded(newest)}")
                local_path = download_dir / newest
                if s3_client and s3_bucket:
                    if not _upload_to_s3(s3_client, s3_bucket, s3_prefix, session_folder, folder_name, local_path):
                        return False
                return True
            time.sleep(0.2)

        print(f"      {MESSAGES.NO_FILE}")
        return False
    except Exception as exc:
        print(f"      {msg_download_error(str(exc))}")
        return False


def _upload_to_s3(s3_client, bucket: str, key_prefix: str, session_folder: str, folder_name: str, local_path: Path) -> bool:
    relative_key = f"{session_folder}/{folder_name}/{local_path.name}"
    s3_key = f"{key_prefix}/{relative_key}" if key_prefix else relative_key

    try:
        s3_client.upload_file(str(local_path), bucket, s3_key)
        print(f"      ✓ Uploaded to S3: s3://{bucket}/{s3_key}")
        return True
    except (ClientError, BotoCoreError, Exception) as exc:
        print(f"      ✗ S3 upload error: {exc}")
        return False


def _find_download_button(driver) -> Optional[object]:
    for selector in SELECTORS["download_button"]:
        try:
            return driver.find_element(By.XPATH, selector)
        except Exception:
            continue
    return None
