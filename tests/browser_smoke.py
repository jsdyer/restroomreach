"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                expect(page.locator("#coverage")).to_contain_text("mapped toilets")
                expect(page.locator("#results button").first).to_be_visible()
                assert page.locator("#map .leaflet-tile-pane img").count() == 0
                page.get_by_label("Region", exact=True).select_option("halifax")
                expect(page.get_by_label("Region", exact=True)).to_have_value("halifax")
                page.get_by_label("Wheelchair", exact=True).select_option("yes")
                expect(page.locator("#results button").first).to_contain_text("Yes — mapped accessible")
                page.locator("#reset").click()
                page.locator("#query").fill("this-name-does-not-exist-93847")
                expect(page.locator("#empty")).to_be_visible()
                page.locator("#query").fill('<img src=x onerror="alert(1)">')
                assert page.locator("#results img").count() == 0
                page.locator("#reset").click()
                page.get_by_text("Sort by distance from a point", exact=True).click()
                expect(page.get_by_label("Latitude", exact=True)).to_be_visible()
                expect(page.get_by_label("Longitude", exact=True)).to_be_visible()
                page.get_by_role("button", name="Halifax", exact=True).click()
                expect(page.locator("#region")).to_have_value("halifax")
                expect(page.locator("#status")).to_contain_text("straight-line distance")
                page.locator("#results button").first.click()
                expect(page.locator("#detail-title")).not_to_have_text("Select a mapped place")
                expect(page.locator("#detail-tags")).to_contain_text("OSM object last edited")
                with page.expect_download() as download_info:
                    page.locator("#save").click()
                path=download_info.value.path()
                page.locator("#import").set_input_files(path)
                expect(page.locator("#status")).to_contain_text("Imported receipt loaded")
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: retained records, filters, local distance, import/export and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
