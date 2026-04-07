import threading
import time
import secrets
import string
import os
from urllib import error as url_error
from urllib import request as url_request

from flask import Flask, jsonify, render_template, request

from selenium_python import run_pipeline

app = Flask(__name__)

active_jobs = 0
active_jobs_lock = threading.Lock()
current_stop_event = None
current_thread = None
current_driver = None
current_driver_lock = threading.Lock()
job_started_at = 0.0
last_heartbeat_at = 0.0
current_vnc_password = None

VNC_IDLE_TIMEOUT_SECONDS = 10
MAX_JOB_SECONDS = 1800
WATCHDOG_POLL_SECONDS = 1
RUNTIME_LOG_FILE = "/app/logs/automation_runtime.log"


def _write_runtime_log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    try:
        os.makedirs(os.path.dirname(RUNTIME_LOG_FILE), exist_ok=True)
        with open(RUNTIME_LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except Exception as exc:
        print(f"[WARN] runtime log write failed: {exc}")
    print(line)


def _build_novnc_url(host: str) -> str:
    return f"http://{host}:7901/vnc.html?autoconnect=true&resize=scale&view_only=0"


def _build_vnc_page_url(host: str) -> str:
    return f"http://{host}:5000/vnc"


def _build_selenium_hub_url() -> str:
    selenium_url = os.environ.get("SELENIUM_REMOTE_URL", "http://selenium:4444").rstrip("/")
    if not selenium_url.endswith("/wd/hub"):
        selenium_url = f"{selenium_url}/wd/hub"
    return selenium_url


def _force_delete_remote_session(session_id: str | None) -> bool:
    if not session_id:
        return False

    endpoint = f"{_build_selenium_hub_url()}/session/{session_id}"
    req = url_request.Request(endpoint, method="DELETE")
    try:
        with url_request.urlopen(req, timeout=3):
            return True
    except url_error.HTTPError as exc:
        # Session may already be gone (404) which is acceptable.
        if exc.code == 404:
            return True
        print(f"[WARN] force delete session http error: {exc}")
    except Exception as exc:
        print(f"[WARN] force delete session failed: {exc}")

    return False


def _generate_vnc_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _is_valid_vnc_password(candidate: str | None) -> bool:
    global current_vnc_password
    if not isinstance(candidate, str):
        return False

    normalized = candidate.strip()
    if not normalized or not current_vnc_password:
        return False

    return secrets.compare_digest(normalized, current_vnc_password)


def _set_current_driver(driver) -> None:
    global current_driver
    with current_driver_lock:
        current_driver = driver


def _clear_current_driver() -> None:
    global current_driver
    with current_driver_lock:
        current_driver = None


def _is_session_already_closed_error(exc: Exception) -> bool:
    message = str(exc)
    return "Unable to find session with ID" in message or "invalid session id" in message.lower()


def _cleanup_driver_async(driver, session_id: str | None) -> None:
    try:
        if driver:
            try:
                driver.quit()
            except Exception as exc:
                if not _is_session_already_closed_error(exc):
                    print(f"[WARN] driver.quit() during stop failed: {exc}")

        _force_delete_remote_session(session_id)
    finally:
        _clear_current_driver()


def request_stop(reason: str) -> bool:
    global current_stop_event

    with active_jobs_lock:
        stop_event = current_stop_event
        running = active_jobs > 0 and stop_event is not None

    if not running:
        return False

    print(f"[INFO] Stop requested: {reason}")
    _write_runtime_log(f"STOP_REQUESTED reason={reason}")
    stop_event.set()

    with current_driver_lock:
        driver = current_driver
        session_id = getattr(driver, "session_id", None) if driver else None

    cleanup_thread = threading.Thread(
        target=_cleanup_driver_async,
        args=(driver, session_id),
        daemon=True,
    )
    cleanup_thread.start()

    return True


def watchdog_loop() -> None:
    while True:
        global last_heartbeat_at
        time.sleep(WATCHDOG_POLL_SECONDS)

        reason = None
        now = time.monotonic()

        with active_jobs_lock:
            if active_jobs == 0:
                last_heartbeat_at = 0.0
                continue

            started = job_started_at
            heartbeat = last_heartbeat_at

        if now - started > MAX_JOB_SECONDS:
            reason = "max_runtime_reached"
        elif heartbeat > 0 and now - heartbeat > VNC_IDLE_TIMEOUT_SECONDS:
            reason = "viewer_no_heartbeat"

        if reason:
            request_stop(reason)


watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
watchdog_thread.start()


def run_google_test(stop_event: threading.Event) -> None:
    global active_jobs, current_stop_event, current_thread, job_started_at, last_heartbeat_at, current_vnc_password

    try:
        run_pipeline(stop_event=stop_event, on_driver_ready=_set_current_driver)
    except Exception as exc:
        print(f"[ERROR] run_google_test: {exc}")
        _write_runtime_log(f"RUN_PIPELINE_ERROR error={exc}")

    if not stop_event.is_set():
        print("[INFO] Automation flow completed; waiting for VNC close or manual cancel.")
        while not stop_event.wait(1.0):
            pass

    _clear_current_driver()
    with active_jobs_lock:
        active_jobs = 0
        current_stop_event = None
        current_thread = None
        job_started_at = 0.0
        last_heartbeat_at = 0.0
        current_vnc_password = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/vnc", methods=["GET"])
def vnc_page():
    password = request.args.get("password", "")

    with active_jobs_lock:
        if active_jobs == 0:
            return render_template("vnc_auth.html", message="Khong co phien VNC dang chay."), 200

    if not _is_valid_vnc_password(password):
        return render_template("vnc_auth.html", message="Mat khau VNC khong dung."), 401

    host = request.host.split(":")[0]
    return render_template(
        "vnc.html",
        novnc_url=_build_novnc_url(host),
        vnc_password=password,
    )


@app.route("/run", methods=["POST"])
def run():
    global active_jobs, current_stop_event, current_thread, job_started_at, last_heartbeat_at, current_vnc_password
    host = request.host.split(":")[0]
    novnc_url = _build_vnc_page_url(host)

    with active_jobs_lock:
        if active_jobs > 0:
            return jsonify(
                {
                    "status": "busy",
                    "message": "Chương trình đang chạy. Bạn có thể mở lại VNC.",
                    "active_jobs": active_jobs,
                    "novnc_url": novnc_url,
                }
            ), 409

        active_jobs = 1
        current_jobs = active_jobs
        current_stop_event = threading.Event()
        current_thread = threading.Thread(target=run_google_test, args=(current_stop_event,), daemon=True)
        job_started_at = time.monotonic()
        last_heartbeat_at = time.monotonic()
        current_vnc_password = _generate_vnc_password()
        _write_runtime_log("RUN_STARTED")

    current_thread.start()

    return jsonify(
        {
            "status": "started",
            "message": "Đã bắt đầu Chương trình tự động.",
            "active_jobs": current_jobs,
            "novnc_url": novnc_url,
            "vnc_password": current_vnc_password,
        }
    )


@app.route("/status", methods=["GET"])
def status():
    host = request.host.split(":")[0]

    with active_jobs_lock:
        stop_requested = current_stop_event.is_set() if current_stop_event else False
        running = active_jobs > 0 and not stop_requested
        stopping = active_jobs > 0 and stop_requested
        jobs = active_jobs

    return jsonify(
        {
            "running": running,
            "stopping": stopping,
            "active_jobs": jobs,
            "novnc_url": _build_vnc_page_url(host),
        }
    )


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    global last_heartbeat_at

    password = request.headers.get("X-VNC-Password", "") or request.args.get("password", "") or (request.get_json(silent=True) or {}).get("password", "")

    with active_jobs_lock:
        if active_jobs == 0:
            return jsonify({"status": "idle", "message": "No running automation."}), 200

    if not _is_valid_vnc_password(password):
        _write_runtime_log("HEARTBEAT unauthorized")
        return jsonify({"status": "unauthorized", "message": "Mat khau VNC khong hop le."}), 401

    with active_jobs_lock:
        last_heartbeat_at = time.monotonic()

    _write_runtime_log("HEARTBEAT ok")
    return jsonify({"status": "ok"}), 200


@app.route("/vnc/cancel", methods=["POST"])
def cancel_vnc_session():
    payload = request.get_json(silent=True) or {}
    password = payload.get("password", "")

    if not isinstance(password, str) or not password:
        return jsonify({"status": "error", "message": "Vui long nhap mat khau VNC."}), 400

    if not _is_valid_vnc_password(password):
        return jsonify({"status": "unauthorized", "message": "Mat khau VNC khong dung."}), 401

    stopped = request_stop("manual_cancel_with_password")
    if not stopped:
        return jsonify({"status": "idle", "message": "Khong co phien nao dang chay."}), 200

    _write_runtime_log("CANCEL accepted")
    return jsonify({"status": "stopped", "message": "Đã hủy phiên VNC hiện tại."}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
