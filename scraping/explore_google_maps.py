"""Explore how Google Maps serves the reviews of a place (decision D-013).

Opens Google Maps in a visible browser, rejects the cookies, searches the place, opens the reviews
tab, scrolls the review list and finally tries the "Ver más reseñas" button. It reports how many
reviews were loaded and whether the review data carries exact timestamps.

No review content is kept. Screenshots and the list of network requests go to data/exploration/
(git-ignored), because the screenshots show author names.

Usage:
    uv run scraping/explore_google_maps.py "El Tormes Mall" [--scrolls 4]

Findings on 2026-10-23: without a Google account Maps shows a "limited view" with 5 reviews; loading
more or sorting asks to sign in. The data arrives through an internal 'batchexecute' request in
which every review has a timestamp in microseconds.
"""

import argparse
import datetime
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# Review timestamps are microseconds since 1970: 16 digits for dates between 2017 and 2033
TIMESTAMP = re.compile(r"(?<!\d)(1[5-9]\d{14})(?!\d)")

# Review cards carry this attribute; the list scrolls inside a panel, so we scroll its first scrollable ancestor
COUNT_REVIEWS = "() => new Set([...document.querySelectorAll('[data-review-id]')].map(e => e.dataset.reviewId)).size"
SCROLL_REVIEWS = """() => {
    let element = document.querySelector('[data-review-id]');
    while (element && !(element.scrollHeight > element.clientHeight + 10
                         && ['auto', 'scroll'].includes(getComputedStyle(element).overflowY)))
        element = element.parentElement;
    if (element) element.scrollBy(0, 4000);
    return Boolean(element);
}"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("place")
    parser.add_argument("--scrolls", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=Path("data/exploration"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    requests, timestamps = [], set()

    def on_response(response):
        requests.append({"url": response.url[:300], "status": response.status, "type": response.request.resource_type})
        if "batchexecute" in response.url and response.request.resource_type in ("xhr", "fetch"):
            try:
                timestamps.update(int(value) for value in TIMESTAMP.findall(response.text()))
            except Exception:  # some responses have no readable body
                pass

    def step(page, number: int, description: str) -> None:
        page.screenshot(path=str(args.output_dir / f"{number:02d}.png"))
        print(f"{number}. {description}: {page.evaluate(COUNT_REVIEWS)} reviews loaded")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page(locale="es-ES", viewport={"width": 1400, "height": 900})
        page.on("response", on_response)

        page.goto(f"https://www.google.com/maps/search/{args.place.replace(' ', '+')}?hl=es")
        time.sleep(3)
        reject = page.get_by_role("button", name="Rechazar todo")
        if reject.count():
            reject.first.click()
            time.sleep(4)
        if "/maps/place/" not in page.url and page.locator('a[href*="/maps/place/"]').count():
            page.locator('a[href*="/maps/place/"]').first.click()
            time.sleep(4)
        total = re.findall(r"([\d.]+)\s+reseñas", page.inner_text("body"))
        step(page, 1, f"Place '{page.locator('h1').first.inner_text()}', {total[0] if total else '?'} reviews in total")

        page.get_by_role("tab", name=re.compile("Reseñas")).first.click()
        time.sleep(4)
        step(page, 2, "Reviews tab")

        for _ in range(args.scrolls):
            page.evaluate(SCROLL_REVIEWS)
            time.sleep(2.5)
        step(page, 3, f"After {args.scrolls} scrolls")

        more = page.get_by_text(re.compile("Ver más reseñas"))
        if more.count():
            more.first.click()
            time.sleep(4)
            sign_in = page.get_by_text(re.compile("Inicia sesión")).count() > 0
            step(page, 4, f"'Ver más reseñas' clicked, sign-in requested: {sign_in}")

        browser.close()

    (args.output_dir / "requests.json").write_text(json.dumps(requests, indent=1), encoding="utf-8")
    dates = sorted(datetime.datetime.fromtimestamp(value / 1e6, datetime.UTC).date() for value in timestamps)
    print(f"Exact review timestamps in the network data: {len(dates)}"
          + (f", from {dates[0]} to {dates[-1]}" if dates else ""))
    print(f"Screenshots and request list in {args.output_dir}")


if __name__ == "__main__":
    main()
