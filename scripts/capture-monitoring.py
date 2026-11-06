#!/usr/bin/env python3
"""Run inside the optional Playwright verification container; never saves credentials/cookies."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.getenv("GRAFANA_URL", "http://grafana:3000").rstrip("/")
output = Path(os.getenv("EVIDENCE_DIRECTORY", "/evidence"))
output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": 1600, "height": 1700}, timezone_id="America/Chicago", locale="en-US")
    login = context.request.post(base + "/login", data={"user": os.environ["GRAFANA_USER"], "password": os.environ["GRAFANA_PASSWORD"]})
    assert login.status == 200, f"Grafana login returned HTTP {login.status}"
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base + "/d/incidentiq-overview/incidentiq-local-operations?from=now-15m&to=now&refresh=5s", wait_until="networkidle", timeout=60000)
    try:
        page.get_by_text("API traffic (requests / second)", exact=True).wait_for(timeout=30000)
    except Exception:
        page.screenshot(path=str(output / "monitoring-browser-failure.png"), full_page=True)
        print(json.dumps({"page_url": page.url, "page_text": page.locator("body").inner_text()[:3000], "errors": errors}), flush=True)
        raise
    for _ in range(15):
        if page.locator("canvas").count() >= 5 and page.get_by_text("No data", exact=True).count() == 0:
            break
        page.wait_for_timeout(2000)
    page.wait_for_timeout(5000)
    canvas_count = page.locator("canvas").count()
    no_data = page.get_by_text("No data", exact=True).count()
    assert canvas_count >= 5, f"Only {canvas_count} chart canvases rendered"
    assert no_data == 0, f"{no_data} panels show No data"
    assert not errors, errors
    page.screenshot(path=str(output / "monitoring-dashboard.png"), full_page=True)
    result = {"dashboard": "incidentiq-overview", "chart_canvases": canvas_count,
              "no_data_messages": no_data, "page_errors": errors, "screenshot": "monitoring-dashboard.png"}
    (output / "browser-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    context.close()
    browser.close()
