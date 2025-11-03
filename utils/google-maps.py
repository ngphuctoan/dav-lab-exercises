import re
import pandas as pd
from playwright.sync_api import sync_playwright, expect

coffee_chains = ["Starbucks", "Highlands+Coffee", "Phuc+Long+Coffee"]
cities = ["Hanoi", "Ho+Chi+Minh+City"]

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    page = browser.new_page()

    for city in cities:
        for coffee_chain in coffee_chains:
            df = pd.DataFrame()

            query = f"{coffee_chain}+in+{city}"

            page.goto(f"https://www.google.com/maps/search/{query}")
            page.wait_for_selector(".Nv2PK")

            sidebar = page.locator("[role=feed]")
            zoom_in = page.locator("#widget-zoom-in")
            about_tab = page.locator("[role=tab][aria-label^=About]")
            info_section = page.locator(".iNvpkb:not(.XJynsc)")
            title = page.locator(".lfPIob")

            prev_height = 0
            for _ in range(60):
                sidebar.evaluate("(el) => (el.scrollTop = el.scrollHeight)")

                height = sidebar.evaluate("(el) => el.scrollHeight")
                if height <= prev_height:
                    try:
                        page.locator(':has-text("You\'ve reached the end of the list.")').wait_for(state="visible", timeout=1_000)
                        break
                    finally:
                        continue

            cards = page.locator(".Nv2PK")
            total = cards.count()

            print(f"Scroll limit reached; Found {total} results!")

            for i in range(total):
                if zoom_in.is_enabled():
                    zoom_in.click(click_count=10)

                old_url = page.url
                card = cards.nth(i)

                name = card.locator(".qBF1Pd").first.text_content().strip()

                for _ in range(10):
                    try:
                        card.click(timeout=0)
                        expect(page).not_to_have_url(old_url, timeout=100)
                        expect(about_tab).to_have_attribute("aria-selected", "false", timeout=100)
                        break
                    except Exception:
                        continue

                reviews = card.locator(".e4rVHe").first.text_content().strip()

                avg_rating = None
                num_of_reviews = None

                if reviews != "No reviews":
                    match = re.search(r"(\d\.\d)\(([\d,]+)\)", reviews)
                    if match:
                        avg_rating = float(match.group(1))
                        num_of_reviews = int(match.group(2).replace(",", ""))

                try:
                    address = page.locator("button[aria-label^=Address]").first.text_content().strip()[1:]
                except Exception:
                    address = None
                try:
                    phone = page.locator("button[aria-label^=Phone]").first.text_content(timeout=100).strip()[1:]
                except Exception:
                    phone = None

                for _ in range(10):
                    try:
                        about_tab.click(timeout=0)
                        info_section.first.wait_for(state="visible", timeout=100)
                        break
                    except Exception:
                        continue

                info = [
                    info_section.nth(j).text_content().strip()[1:]
                    for j in range(info_section.count())
                ]

                lat = None
                long = None

                match = re.search(r"/@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                if match:
                    lat, long = [float(group) for group in match.groups()]

                result = {
                    "name": name,
                    "address": address,
                    "lat": lat,
                    "long": long,
                    "phone": phone,
                    "avg_rating": avg_rating,
                    "num_of_reviews": num_of_reviews,
                    "info": info,
                }

                print(result)

                df = pd.concat([df, pd.DataFrame(result)], ignore_index=True)

            df.to_csv(f"{coffee_chain}_{city}.csv", index=False)

    browser.close()