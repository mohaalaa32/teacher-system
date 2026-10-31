import os
import sys
import json
import base64
import asyncio
import subprocess
import tempfile
import time
import urllib.request
import websockets

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.database import Base, engine, SessionLocal
from backend.app.services.seed_service import ensure_initial_seed_data
from backend.app.main import create_export_task
from backend.app.schemas import ExportCreateRequest
from backend.app.services.export_service import verify_exported_file_structure

EVIDENCE_DIR = os.path.join(ROOT_DIR, "docs", "evidence")
SCREENSHOTS_DIR = os.path.join(EVIDENCE_DIR, "screenshots")
EXPORTS_EVIDENCE_DIR = os.path.join(EVIDENCE_DIR, "sample_exports")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_EVIDENCE_DIR, exist_ok=True)

ROUTES = [
    ("01_dashboard", "/"),
    ("02_curriculum", "/curriculum"),
    ("03_lessons", "/lessons"),
    ("04_tools", "/tools"),
    ("05_settings", "/settings"),
    ("06_daily_plan", "/daily-plan"),
    ("07_weekly_plan", "/weekly-plan"),
    ("08_five_day_plan", "/five-day-plan"),
    ("09_review", "/review"),
    ("10_reports", "/reports"),
    ("11_presentations", "/presentations"),
    ("12_sources", "/sources"),
    ("13_export_package", "/export-package"),
]

VIEWPORTS = [
    ("desktop_1440x900", 1440, 900),
    ("tablet_768x1024", 768, 1024),
    ("mobile_390x844", 390, 844),
    ("overflow_320x800", 320, 800),
]


def wait_for_url(url: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def generate_sample_exports_and_verify():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_initial_seed_data(db)
        results = {}
        for fmt, filename in [
            ("docx", "sample_daily_plan.docx"),
            ("pdf", "sample_daily_plan.pdf"),
            ("pptx", "sample_presentation.pptx"),
            ("report_pdf", "sample_planning_report.pdf"),
            ("bundle_zip", "sample_full_bundle.zip"),
        ]:
            task_info = create_export_task(
                payload=ExportCreateRequest(
                    contextId="ctx_math_iq_demo",
                    planId="pln_daily_demo_a",
                    exportFormat=fmt,
                ),
                x_active_context_id="ctx_math_iq_demo",
                db=db,
            )
            src_files = os.listdir(os.path.join(ROOT_DIR, "backend", "storage", "exports"))
            matching = [f for f in src_files if f.endswith(task_info["fileName"])]
            if matching:
                src_path = os.path.join(ROOT_DIR, "backend", "storage", "exports", matching[0])
                dst_path = os.path.join(EXPORTS_EVIDENCE_DIR, filename)
                with open(src_path, "rb") as f_in:
                    data = f_in.read()
                with open(dst_path, "wb") as f_out:
                    f_out.write(data)
                ver = verify_exported_file_structure(data, fmt)
                results[fmt] = {
                    "file": f"docs/evidence/sample_exports/{filename}",
                    "sizeBytes": len(data),
                    "sha256": task_info["contentSha256"],
                    "verification": ver,
                }
        with open(os.path.join(EVIDENCE_DIR, "export_verification_report.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("Sample exports generated and verified successfully.")
    finally:
        db.close()


async def cdp_capture_all(ws_url: str):
    viewport_audit = []
    msg_id = 0

    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        async def send_cmd(method: str, params: dict = None):
            nonlocal msg_id
            msg_id += 1
            cur_id = msg_id
            await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
            while True:
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("id") == cur_id:
                    return data.get("result", {})

        await send_cmd("Page.enable")
        await send_cmd("Runtime.enable")

        for route_slug, route_path in ROUTES:
            url = f"http://127.0.0.1:3000{route_path}"
            await send_cmd("Page.navigate", {"url": url})
            await asyncio.sleep(0.55)

            for vp_name, w, h in VIEWPORTS:
                if vp_name in ("tablet_768x1024", "overflow_320x800") and route_slug not in (
                    "01_dashboard",
                    "06_daily_plan",
                    "09_review",
                    "11_presentations",
                ):
                    continue

                await send_cmd(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": w,
                        "height": h,
                        "deviceScaleFactor": 1,
                        "mobile": w < 820,
                    },
                )
                await asyncio.sleep(0.2)

                eval_res = await send_cmd(
                    "Runtime.evaluate",
                    {
                        "expression": """JSON.stringify({
                            innerWidth: window.innerWidth,
                            scrollWidth: document.documentElement.scrollWidth,
                            hasHorizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
                            dir: document.documentElement.dir || 'rtl',
                            lang: document.documentElement.lang || 'ar'
                        })""",
                        "returnByValue": True,
                    },
                )
                metrics_str = eval_res.get("result", {}).get("value", "{}")
                metrics = json.loads(metrics_str)

                shot = await send_cmd(
                    "Page.captureScreenshot",
                    {
                        "format": "png",
                        "clip": {"x": 0, "y": 0, "width": w, "height": h, "scale": 1},
                    },
                )
                b64_data = shot.get("data", "")
                out_file = os.path.join(SCREENSHOTS_DIR, f"{route_slug}_{vp_name}.png")
                if b64_data:
                    with open(out_file, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                viewport_audit.append(
                    {
                        "route": route_path,
                        "screenshot": f"docs/evidence/screenshots/{route_slug}_{vp_name}.png",
                        "viewport": f"{w}x{h}",
                        **metrics,
                    }
                )

    with open(os.path.join(EVIDENCE_DIR, "viewport_audit_report.json"), "w", encoding="utf-8") as f:
        json.dump(viewport_audit, f, ensure_ascii=False, indent=2)
    print(f"Captured {len(viewport_audit)} screenshots and viewport metrics via CDP.")


def capture_all_screenshots():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.isfile(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    python_exe = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe")
    node_exe = "node"
    next_bin = os.path.join(ROOT_DIR, "frontend", "node_modules", "next", "dist", "bin", "next")
    user_data_dir = tempfile.mkdtemp(prefix="chrome_cdp_")

    backend_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    frontend_proc = subprocess.Popen(
        [node_exe, next_bin, "start", "-p", "3000"],
        cwd=os.path.join(ROOT_DIR, "frontend"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    chrome_proc = subprocess.Popen(
        [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--remote-debugging-port=9229",
            f"--user-data-dir={user_data_dir}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        print("Waiting for backend (8000), frontend (3000), and Chrome CDP (9229)...")
        if not wait_for_url("http://127.0.0.1:8000/api/health", 25):
            raise RuntimeError("Backend did not become ready on port 8000")
        if not wait_for_url("http://127.0.0.1:3000/", 25):
            raise RuntimeError("Frontend did not become ready on port 3000")
        if not wait_for_url("http://127.0.0.1:9229/json", 15):
            raise RuntimeError("Chrome CDP did not become ready on port 9229")

        with urllib.request.urlopen("http://127.0.0.1:9229/json") as resp:
            targets = json.loads(resp.read().decode("utf-8"))
        page_target = next(t for t in targets if t.get("type") == "page")
        ws_url = page_target["webSocketDebuggerUrl"]

        asyncio.run(cdp_capture_all(ws_url))
    finally:
        chrome_proc.terminate()
        frontend_proc.terminate()
        backend_proc.terminate()


if __name__ == "__main__":
    generate_sample_exports_and_verify()
    capture_all_screenshots()
