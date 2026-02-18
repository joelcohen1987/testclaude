"""
SEC Exempt Reporting Adviser Website Scraper
=============================================
Visits every ERA firm website from the SEC CSV data and identifies firms
that discuss value investing, long-term investing, or business quality.

Usage:
    python scrape_era_websites.py

Output:
    - results.csv: All firms with match details
    - matches.csv: Only firms that matched keywords
    - Console summary of matching firms
"""

import csv
import re
import time
import sys
import os
import concurrent.futures
from urllib.parse import urlparse
import ssl

# Use requests if available, fall back to urllib
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CSV_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "IA_SEC_-_FIRM_ROSTER_FOIA_DOWNLOAD_-_34537694.CSV",
)

# Keywords grouped by theme
KEYWORD_GROUPS = {
    "value_investing": [
        r"value\s+invest",
        r"intrinsic\s+value",
        r"margin\s+of\s+safety",
        r"deep\s+value",
        r"value[\s-]+oriented",
        r"undervalued",
        r"value\s+approach",
        r"value\s+strategy",
        r"value\s+discipline",
        r"fundamental\s+value",
        r"book\s+value",
        r"discount\s+to\s+(?:intrinsic|fair|net\s+asset)",
        r"benjamin\s+graham",
        r"warren\s+buffett",
        r"seth\s+klarman",
        r"howard\s+marks",
    ],
    "long_term_investing": [
        r"long[\s-]+term\s+invest",
        r"long[\s-]+term\s+(?:horizon|perspective|focus|approach|orientation|holders|ownership|compounding|wealth|growth|capital\s+appreciation)",
        r"buy\s+and\s+hold",
        r"patient\s+(?:capital|invest|approach)",
        r"multi[\s-]+year\s+(?:horizon|holding|investment)",
        r"long[\s-]+duration",
        r"generational\s+(?:wealth|invest)",
        r"compounding",
        r"compound\s+(?:returns|growth|interest|capital)",
        r"time\s+in\s+the\s+market",
        r"long[\s-]+term\s+value\s+creation",
    ],
    "business_quality": [
        r"business\s+quality",
        r"quality\s+(?:business|companies|compani|assets|invest|growth|franchise|earnings)",
        r"high[\s-]+quality\s+(?:business|companies|compani|assets|growth)",
        r"durable\s+(?:competitive\s+)?advantage",
        r"economic\s+moat",
        r"sustainable\s+(?:competitive\s+advantage|business|earnings|growth)",
        r"franchise\s+value",
        r"pricing\s+power",
        r"barriers?\s+to\s+entry",
        r"strong\s+fundamentals",
        r"fundamental\s+(?:analysis|research|approach)",
        r"bottom[\s-]+up\s+(?:research|analysis|approach|stock\s+selection|invest)",
    ],
}

# Compile all patterns
ALL_PATTERNS = {}
for group, patterns in KEYWORD_GROUPS.items():
    ALL_PATTERNS[group] = re.compile("|".join(patterns), re.IGNORECASE)

MAX_WORKERS = 10       # concurrent threads
TIMEOUT = 15           # seconds per request
RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")
MATCHES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matches.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """Ensure URL has a scheme and is lowercase-normalized."""
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url


def extract_text(html: str) -> str:
    """Extract visible text from HTML."""
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "meta", "link"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    else:
        # Basic HTML tag stripping
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def fetch_page(url: str) -> str:
    """Fetch a web page and return its text content."""
    if HAS_REQUESTS:
        session = requests.Session()
        retries = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        resp = session.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            allow_redirects=True,
            verify=True,
        )
        resp.raise_for_status()
        return extract_text(resp.text)
    else:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")
            return extract_text(html)


def check_keywords(text: str) -> dict:
    """Check text against keyword groups. Returns dict of group -> list of matched snippets."""
    matches = {}
    for group, pattern in ALL_PATTERNS.items():
        found = pattern.findall(text)
        if found:
            # Deduplicate and lowercase
            matches[group] = list(set(m.lower().strip() for m in found))
    return matches


def process_firm(firm_name: str, url: str) -> dict:
    """Fetch a firm's website and check for keywords."""
    result = {
        "firm": firm_name,
        "url": url,
        "status": "ok",
        "error": "",
        "value_investing": "",
        "long_term_investing": "",
        "business_quality": "",
        "any_match": False,
    }
    try:
        normalized = normalize_url(url)
        text = fetch_page(normalized)
        matches = check_keywords(text)

        for group in KEYWORD_GROUPS:
            if group in matches:
                result[group] = "; ".join(matches[group])

        result["any_match"] = len(matches) > 0
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("SEC Exempt Reporting Adviser Website Scraper")
    print("=" * 70)

    # 1. Read CSV
    print(f"\nReading CSV: {CSV_FILE}")
    firms = []
    with open(CSV_FILE, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Firm Type", "").strip() == "ERA":
                website = row.get("Website Address", "").strip()
                name = row.get("Primary Business Name", "").strip()
                if website and not re.search(r"linkedin|facebook|twitter\.com|instagram|x\.com", website, re.IGNORECASE):
                    firms.append((name, website))

    print(f"Found {len(firms)} ERA firms with proper websites (excluding social media)")

    if not firms:
        print("No firms to process. Exiting.")
        return

    # 2. Scrape websites
    print(f"\nScraping websites with {MAX_WORKERS} concurrent workers...")
    print("This may take a while for ~4000 sites...\n")

    results = []
    match_count = 0
    error_count = 0
    done = 0
    total = len(firms)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_firm = {
            executor.submit(process_firm, name, url): (name, url)
            for name, url in firms
        }

        for future in concurrent.futures.as_completed(future_to_firm):
            done += 1
            result = future.result()
            results.append(result)

            if result["any_match"]:
                match_count += 1
                themes = []
                if result["value_investing"]:
                    themes.append("VALUE")
                if result["long_term_investing"]:
                    themes.append("LONG-TERM")
                if result["business_quality"]:
                    themes.append("QUALITY")
                print(f"  MATCH [{'/'.join(themes)}] {result['firm']} ({result['url']})")

            if result["status"] == "error":
                error_count += 1

            if done % 100 == 0:
                print(f"  ... processed {done}/{total} ({match_count} matches, {error_count} errors)")

    # 3. Write results
    fieldnames = ["firm", "url", "status", "error", "any_match", "value_investing", "long_term_investing", "business_quality"]

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    matching = [r for r in results if r["any_match"]]
    with open(MATCHES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matching)

    # 4. Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total ERA firms processed: {total}")
    print(f"Successfully scraped:      {total - error_count}")
    print(f"Errors (unreachable etc):  {error_count}")
    print(f"Firms matching keywords:   {match_count}")
    print(f"\nResults written to:")
    print(f"  All firms:      {RESULTS_FILE}")
    print(f"  Matches only:   {MATCHES_FILE}")

    if matching:
        print(f"\n{'='*70}")
        print("MATCHING FIRMS")
        print(f"{'='*70}")
        for r in sorted(matching, key=lambda x: x["firm"]):
            themes = []
            if r["value_investing"]:
                themes.append(f"  Value Investing: {r['value_investing']}")
            if r["long_term_investing"]:
                themes.append(f"  Long-Term Investing: {r['long_term_investing']}")
            if r["business_quality"]:
                themes.append(f"  Business Quality: {r['business_quality']}")
            print(f"\n{r['firm']}")
            print(f"  URL: {r['url']}")
            for t in themes:
                print(t)


if __name__ == "__main__":
    main()
