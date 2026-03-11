#!/usr/bin/env python3
"""
Deep Screen: Sub-$100M Emerging Managers for MIT Endowment
==========================================================
Much more thorough screening of the smallest firms in the SEC exempt
reporting adviser database. These are potential seed/early-stage allocations.

Focus: long-term, concentrated, value/quality equity investors.
"""

import csv
import json
from collections import Counter

CSV_FILE = "IA_SEC_-_FIRM_ROSTER_FOIA_DOWNLOAD_-_34537694.CSV"

# ─── Strong positive signals in firm name ──────────────────────────────────
# These are the strongest indicators of a Buffett/Munger style investor
TIER1_NAME_SIGNALS = [
    "value",
    "quality",
    "fundamental",
    "intrinsic",
    "compounding", "compound",
    "patient", "patience",
    "permanent",
    "enduring",
    "durable",
    "long-term", "longterm", "long term",
    "concentrated",
    "conviction",
    "contrarian",
    "margin of safety",
    "deep value",
    "franchise",
    "owner", "ownership",
    "rational",
    "circle of competence",
    "moat",
]

# Moderate positive signals
TIER2_NAME_SIGNALS = [
    "capital partners",
    "investment partners",
    "equity partners",
    "capital management",
    "asset management",
    "investment management",
    "fund management",
    "equity",
    "holdings",
    "partners",
    "advisors",
    "capital",
]

# Strong negative signals - immediately disqualify or heavily penalize
HARD_NEGATIVE = [
    "venture", "ventures",
    "crypto", "blockchain", "digital asset", "token", "defi", "web3",
    "cannabis", "marijuana", "hemp", "cbd",
    "spac", "blank check",
    "real estate", "realty", "property", "reit", "housing", "mortgage",
    "infrastructure", "timber", "farmland", "agriculture", "agri",
    "quantitative", "quant fund", "algorithmic", "algo ", "systematic",
    "high frequency", "hft",
    "momentum", "trend following", "trend-following",
    "macro", "global macro",
    "commodity", "commodities", "futures", "oil", "gas", "energy fund",
    "mining", "mineral", "metals",
    "credit fund", "lending", "loan", "debt fund", "mezzanine", "distressed debt",
    "film", "entertainment", "music", "media fund", "sports",
    "litigation", "legal fund",
    "insurance fund",
    "forex", "fx fund", "currency",
    "options", "derivatives fund", "volatility",
    "social impact", "esg fund", "climate fund", "clean energy",
    "biotech", "pharma", "life science", "healthcare fund",
    "fintech", "proptech", "edtech", "healthtech",
    "family office",  # not a fund manager
    "index", "passive", "etf",
    "robo", "automated",
    "crowdfund", "crowd",
    "royalt",
    "securitiz",
]

# Soft negative - penalize but don't disqualify
SOFT_NEGATIVE = [
    "multi-strategy", "multi strategy",
    "global macro",
    "special situation",  # can be value-adjacent but often event-driven
    "event driven", "event-driven",
    "arbitrage",
    "market neutral",
    "statistical",
]

# Website URL signals
URL_POSITIVE = [
    "value", "quality", "fundamental", "concentrated", "compounding",
    "patient", "longterm", "conviction", "intrinsic", "ownership",
    "enduring", "durable", "permanent",
]

URL_NEGATIVE = [
    "venture", "crypto", "quant", "realestate", "property",
    "commodity", "forex", "option", "algo", "systematic",
    "cannabis", "mining", "biotech", "fintech", "impact",
]


