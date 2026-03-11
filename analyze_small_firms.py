#!/usr/bin/env python3
"""
MIT Endowment - Small/Emerging Investment Firm Screening Tool
==============================================================
Analyzes SEC Form ADV Exempt Reporting Adviser data to identify SMALL firms
(under $100M AUM) matching MIT's investment philosophy:
- Long-term investing in high-quality businesses
- Value-oriented investment philosophy
- Excludes: pure venture capital firms, 100% real estate firms
- Focus on newer/smaller/emerging managers
"""

import csv
import json
from collections import Counter

CSV_FILE = "IA_SEC_-_FIRM_ROSTER_FOIA_DOWNLOAD_-_34537694.CSV"

# ─── Value Investing Keywords ──────────────────────────────────────────────────
VALUE_NAME_KEYWORDS = [
    "value", "quality", "fundamental", "long-term", "longterm",
    "compounding", "compound", "concentrated", "conviction",
    "patient", "permanent", "enduring", "durable", "franchise",
    "intrinsic", "margin of safety", "deep value", "contrarian",
    "opportunistic", "absolute return", "total return",
    "capital allocation", "owner", "partnership",
]

NEGATIVE_KEYWORDS = [
    "venture", "crypto", "blockchain", "digital asset", "token",
    "cannabis", "marijuana", "hemp", "spac",
    "quantitative", "quant", "algorithmic", "algo", "systematic",
    "high frequency", "hft", "momentum", "trend following",
    "macro", "commodity", "commodities", "futures",
    "credit", "lending", "loan", "debt fund", "mezzanine",
    "real estate", "realty", "property", "reit", "housing",
    "infrastructure", "timber", "farmland", "agriculture",
    "film", "entertainment", "music", "media fund",
    "litigation", "legal", "insurance",
    "special purpose", "blank check",
]

POSITIVE_STRATEGY_KEYWORDS = [
    "equity", "equities", "stock", "public equity",
    "global equity", "long only", "long/short", "long short",
    "value invest", "growth equity", "buyout",
    "capital partners", "investment partners",
    "capital management", "asset management",
    "investment management", "fund management",
    "holdings", "advisors", "partners",
]


def load_data():
    with open(CSV_FILE, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"Loaded {len(rows)} Exempt Reporting Advisers")
    return rows


