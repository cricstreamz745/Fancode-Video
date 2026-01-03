import json
from scraper import scrape_highlights, URL

if __name__ == "__main__":
    data = scrape_highlights(URL)

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("JSON saved as output.json")