def parse_assets(val):
    try:
        return float(val.strip().replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        return 0.0


def screen_firm(row):
    """Score a firm. Returns (score, signals_list, disqualified)."""
    name = row["Primary Business Name"].strip()
    name_lower = name.lower()
    website = row["Website Address"].strip().lower()
    assets = parse_assets(row["Total Gross Assets of Private Funds"])
    aum_m = assets / 1e6

    score = 0
    signals = []
    disqualified = False

    # ── Hard negative check ─────────────────────────────────────────────
    for kw in HARD_NEGATIVE:
        if kw in name_lower or kw in website:
            disqualified = True
            signals.append(f"DISQUALIFIED:{kw}")
            return score, signals, disqualified

    # ── Fund type analysis ──────────────────────────────────────────────
    has_hf = row["Any Hedge Funds"].strip() == "Y"
    has_pe = row["Any PE Funds"].strip() == "Y"
    has_vc = row["Any VC Funds"].strip() == "Y"
    has_re = row["Any Real Estate Funds"].strip() == "Y"
    has_other = row["Any Other Funds"].strip() == "Y"
    has_sec = row["Any Securitized Funds"].strip() == "Y"
    has_liq = row["Any Liquidity Funds"].strip() == "Y"

    # Pure VC or pure RE = disqualify
    if has_vc and not any([has_hf, has_pe, has_other]):
        disqualified = True
        signals.append("DISQUALIFIED:pure_vc")
        return score, signals, disqualified

    if has_re and not any([has_hf, has_pe, has_vc, has_other]):
        disqualified = True
        signals.append("DISQUALIFIED:pure_re")
        return score, signals, disqualified

    # Best signal: hedge fund only (likely equity L/S or long-only)
    if has_hf and not has_vc and not has_re and not has_sec and not has_liq:
        score += 35
        signals.append("STRONG:pure_hedge_fund")
    elif has_hf:
        score += 20
        signals.append("hedge_fund_mixed")

    # PE without VC is OK (could be buyout/value)
    if has_pe and not has_vc:
        score += 10
        signals.append("pe_no_vc")

    if has_vc:
        score -= 20
        signals.append("PENALTY:has_vc")

    if has_re:
        score -= 15
        signals.append("PENALTY:has_re")

    # ── Fund concentration ──────────────────────────────────────────────
    try:
        num_funds = int(row["Count of Private Funds - 7B(1)"].strip())
    except (ValueError, KeyError):
        num_funds = 0

    if num_funds == 1:
        score += 15
        signals.append("STRONG:single_fund")
    elif num_funds == 2:
        score += 10
        signals.append("two_funds")
    elif 3 <= num_funds <= 4:
        score += 5
        signals.append("few_funds")
    elif num_funds > 6:
        score -= 5
        signals.append("many_funds")

    # ── Tier 1 name signals ────────────────────────────────────────────
    tier1_hits = []
    for kw in TIER1_NAME_SIGNALS:
        if kw in name_lower:
            tier1_hits.append(kw)
    if tier1_hits:
        score += 15 * len(tier1_hits)
        signals.append(f"NAME_STRONG:{','.join(tier1_hits)}")

    # ── Tier 2 name signals ────────────────────────────────────────────
    tier2_hits = []
    for kw in TIER2_NAME_SIGNALS:
        if kw in name_lower:
            tier2_hits.append(kw)
    if tier2_hits:
        score += 3 * len(tier2_hits)
        signals.append(f"name_moderate:{','.join(tier2_hits[:3])}")

    # ── Soft negatives ─────────────────────────────────────────────────
    for kw in SOFT_NEGATIVE:
        if kw in name_lower:
            score -= 8
            signals.append(f"soft_neg:{kw}")

    # ── URL positive signals ───────────────────────────────────────────
    for kw in URL_POSITIVE:
        if kw in website:
            score += 8
            signals.append(f"url_positive:{kw}")

    for kw in URL_NEGATIVE:
        if kw in website:
            score -= 10
            signals.append(f"url_negative:{kw}")

    # ── AUM scoring ────────────────────────────────────────────────────
    # For sub-$100M, having *some* meaningful AUM is a positive signal
    if 50 <= aum_m < 100:
        score += 10
        signals.append(f"aum_${aum_m:.0f}M")
    elif 20 <= aum_m < 50:
        score += 8
        signals.append(f"aum_${aum_m:.0f}M")
    elif 5 <= aum_m < 20:
        score += 5
        signals.append(f"aum_${aum_m:.0f}M")
    elif 0 < aum_m < 5:
        score += 2
        signals.append(f"aum_${aum_m:.1f}M")
    else:
        signals.append("aum_unreported")

    # ── Geography bonus ────────────────────────────────────────────────
    country = row["Main Office Country"].strip()
    state = row["Main Office State"].strip()
    city = row["Main Office City"].strip()

    # International firms are interesting (less picked-over by US allocators)
    if country != "United States":
        score += 5
        signals.append(f"intl:{country}")

    # Major financial centers slightly positive (access to talent/deals)
    financial_cities = ["NEW YORK", "LONDON", "HONG KONG", "SINGAPORE",
                       "SAN FRANCISCO", "BOSTON", "CHICAGO", "TORONTO",
                       "ZURICH", "GENEVA", "SYDNEY", "MUMBAI"]
    if city.upper() in financial_cities:
        score += 3
        signals.append(f"fin_center:{city}")

    # ── Clean regulatory record ────────────────────────────────────────
    has_disclosure = row.get("11", "").strip() == "Y"
    if has_disclosure:
        score -= 10
        signals.append("PENALTY:regulatory_disclosure")
    else:
        score += 5
        signals.append("clean_record")

    # ── Website existence (must have) ──────────────────────────────────
    if not website or website in ["n/a", "none", ""]:
        score -= 20
        signals.append("PENALTY:no_website")

    return score, signals, disqualified


def main():
    with open(CSV_FILE, "r", encoding="latin-1") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} firms from SEC FOIA data")

    # Filter to sub-$100M first
    sub100 = []
    for row in rows:
        assets = parse_assets(row["Total Gross Assets of Private Funds"])
        aum_m = assets / 1e6
        website = row["Website Address"].strip()
        if aum_m < 100 and website:
            sub100.append(row)
    print(f"Sub-$100M firms with websites: {len(sub100)}")

    # Score all
    scored = []
    disqualified_count = 0
    for row in sub100:
        score, signals, disq = screen_firm(row)
        if disq:
            disqualified_count += 1
            continue
        scored.append((score, signals, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    print(f"Disqualified: {disqualified_count}")
    print(f"Remaining after screen: {len(scored)}")
    print(f"Score range: {scored[0][0]} to {scored[-1][0]}")

    # Show distribution
    brackets = [(60, 999), (50, 59), (40, 49), (30, 39), (20, 29)]
    for lo, hi in brackets:
        count = len([s for s, _, _ in scored if lo <= s <= hi])
        print(f"  Score {lo}-{hi}: {count} firms")

    # Output top candidates (score >= 40)
    top = [(s, sig, r) for s, sig, r in scored if s >= 40]
    print(f"\n{'='*120}")
    print(f"TOP SUB-$100M EMERGING MANAGERS FOR MIT ENDOWMENT (Score >= 40)")
    print(f"{'='*120}")

    results = []
    for rank, (score, signals, row) in enumerate(top, 1):
        assets = parse_assets(row["Total Gross Assets of Private Funds"])
        aum_m = assets / 1e6
        name = row["Primary Business Name"].strip()
        website = row["Website Address"].strip()
        city = row["Main Office City"].strip()
        state = row["Main Office State"].strip()
        country = row["Main Office Country"].strip()
        location = f"{city}, {state}" if state else f"{city}, {country}"

        has_hf = row["Any Hedge Funds"].strip() == "Y"
        has_pe = row["Any PE Funds"].strip() == "Y"
        has_vc = row["Any VC Funds"].strip() == "Y"
        has_other = row["Any Other Funds"].strip() == "Y"
        fund_types = []
        if has_hf: fund_types.append("HF")
        if has_pe: fund_types.append("PE")
        if has_vc: fund_types.append("VC")
        if has_other: fund_types.append("Other")
        num_funds = row["Count of Private Funds - 7B(1)"].strip()

        result = {
            "rank": rank,
            "score": score,
            "name": name,
            "legal_name": row["Legal Name"].strip(),
            "website": website,
            "aum_millions": round(aum_m, 1),
            "fund_types": "/".join(fund_types),
            "num_funds": num_funds,
            "city": city,
            "state": state,
            "country": country,
            "location": location,
            "crd": row["Organization CRD#"].strip(),
            "sec_number": row["SEC#"].strip(),
            "signals": signals,
        }
        results.append(result)

        sig_str = " | ".join(s for s in signals if not s.startswith("name_moderate") and not s.startswith("clean_"))
        print(f"\n#{rank:3d} Score:{score:3d} | {name}")
        print(f"     AUM: ${aum_m:>7.1f}M | Funds: {'/'.join(fund_types)}({num_funds}) | {location}")
        print(f"     Web: {website}")
        print(f"     Signals: {sig_str}")

    # Also show score 30-39 as "watchlist"
    watchlist = [(s, sig, r) for s, sig, r in scored if 30 <= s < 40]
    print(f"\n\n{'='*120}")
    print(f"WATCHLIST: Score 30-39 ({len(watchlist)} firms)")
    print(f"{'='*120}")

    for rank, (score, signals, row) in enumerate(watchlist, len(top)+1):
        name = row["Primary Business Name"].strip()
        website = row["Website Address"].strip()
        aum_m = parse_assets(row["Total Gross Assets of Private Funds"]) / 1e6
        city = row["Main Office City"].strip()
        country = row["Main Office Country"].strip()
        sig_str = " | ".join(s for s in signals if "STRONG" in s or "NAME" in s or "url_positive" in s)
        print(f"  #{rank:3d} Score:{score:3d} | {name:<55} AUM:${aum_m:>7.1f}M | {city}, {country}")
        if sig_str:
            print(f"       {sig_str}")
        result = {
            "rank": rank,
            "score": score,
            "name": name,
            "website": website,
            "aum_millions": round(aum_m, 1),
            "city": city,
            "country": country,
            "signals": signals,
            "watchlist": True,
        }
        results.append(result)

    # Save
    with open("micro_firm_candidates.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nSaved {len(results)} candidates to micro_firm_candidates.json")

    # Summary stats
    top_only = [r for r in results if not r.get("watchlist")]
    print(f"\nSummary:")
    print(f"  Top candidates (score >= 40): {len(top_only)}")
    print(f"  Watchlist (score 30-39): {len(watchlist)}")
    print(f"  Total screened: {len(sub100)}")
    print(f"  Total disqualified: {disqualified_count}")


if __name__ == "__main__":
    main()
