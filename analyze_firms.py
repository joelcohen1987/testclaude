#!/usr/bin/env python3
"""
MIT Endowment Investment Firm Screening Tool
=============================================
Analyzes SEC Form ADV Exempt Reporting Adviser data to identify firms
matching MIT's investment philosophy:
- Long-term investing in high-quality businesses
- Value-oriented investment philosophy
- Excludes: pure venture capital firms, 100% real estate firms
"""

import csv
import re
import json
from collections import Counter

CSV_FILE = "IA_SEC_-_FIRM_ROSTER_FOIA_DOWNLOAD_-_34537694.CSV"

# ─── Value Investing Keywords ──────────────────────────────────────────────────
# These keywords in firm names or website URLs signal potential alignment with
# MIT's long-term, value-oriented, quality-focused investment philosophy.

VALUE_NAME_KEYWORDS = [
    "value", "quality", "fundamental", "long-term", "longterm",
    "compounding", "compound", "concentrated", "conviction",
    "patient", "permanent", "enduring", "durable", "franchise",
    "intrinsic", "margin of safety", "deep value", "contrarian",
    "opportunistic", "absolute return", "total return",
    "capital allocation", "owner", "partnership",
]

# Keywords that suggest non-value strategies (negative signals)
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

# Keywords suggesting hedge fund / PE equity value investing
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
    """Load and parse the SEC Form ADV CSV data."""
    with open(CSV_FILE, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"Loaded {len(rows)} Exempt Reporting Advisers")
    return rows


