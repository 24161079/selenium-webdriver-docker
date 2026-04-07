from pathlib import Path

from types import SimpleNamespace

from types import MappingProxyType


URLS = MappingProxyType(
    {
        "BASE": "https://truong.khanhhoa.edu.vn",
        "LOGIN": "https://truong.khanhhoa.edu.vn/Login.aspx",
        "LOGIN_PAGE_INDICATOR": "Login.aspx",
    }
)

PATHS = MappingProxyType({"INPUT_DIR": "inputs"})

BROWSER_OPTIONS = MappingProxyType(
    {
        "headless": False,
        "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        "slow_mo_ms": 100,
    }
)

DELAYS = MappingProxyType(
    {
        "after_click": 0.1,
        "after_navigation": 0.1,
        "slow_mo": 0.1,
    }
)

SELECTORS = MappingProxyType(
    {
        "menu_input": "//a[contains(normalize-space(.), '5. Nhập liệu')]",
        "menu_score_input": "//a[contains(normalize-space(.), '5.4. Nhập điểm')]",
        "menu_subject_score_input": "//a[contains(normalize-space(.), '5.4.1. Nhập điểm môn học')]",
        "menu_comment_score_input": "//a[contains(normalize-space(.), '5.4.2. Nhập nhận xét môn học')]",
        "button_excel_subject_score_input": "//*[contains(normalize-space(.), 'Nhập điểm từ excel')]",
        "button_class_excel_subject_score_input": "//*[contains(normalize-space(.), 'Nhập theo lớp và môn học')]",
        "button_excel_comment_score_input": "//*[contains(normalize-space(.), 'Nhập nhận xét từ file excel')]",
        "loading_text": "//*[contains(normalize-space(.), 'Vui lòng chờ')]",
        "rad_combo_box": ".RadComboBox",
        "download_button": [
            "//button[contains(., 'Tải file mẫu')]",
            "//a[contains(., 'Tải file mẫu')]",
            "//input[contains(@value, 'Tải')]",
        ],
        "choose_file_input": "input[type='file']",
        "upload_button": [
            "//button[contains(., 'Tải lên')]",
            "//input[contains(@value, 'Tải lên')]",
            "//a[contains(., 'Tải lên')]",
        ],
        "update_button": [
            "//button[contains(., 'Cập nhật')]",
            "//input[contains(@value, 'Cập nhật')]",
            "//a[contains(., 'Cập nhật')]",
        ],
    }
)

FRAMES = MappingProxyType({"rad_window": "RadWindow1"})

COMBO_ID_PATTERNS = MappingProxyType(
    {
        "grade": "rcbKhoi",
        "class_room": "rcbLop",
        "subject": "rcbMon",
    }
)

TIMEOUTS = MappingProxyType(
    {
        "default_wait": 10,
        "modal_load": 0.5,
        "modal_loading_hidden": 1,
        "combo_box_wait": 1,
        "click_arrow": 0.2,
        "after_network_idle": 0.3,
        "after_select": 0.4,
        "before_download": 0.2,
        "between_downloads": 0.1,
        "download_event": 10,
        "network_idle_timeout": 5,
        "before_upload": 0.3,
        "after_upload": 0.5,
        "between_uploads": 0.2,
        "upload_wait": 1,
        "url_poll_interval": 0.5,
    }
)


