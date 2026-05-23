import sys
import json
import os
import subprocess
import tempfile

args = json.load(sys.stdin)
html = args["html"]
output_path = os.path.abspath(args.get("output_path", "output/cv.pdf"))

parent = os.path.dirname(output_path)
if parent:
    os.makedirs(parent, exist_ok=True)

# Write HTML to a temp file so the browser can load it
with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(html)
    html_path = f.name

file_url = "file:///" + html_path.replace("\\", "/")

# Browser candidates — Edge is always on Windows 11
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

browser = next((b for b in BROWSERS if os.path.exists(b)), None)

if browser:
    result = subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={output_path}",
            "--print-to-pdf-no-header",
            file_url,
        ],
        capture_output=True,
        timeout=30,
    )
    os.unlink(html_path)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(json.dumps({"ok": True, "path": output_path, "renderer": "edge/chrome-headless"}))
        sys.exit(0)

    err = result.stderr.decode(errors="replace")
    print(json.dumps({"error": f"Browser headless failed: {err[:300]}"}))
    sys.exit(1)

# Fallback: try playwright if installed
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser_pw = p.chromium.launch()
        page = browser_pw.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=output_path,
            format="A4",
            margin={"top": "1.5cm", "bottom": "1.5cm", "left": "1.5cm", "right": "1.5cm"},
            print_background=True,
        )
        browser_pw.close()
    os.unlink(html_path)
    print(json.dumps({"ok": True, "path": output_path, "renderer": "playwright"}))
    sys.exit(0)
except Exception as e:
    pass

os.unlink(html_path)
print(json.dumps({"error": "No renderer available. Install playwright: pip install playwright && playwright install chromium"}))
sys.exit(1)