def parse_assets(val):
    try:
        return float(val.strip().replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        return 0.0


def is_pure_vc(row):
    has_vc = row["Any VC Funds"].strip() == "Y"
    has_hf = row["Any Hedge Funds"].strip() == "Y"
    has_pe = row["Any PE Funds"].strip() == "Y"
    has_re = row["Any Real Estate Funds"].strip() == "Y"
    has_other = row["Any Other Funds"].strip() == "Y"
    has_sec = row["Any Securitized Funds"].strip() == "Y"
    has_liq = row["Any Liquidity Funds"].strip() == "Y"
    return has_vc and not any([has_hf, has_pe, has_re, has_other, has_sec, has_liq])


def is_pure_real_estate(row):
    has_vc = row["Any VC Funds"].strip() == "Y"
    has_hf = row["Any Hedge Funds"].strip() == "Y"
    has_pe = row["Any PE Funds"].strip() == "Y"
    has_re = row["Any Real Estate Funds"].strip() == "Y"
    has_other = row["Any Other Funds"].strip() == "Y"
    has_sec = row["Any Securitized Funds"].strip() == "Y"
    has_liq = row["Any Liquidity Funds"].strip() == "Y"
    return has_re and not any([has_hf, has_pe, has_vc, has_other, has_sec, has_liq])


def phase1_filter(rows):
    """
    Phase 1: Structural filtering - focus on SMALL firms under $100M AUM.

    Criteria:
    - Has a website
    - Not pure VC
    - Not 100% real estate
    - AUM under $100M (small/emerging manager focus)
    - Must have reported some assets (> $0)
    """
    candidates = []
    excluded = Counter()

    for row in rows:
        name = row["Primary Business Name"].strip()
        website = row["Website Address"].strip()
        assets = parse_assets(row["Total Gross Assets of Private Funds"])

        if not website:
            excluded["no_website"] += 1
            continue

        if is_pure_vc(row):
            excluded["pure_vc"] += 1
            continue

        if is_pure_real_estate(row):
            excluded["pure_re"] += 1
            continue

        # Focus on small firms: under $100M AUM
        if assets >= 100_000_000:
            excluded["too_large"] += 1
            continue

        candidates.append(row)

    print(f"\nPhase 1 Filtering Results (Small Firm Focus):")
    print(f"  Excluded (no website):      {excluded['no_website']}")
    print(f"  Excluded (pure VC):         {excluded['pure_vc']}")
    print(f"  Excluded (pure RE):         {excluded['pure_re']}")
    print(f"  Excluded (AUM >= $100M):    {excluded['too_large']}")
    print(f"  Remaining small firms:      {len(candidates)}")
    return candidates


def score_firm(row):
    """
    Phase 2: Score each small firm for value-oriented, long-term,
    quality-focused investing signals.
    """
    score = 0
    reasons = []
    name = row["Primary Business Name"].strip().lower()
    website = row["Website Address"].strip().lower()
    assets = parse_assets(row["Total Gross Assets of Private Funds"])

    # ── Fund type scoring ────────────────────────────────────────────────
    has_hf = row["Any Hedge Funds"].strip() == "Y"
    has_pe = row["Any PE Funds"].strip() == "Y"
    has_vc = row["Any VC Funds"].strip() == "Y"
    has_re = row["Any Real Estate Funds"].strip() == "Y"
    has_other = row["Any Other Funds"].strip() == "Y"

    if has_hf and not has_vc and not has_re:
        score += 30
        reasons.append("hedge_fund_pure_equity_signal")
    elif has_hf:
        score += 15
        reasons.append("hedge_fund_mixed")

    if has_pe and not has_vc:
        score += 10
        reasons.append("pe_fund_no_vc")

    if has_other and not has_vc:
        score += 5
        reasons.append("other_fund_type")

    if has_vc:
        score -= 15
        reasons.append("has_vc_penalty")

    if has_re:
        score -= 10
        reasons.append("has_re_penalty")

    # ── AUM scoring (for small firms, having SOME assets is good) ──────
    if assets >= 50_000_000:
        score += 8
        reasons.append("aum_50m+")
    elif assets >= 20_000_000:
        score += 5
        reasons.append("aum_20m+")
    elif assets >= 5_000_000:
        score += 3
        reasons.append("aum_5m+")
    elif assets > 0:
        score += 1
        reasons.append("has_some_assets")

    # ── Fund concentration (fewer = more focused) ─────────────────────
    try:
        num_funds = int(row["Count of Private Funds - 7B(1)"].strip())
    except (ValueError, KeyError):
        num_funds = 0

    if 1 <= num_funds <= 2:
        score += 10
        reasons.append("very_concentrated_1-2_funds")
    elif 3 <= num_funds <= 4:
        score += 5
        reasons.append("moderate_fund_count")

    # ── Firm name keyword analysis ────────────────────────────────────
    for kw in VALUE_NAME_KEYWORDS:
        if kw in name:
            score += 10
            reasons.append(f"name_positive:{kw}")

    for kw in NEGATIVE_KEYWORDS:
        if kw in name:
            score -= 15
            reasons.append(f"name_negative:{kw}")

    for kw in POSITIVE_STRATEGY_KEYWORDS:
        if kw in name:
            score += 3
            reasons.append(f"name_strategy:{kw}")

    for kw in NEGATIVE_KEYWORDS:
        if kw in website:
            score -= 8
            reasons.append(f"url_negative:{kw}")

    # ── US-based bonus ─────────────────────────────────────────────────
    if row["Main Office Country"].strip() == "United States":
        score += 2
        reasons.append("us_based")

    # ── Clean regulatory record ────────────────────────────────────────
    has_disclosure = row.get("11", "").strip() == "Y"
    if not has_disclosure:
        score += 3
        reasons.append("clean_regulatory")

    return score, reasons


def extract_firm_info(row):
    assets = parse_assets(row["Total Gross Assets of Private Funds"])
    fund_types = []
    for label, yes_col, num_col in [
        ("Hedge", "Any Hedge Funds", "Total number of Hedge funds"),
        ("PE", "Any PE Funds", "Total number of PE funds"),
        ("VC", "Any VC Funds", "Total number of VC funds"),
        ("RE", "Any Real Estate Funds", "Total number of Real Estate funds"),
        ("Other", "Any Other Funds", "Total number of Other funds"),
        ("Sec", "Any Securitized Funds", "Total number of Securitized funds"),
        ("Liq", "Any Liquidity Funds", "Total number of Liquidity funds"),
    ]:
        if row[yes_col].strip() == "Y":
            n = row[num_col].strip()
            fund_types.append(f"{label}({n})")

    return {
        "name": row["Primary Business Name"].strip(),
        "legal_name": row["Legal Name"].strip(),
        "website": row["Website Address"].strip(),
        "city": row["Main Office City"].strip(),
        "state": row["Main Office State"].strip(),
        "country": row["Main Office Country"].strip(),
        "assets_millions": round(assets / 1_000_000, 1),
        "fund_types": ", ".join(fund_types),
        "num_funds": row["Count of Private Funds - 7B(1)"].strip(),
        "crd": row["Organization CRD#"].strip(),
        "sec_number": row["SEC#"].strip(),
    }


def main():
    rows = load_data()

    # Phase 1: Filter to small firms
    candidates = phase1_filter(rows)

    # Phase 2: Score
    scored = []
    for row in candidates:
        score, reasons = score_firm(row)
        scored.append((score, reasons, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    print(f"\nPhase 2 Scoring Complete:")
    print(f"  Top score: {scored[0][0]}")
    print(f"  Median score: {scored[len(scored)//2][0]}")
    print(f"  Bottom score: {scored[-1][0]}")

    # Take top candidates scoring >= 25
    top_candidates = [(s, r, row) for s, r, row in scored if s >= 25]
    print(f"\n  Firms scoring >= 25: {len(top_candidates)}")

    if len(top_candidates) > 300:
        top_candidates = top_candidates[:300]
        print(f"  Trimmed to top 300")

    # Display
    print(f"\n{'='*100}")
    print(f"SMALL FIRM CANDIDATES FOR MIT ENDOWMENT REVIEW (<$100M AUM)")
    print(f"Long-term, value-oriented, quality-focused emerging investment managers")
    print(f"{'='*100}\n")

    results = []
    for rank, (score, reasons, row) in enumerate(top_candidates, 1):
        info = extract_firm_info(row)
        results.append({**info, "score": score, "reasons": reasons, "rank": rank})

        location = f"{info['city']}, {info['state']}" if info['state'] else f"{info['city']}, {info['country']}"
        print(f"#{rank:3d} | Score: {score:3d} | {info['name']}")
        print(f"      AUM: ${info['assets_millions']:,.1f}M | Funds: {info['fund_types']}")
        print(f"      Location: {location}")
        print(f"      Website: {info['website']}")
        print(f"      CRD#: {info['crd']} | SEC#: {info['sec_number']}")
        print(f"      Signals: {', '.join(reasons[:5])}")
        print()

    # Save results
    with open("small_firm_candidates.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to small_firm_candidates.json ({len(results)} firms)")

    with open("small_firm_candidates.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Score", "Firm Name", "Website", "AUM ($M)",
            "Fund Types", "# Funds", "City", "State", "Country",
            "CRD#", "SEC#", "Key Signals"
        ])
        for r in results:
            writer.writerow([
                r["rank"], r["score"], r["name"], r["website"],
                r["assets_millions"], r["fund_types"], r["num_funds"],
                r["city"], r["state"], r["country"],
                r["crd"], r["sec_number"],
                "; ".join(r["reasons"][:5])
            ])
    print(f"Summary CSV saved to small_firm_candidates.csv")

    return results


if __name__ == "__main__":
    main()