def parse_assets(val):
    """Parse the 'Total Gross Assets of Private Funds' field to a float."""
    try:
        return float(val.strip().replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        return 0.0


def is_pure_vc(row):
    """Return True if the firm only manages VC funds."""
    has_vc = row["Any VC Funds"].strip() == "Y"
    has_hf = row["Any Hedge Funds"].strip() == "Y"
    has_pe = row["Any PE Funds"].strip() == "Y"
    has_re = row["Any Real Estate Funds"].strip() == "Y"
    has_other = row["Any Other Funds"].strip() == "Y"
    has_sec = row["Any Securitized Funds"].strip() == "Y"
    has_liq = row["Any Liquidity Funds"].strip() == "Y"
    return has_vc and not any([has_hf, has_pe, has_re, has_other, has_sec, has_liq])


def is_pure_real_estate(row):
    """Return True if the firm only manages real estate funds."""
    has_vc = row["Any VC Funds"].strip() == "Y"
    has_hf = row["Any Hedge Funds"].strip() == "Y"
    has_pe = row["Any PE Funds"].strip() == "Y"
    has_re = row["Any Real Estate Funds"].strip() == "Y"
    has_other = row["Any Other Funds"].strip() == "Y"
    has_sec = row["Any Securitized Funds"].strip() == "Y"
    has_liq = row["Any Liquidity Funds"].strip() == "Y"
    return has_re and not any([has_hf, has_pe, has_vc, has_other, has_sec, has_liq])


def has_vc_component(row):
    """Return True if the firm has ANY VC funds (used for downscoring)."""
    return row["Any VC Funds"].strip() == "Y"


def phase1_filter(rows):
    """
    Phase 1: Structural filtering using Form ADV data.

    Criteria:
    - Active ERA status
    - Has a website
    - Not pure VC
    - Not 100% real estate
    - Has at least $50M in gross assets (meaningful AUM for endowment allocations)
    """
    candidates = []
    excluded = Counter()

    for row in rows:
        name = row["Primary Business Name"].strip()
        website = row["Website Address"].strip()
        assets = parse_assets(row["Total Gross Assets of Private Funds"])

        # Must have a website
        if not website:
            excluded["no_website"] += 1
            continue

        # Exclude pure VC
        if is_pure_vc(row):
            excluded["pure_vc"] += 1
            continue

        # Exclude pure real estate
        if is_pure_real_estate(row):
            excluded["pure_re"] += 1
            continue

        # Minimum AUM threshold ($50M) for meaningful endowment allocation
        if assets < 50_000_000:
            excluded["low_aum"] += 1
            continue

        candidates.append(row)

    print(f"\nPhase 1 Filtering Results:")
    print(f"  Excluded (no website):      {excluded['no_website']}")
    print(f"  Excluded (pure VC):         {excluded['pure_vc']}")
    print(f"  Excluded (pure RE):         {excluded['pure_re']}")
    print(f"  Excluded (AUM < $50M):      {excluded['low_aum']}")
    print(f"  Remaining candidates:       {len(candidates)}")
    return candidates


def score_firm(row):
    """
    Phase 2: Score each firm based on signals of value-oriented,
    long-term, quality-focused investing.

    Scoring factors:
    - Fund type mix (hedge funds and 'other' funds score highest for
      public equity value investing)
    - AUM (larger indicates more established)
    - Firm name keyword analysis
    - Concentration (fewer funds = potentially more focused)
    - Negative keyword penalties
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

    # Hedge funds are the primary vehicle for public equity value investing
    # (like Linonia). This is the strongest positive signal.
    if has_hf and not has_vc and not has_re:
        score += 30
        reasons.append("hedge_fund_pure_equity_signal")
    elif has_hf:
        score += 15
        reasons.append("hedge_fund_mixed")

    # PE funds focused on quality businesses
    if has_pe and not has_vc:
        score += 10
        reasons.append("pe_fund_no_vc")

    # "Other" funds can be interesting (long-only, concentrated equity, etc.)
    if has_other and not has_vc:
        score += 5
        reasons.append("other_fund_type")

    # Penalty for having VC component (mixed firms)
    if has_vc:
        score -= 15
        reasons.append("has_vc_penalty")

    # Penalty for real estate component
    if has_re:
        score -= 10
        reasons.append("has_re_penalty")

    # ── AUM scoring (larger = more established) ─────────────────────────
    if assets >= 5_000_000_000:
        score += 15
        reasons.append("aum_5b+")
    elif assets >= 1_000_000_000:
        score += 12
        reasons.append("aum_1b+")
    elif assets >= 500_000_000:
        score += 8
        reasons.append("aum_500m+")
    elif assets >= 100_000_000:
        score += 5
        reasons.append("aum_100m+")

    # ── Fund concentration scoring ──────────────────────────────────────
    try:
        num_funds = int(row["Count of Private Funds - 7B(1)"].strip())
    except (ValueError, KeyError):
        num_funds = 0

    # Fewer funds suggests more concentrated/focused approach
    if 1 <= num_funds <= 3:
        score += 10
        reasons.append("concentrated_few_funds")
    elif 4 <= num_funds <= 6:
        score += 5
        reasons.append("moderate_fund_count")

    # ── Firm name keyword analysis ──────────────────────────────────────
    # Positive keywords
    for kw in VALUE_NAME_KEYWORDS:
        if kw in name:
            score += 8
            reasons.append(f"name_positive:{kw}")

    # Negative keywords
    for kw in NEGATIVE_KEYWORDS:
        if kw in name:
            score -= 12
            reasons.append(f"name_negative:{kw}")

    # Positive strategy keywords in name
    for kw in POSITIVE_STRATEGY_KEYWORDS:
        if kw in name:
            score += 3
            reasons.append(f"name_strategy:{kw}")

    # Website URL analysis
    for kw in NEGATIVE_KEYWORDS:
        if kw in website:
            score -= 8
            reasons.append(f"url_negative:{kw}")

    # ── US-based bonus (slight preference for domestic managers) ─────────
    if row["Main Office Country"].strip() == "United States":
        score += 2
        reasons.append("us_based")

    # ── Clean regulatory record ─────────────────────────────────────────
    has_disclosure = row.get("11", "").strip() == "Y"
    if not has_disclosure:
        score += 3
        reasons.append("clean_regulatory")

    return score, reasons


def phase2_score_and_rank(candidates):
    """Score all candidates and return sorted by score descending."""
    scored = []
    for row in candidates:
        score, reasons = score_firm(row)
        scored.append((score, reasons, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    print(f"\nPhase 2 Scoring Complete:")
    print(f"  Top score: {scored[0][0]}")
    print(f"  Median score: {scored[len(scored)//2][0]}")
    print(f"  Bottom score: {scored[-1][0]}")

    return scored


def extract_firm_info(row):
    """Extract key information about a firm for display."""
    assets = parse_assets(row["Total Gross Assets of Private Funds"])
    fund_types = []
    if row["Any Hedge Funds"].strip() == "Y":
        n = row["Total number of Hedge funds"].strip()
        fund_types.append(f"Hedge({n})")
    if row["Any PE Funds"].strip() == "Y":
        n = row["Total number of PE funds"].strip()
        fund_types.append(f"PE({n})")
    if row["Any VC Funds"].strip() == "Y":
        n = row["Total number of VC funds"].strip()
        fund_types.append(f"VC({n})")
    if row["Any Real Estate Funds"].strip() == "Y":
        n = row["Total number of Real Estate funds"].strip()
        fund_types.append(f"RE({n})")
    if row["Any Other Funds"].strip() == "Y":
        n = row["Total number of Other funds"].strip()
        fund_types.append(f"Other({n})")
    if row["Any Securitized Funds"].strip() == "Y":
        n = row["Total number of Securitized funds"].strip()
        fund_types.append(f"Sec({n})")
    if row["Any Liquidity Funds"].strip() == "Y":
        n = row["Total number of Liquidity funds"].strip()
        fund_types.append(f"Liq({n})")

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
    # Load data
    rows = load_data()

    # Phase 1: Structural filtering
    candidates = phase1_filter(rows)

    # Phase 2: Scoring
    scored = phase2_score_and_rank(candidates)

    # Take top candidates (generous cut for Phase 3 review)
    # We'll take firms scoring above a threshold
    top_candidates = [(s, r, row) for s, r, row in scored if s >= 25]
    print(f"\n  Firms scoring >= 25: {len(top_candidates)}")

    # If too many, take top 200 for further analysis
    if len(top_candidates) > 200:
        top_candidates = top_candidates[:200]
        print(f"  Trimmed to top 200")

    # Display top results
    print(f"\n{'='*100}")
    print(f"TOP CANDIDATES FOR MIT ENDOWMENT REVIEW")
    print(f"Long-term, value-oriented, quality-focused investment managers")
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

    # Save full results to JSON for further analysis
    with open("candidate_firms.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to candidate_firms.json ({len(results)} firms)")

    # Save CSV summary
    with open("candidate_firms_summary.csv", "w", newline="") as f:
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
    print(f"Summary CSV saved to candidate_firms_summary.csv")

    return results


if __name__ == "__main__":
    main()