MESSAGES = SimpleNamespace(
    LOGIN_START="Opening login page...",
    LOGIN_WAIT_USER="Please enter USER/PASS + CAPTCHA in browser (via noVNC), then click Login.",
    LOGIN_WAIT_REDIRECT="Waiting until URL leaves Login.aspx...",
    LOGIN_SUCCESS="Login successful.",
    SELECT_INPUT='Selecting menu "5. Nhập liệu"...',
    SELECT_INPUT_CLICKED='Clicked "5. Nhập liệu"',
    SELECT_SCORE_INPUT='Selecting menu "5.4. Nhập điểm"...',
    SELECT_SCORE_INPUT_CLICKED='Clicked "5.4. Nhập điểm"',
    SELECT_SUBJECT_SCORE_INPUT='Selecting menu "5.4.1. Nhập điểm môn học"...',
    SELECT_SUBJECT_SCORE_INPUT_CLICKED='Clicked "5.4.1. Nhập điểm môn học"',
    SELECT_EXCEL_SUBJECT_SCORE_INPUT='Selecting "Nhập điểm từ excel"...',
    SELECT_EXCEL_SUBJECT_SCORE_INPUT_CLICKED='Clicked "Nhập điểm từ excel"',
    SELECT_CLASS_EXCEL_SUBJECT_SCORE_INPUT='Selecting "Nhập theo lớp và môn học"...',
    SELECT_CLASS_EXCEL_SUBJECT_SCORE_INPUT_CLICKED='Clicked "Nhập theo lớp và môn học"',
    SELECT_COMMENT_SCORE_INPUT='Selecting menu "5.4.2. Nhập nhận xét môn học"...',
    SELECT_COMMENT_SCORE_INPUT_CLICKED='Clicked "5.4.2. Nhập nhận xét môn học"',
    SELECT_EXCEL_COMMENT_SCORE_INPUT='Selecting "Nhập nhận xét từ file excel"...',
    SELECT_EXCEL_COMMENT_SCORE_INPUT_CLICKED='Clicked "Nhập nhận xét từ file excel"',
    START_DOWNLOAD="Starting template download...",
    WAIT_MODAL="Waiting for modal...",
    MODAL_LOADED="Modal ready.",
    MODAL_TIMEOUT="Modal timeout, continuing...",
    FIND_IFRAME="Finding RadWindow1 iframe...",
    IFRAME_FOUND="Found RadWindow1 iframe.",
    IFRAME_NOT_FOUND="RadWindow1 iframe not found.",
    COMBO_APPEARED="RadComboBox appeared.",
    COMBO_NOT_FOUND="RadComboBox not found.",
    COMBO_NOT_ENOUGH="Not enough ComboBoxes found.",
    DOWNLOADING="Downloading template...",
    NO_FILE="No downloaded file detected.",
    NO_BUTTON="Download button not found.",
    UPLOAD_START="\\n=== Start uploading files ===",
    UPLOAD_NO_BUTTON='Upload button "Tải lên" not found.',
    ALL_DONE="All steps completed.",
)


def msg_download_dir(dir_path: Path) -> str:
    return f"Download directory: {dir_path}"


def msg_complete(count: int) -> str:
    return f"\\n=== Completed: downloaded {count} templates ==="


def msg_selected(text: str) -> str:
    return f"  ✓ Selected: {text}"


def msg_not_found(text: str) -> str:
    return f"  ⚠ Item not found: {text}"


def msg_select_error(text: str, error: str) -> str:
    return f"  ✗ Select error for '{text}': {error}"


def msg_downloaded(filename: str) -> str:
    return f"  ✓ Downloaded: {filename}"


def msg_download_error(error: str) -> str:
    return f"  ✗ Download error: {error}"


def msg_upload_dir(dir_path: Path) -> str:
    return f"Processed directory: {dir_path}"


def msg_upload_file_count(count: int) -> str:
    return f"Found {count} files to upload"


def msg_upload_processing(index: int, total: int, file_name: str) -> str:
    return f"\\n[{index}/{total}] Processing: {file_name}"


def msg_upload_selecting(grade: str, class_room: str, subject: str) -> str:
    return f"  Selecting: Grade={grade}, Class={class_room}, Subject={subject}"


def msg_upload_file_selected(filename: str) -> str:
    return f"  ✓ File selected: {filename}"


def msg_upload_success(filename: str) -> str:
    return f"  ✓✓ Upload success: {filename}"


def msg_upload_failed(filename: str, error: str) -> str:
    return f"  ✗✗ Upload failed: {filename} - {error}"


def msg_upload_complete(success: int, total: int) -> str:
    return f"\\n=== Upload complete: {success}/{total} files succeeded ==="
