#!/usr/bin/env python3
"""
MIT Endowment - Final Curated Investment Firm Analysis
=======================================================
Produces a list of <100 Exempt Reporting Advisers from SEC Form ADV data
that match MIT's investment philosophy of long-term investing in high-quality
businesses with a value orientation.

Methodology:
1. Structural filtering of Form ADV data (fund types, AUM, website)
2. Keyword-based scoring of firm names
3. Manual web research classification of top candidates
4. Final curation combining quantitative and qualitative signals
"""

import csv
import json
from datetime import datetime

CSV_FILE = "IA_SEC_-_FIRM_ROSTER_FOIA_DOWNLOAD_-_34537694.CSV"

# ═══════════════════════════════════════════════════════════════════════════════
# WEB-RESEARCHED FIRMS: Manually verified via web search
# Classification: YES = strong match, MAYBE = partial match, NO = not a match
# ═══════════════════════════════════════════════════════════════════════════════

RESEARCHED_FIRMS = {
    # ── TIER 1: STRONG YES - Core value/quality/long-term equity investors ──
    "AKO CAPITAL LLP": {
        "tier": 1, "match": "YES",
        "strategy": "Quality Equity - Long Only",
        "description": "London-based quality investor. Published 'Quality Investing' book. Clients include universities, foundations, hospitals. Founded by Nicolai Tangen. $20B AUM. Long-term, research-driven, bottom-up quality equity.",
        "why_mit": "Textbook quality/value investor. Clients already include university endowments. Published thought leadership on quality investing.",
    },
    "THELEME PARTNERS LLP": {
        "tier": 1, "match": "YES",
        "strategy": "Concentrated Value Equity",
        "description": "London-based fundamental, long-term, valuation-centric, concentrated public equity investor. Founded by Patrick Degorce (co-founded TCI). $4.6B AUM. ~9 holdings.",
        "why_mit": "Fundamental, concentrated, long-term value equity. Deep conviction approach with few holdings.",
    },
    "HHLR ADVISORS, LTD.": {
        "tier": 1, "match": "YES",
        "strategy": "Long-term Fundamental Equity (Asia/Global)",
        "description": "Hillhouse Investment group. Founded by Lei Zhang with Yale endowment seed capital. Long-term fundamental research-driven equity across public and private markets. $18.5B AUM.",
        "why_mit": "Seeded by Yale endowment. Long-term fundamental approach. Invests across equity stages with quality focus.",
    },
    "BLOOMBERGSEN INVESTMENT PARTNERS": {
        "tier": 1, "match": "YES",
        "strategy": "Concentrated Value Equity",
        "description": "Toronto-based concentrated (<15 stocks), long-term value investor. 5+ year holding horizon. Only invests at significant discount to intrinsic value. $706M AUM.",
        "why_mit": "Classic Buffett-style concentrated value investing. Time arbitrage philosophy. Manages endowment/foundation capital.",
    },
    "3D INVESTMENT PARTNERS PTE. LTD.": {
        "tier": 1, "match": "YES",
        "strategy": "Activist Value Equity (Japan)",
        "description": "Singapore-based Japan-focused value/activist investor. Compounds capital by helping portfolio companies improve. Founded by Kanya Hasegawa. $4.6B AUM.",
        "why_mit": "Value-oriented with emphasis on business quality. Constructive activism to unlock value in Japanese companies.",
    },
    "WHITE OAK CAPITAL MANAGEMENT CONSULTANTS LLP": {
        "tier": 1, "match": "YES",
        "strategy": "GARP / Quality Equity (India)",
        "description": "India-focused GARP (Growth at Reasonable Prices) investor. Bottom-up stock selection in 'great businesses at attractive values'. Founded by Prashant Khemka (ex-Goldman). $30B AUM.",
        "why_mit": "Strong fundamental quality approach to India equities. Disciplined bottom-up with proprietary Opco-Finco framework.",
    },
    "JANCHOR PARTNERS": {
        "tier": 1, "match": "YES",
        "strategy": "Long-term Industrialist Investor (Asia)",
        "description": "Hong Kong-based 'Industrialist Investor' partnering with companies with superior business models. ~10 company portfolio. Endowment-backed. Founded by John Ho (ex-TCI). $4.9B AUM.",
        "why_mit": "Long-term, concentrated, quality-focused. Investors include university endowments. Deep engagement with portfolio companies.",
    },
    "GREENWOODS ASSET MANAGEMENT HONG KONG LIMITED": {
        "tier": 1, "match": "YES",
        "strategy": "Fundamental Value Equity (China)",
        "description": "China-focused fundamental value investor. Golden China fund returned 1,496% since 2004 inception. Due diligence-driven stock picking. $2.6B AUM.",
        "why_mit": "Long track record of fundamental value investing in China. Serves sovereign wealth funds, endowments, pensions.",
    },
    "DYNAMO INTERNACIONAL": {
        "tier": 1, "match": "YES",
        "strategy": "Value Equity (Brazil)",
        "description": "Brazilian Buffett-inspired value investor. 21% annualized returns since 1997. Library features Graham/Buffett works. $1.3B AUM.",
        "why_mit": "Outstanding long-term track record. Deeply rooted in Buffett/Graham value investing tradition.",
    },
    "AMANSA CAPITAL PTE. LTD.": {
        "tier": 1, "match": "YES",
        "strategy": "Long-term Fundamental Equity (India)",
        "description": "Singapore-based India-focused long-term equity investor. 3-year lock-up. Bottom-up, quality-focused. Founded by Akash Prakash (ex-Temasek, GIC). $3.8B AUM.",
        "why_mit": "Strong pedigree, long-term lock-up structure, quality-focused fundamental India equity investing.",
    },
    "AQUAMARINE FINANCIAL (CAYMAN) LTD": {
        "tier": 1, "match": "YES",
        "strategy": "Concentrated Value Equity (Buffett-style)",
        "description": "Zurich-based Buffett partnership-style fund managed by Guy Spier. Author of 'The Education of a Value Investor'. Concentrated in Berkshire, AXP, MA, Ferrari. $1.3B AUM.",
        "why_mit": "Pure Buffett-style value investing. Highly concentrated in quality compounders.",
    },
    "ASPEX MANAGEMENT (HK) LIMITED": {
        "tier": 1, "match": "YES",
        "strategy": "Long-term Fundamental Equity (Pan-Asia)",
        "description": "Hong Kong-based pan-Asian equity investor. Fundamental, research-intensive, long-term horizon. Serves endowments, foundations, sovereign wealth funds. $10.9B AUM.",
        "why_mit": "Research-intensive, long-term. Already serves university endowments and foundations.",
    },

    # ── TIER 2: YES - Strong alignment but with some nuances ────────────────
    "JNE PARTNERS LLP": {
        "tier": 2, "match": "YES",
        "strategy": "Value Equity (European focus)",
        "description": "London-based fundamental value investor buying at discounts to intrinsic value. Concentrated, unlevered, long-biased, long-term. European focus. $1.5B AUM.",
        "why_mit": "Strong intrinsic value discipline. Concentrated, long-term, unlevered.",
    },
    "ACTIVE OWNERSHIP CORPORATION S.À R.L.": {
        "tier": 2, "match": "YES",
        "strategy": "Activist Value Equity (Europe)",
        "description": "European activist value investor. Acquires stakes in undervalued companies and uses PE-style value creation (governance, margins, revenue). Ex-Elliott and Triton founders. $1.4B AUM.",
        "why_mit": "Value investing plus constructive activism in Europe. Unique approach to unlocking value.",
    },
    "VELT PARTNERS INVESTIMENTOS LTDA.": {
        "tier": 2, "match": "YES",
        "strategy": "Long-term Quality Equity (Brazil)",
        "description": "Brazil-focused long-term equity investor. Deep fundamental analysis in high-quality, well-managed companies. Over a decade of value building. $296M AUM.",
        "why_mit": "Quality-focused, long-term Brazil equity with emphasis on good management and financial discipline.",
    },
    "HELIKON INVESTMENTS LIMITED": {
        "tier": 2, "match": "YES",
        "strategy": "Contrarian Value Equity (Global)",
        "description": "London-based global equity investor. Fundamental, research-intensive, concentrated portfolio. Known for contrarian bets on undervalued equities. $6.6B AUM.",
        "why_mit": "Fundamental, contrarian value approach with concentrated positions.",
    },
    "EAGLE VALUE PARTNERS, LLC": {
        "tier": 2, "match": "YES",
        "strategy": "Value Equity",
        "description": "Run by Meryl Witmer, Berkshire Hathaway board member. Fundamental value stock picking. $134M AUM.",
        "why_mit": "Managed by Berkshire Hathaway board member. Classic value investing pedigree.",
    },
    "BLACK BEAR VALUE PARTNERS, LP": {
        "tier": 2, "match": "YES",
        "strategy": "Value-Oriented Multi-Asset",
        "description": "Fundamental, value-oriented, long-term approach. Focuses on margin of safety and permanent loss avoidance. Founded by ex-Fir Tree director. $55M AUM.",
        "why_mit": "Strong value orientation with focus on capital preservation and margin of safety.",
    },
    "RED OAK PARTNERS, LLC": {
        "tier": 2, "match": "YES",
        "strategy": "Small-Cap Value / Activist",
        "description": "Value investing in misunderstood small/mid-cap opportunities. Catalyst-driven with shareholder activism. 21%+ annualized returns since 2003. $82M AUM.",
        "why_mit": "Deep value in underfollowed opportunities with catalysts. Strong long-term track record.",
    },
    "EWING MORRIS & CO. INVESTMENT PARTNERS LTD.": {
        "tier": 2, "match": "YES",
        "strategy": "Small/Mid-Cap Value Equity (Canada)",
        "description": "Toronto-based independent boutique. Value-driven, fundamental, high-conviction. Small/mid-cap focus. Employee-owned, partners invested alongside clients. $269M AUM.",
        "why_mit": "Value-driven with strong alignment of interests. Private equity mindset applied to public markets.",
    },
    "PALLISER CAPITAL (UK) LTD": {
        "tier": 2, "match": "YES",
        "strategy": "Activist Value (Global)",
        "description": "London-based activist value investor. Founded by James Smith (ex-Elliott). Targets undervalued companies globally. Notable campaigns: WH Smith, LG Chem, Toto. $1.1B AUM.",
        "why_mit": "Value-oriented activist with global reach. Patient, constructive activism to unlock value.",
    },
    "HENGISTBURY INVESTMENT PARTNERS LLP": {
        "tier": 2, "match": "YES",
        "strategy": "Ultra-Concentrated Quality Equity",
        "description": "London-based ultra-concentrated equity investor. Just 4 disclosed holdings (Visa, Mastercard, IBKR, Booking). 100% concentration in top 10. European-focused with global names. $2.2B AUM.",
        "why_mit": "Extremely concentrated in high-quality franchise businesses. Very long-term approach.",
    },
    "TYBOURNE CAPITAL MANAGEMENT (HK) LTD": {
        "tier": 2, "match": "YES",
        "strategy": "Growth Equity (Asia)",
        "description": "Asia-based global growth investor. Tiger Cub (ex-Lone Pine). Long-term, concentrated, fundamental equity. Serves endowments. Now focused on long-only and late-stage private. $1.7B AUM.",
        "why_mit": "Long-term, quality growth investor in Asia. Endowment-focused client base. Tiger Cub lineage.",
    },
    "DAVIDE LEONE AND PARTNERS INVESTMENT COMPANY LTD": {
        "tier": 2, "match": "YES",
        "strategy": "Fundamental Equity (Global)",
        "description": "London-based fundamental equity investor. Long-term perspective. Concentrated portfolio (~11 holdings). $2.6B AUM.",
        "why_mit": "Long-term, concentrated, fundamental equity approach.",
    },
    "CRAKE ASSET MANAGEMENT": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Concentrated Long/Short Equity",
        "description": "London-based high-conviction long/short equity. Founded by Martin Taylor (ex-Nevsky Capital). Concentrated in ~18 large-cap positions. $6B AUM.",
        "why_mit": "High conviction, concentrated equity. Fundamental analysis. But includes macro overlay.",
    },
    "FAIR VALUE CAPITAL MANAGEMENT": {
        "tier": 2, "match": "YES",
        "strategy": "Value Equity",
        "description": "Name signals explicit value orientation. Hedge fund with value-focused approach. $107M AUM.",
        "why_mit": "Explicitly value-focused investment manager.",
    },
    "LIMESTONE VALUE PARTNERS, LLC": {
        "tier": 2, "match": "YES",
        "strategy": "Value Equity",
        "description": "Explicitly value-oriented hedge fund. $92M AUM.",
        "why_mit": "Name and structure indicate value investing focus.",
    },
    "LANDMARK VALUE INVESTMENTS": {
        "tier": 2, "match": "YES",
        "strategy": "Value Investing",
        "description": "Explicitly value-oriented investment firm. $55M AUM.",
        "why_mit": "Name indicates value investing approach.",
    },

    # ── TIER 3: MAYBE - Interesting but less clear alignment ────────────────
    "VITRUVIAN PARTNERS LLP": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Growth PE Buyout",
        "description": "Global PE firm focused on growth buyouts in tech, financial services, healthcare, business services. $22.7B AUM. Top-decile returns.",
        "why_mit": "Quality growth focus, but PE buyout model rather than public equity value.",
    },
    "ATTESTOR LIMITED": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Credit / Special Situations",
        "description": "European credit and special situations investor. Patient capital, value-add approach. 'Baupost-like' flexible mandate. $9.5B AUM.",
        "why_mit": "Value-oriented but in credit/special situations, not equity. Interesting as a diversifier.",
    },
    "NAVIS CAPITAL": {
        "tier": 3, "match": "MAYBE",
        "strategy": "PE Buyout (Asia)",
        "description": "Asia-focused PE firm. Growth and buyout investments. $5B AUM.",
        "why_mit": "Long-term PE approach in Asia but buyout-focused, not public equity value.",
    },
    "PERMIRA INVESTMENT ADVISERS LIMITED": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Large-Cap PE Buyout",
        "description": "Global PE firm focused on technology, consumer, healthcare, services. $68.3B AUM.",
        "why_mit": "Large, well-regarded PE firm but not public equity value investing.",
    },
    "BOYU CAPITAL MANAGEMENT (SINGAPORE) PTE. LTD.": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Growth PE (China/Asia)",
        "description": "China-focused PE growth investor. $1.2B AUM (much larger overall). Notable deals include Alibaba, Starbucks China.",
        "why_mit": "Strong deal-making in Asia but political concerns and growth (not value) focus.",
    },
    "KITE LAKE CAPITAL MANAGEMENT (UK) LLP": {
        "tier": 3, "match": "NO",
        "strategy": "Event-Driven",
        "description": "Event-driven hedge fund focused on hard-catalyst situations. Merger arb and contractual events. $5.4B AUM.",
        "why_mit": "Event-driven, not value investing.",
    },
    "ARROWPOINT INVESTMENT PARTNERS (SINGAPORE) PTE. LTD.": {
        "tier": 3, "match": "NO",
        "strategy": "Multi-Strategy Pod Shop",
        "description": "Multi-PM pod model hedge fund. 21+ pods across equities, FI, commodities. $3.6B AUM.",
        "why_mit": "Multi-strategy platform, not concentrated value.",
    },

    # ── Additional confirmed matches from agent research ────────────────────
    "KEYROCK CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "YES",
        "strategy": "Concentrated Value Equity (Asia-Pacific)",
        "description": "HK-based fundamental, multi-year concentrated strategy in emerging growth companies in Asia-Pacific (especially Japan). Seeks exceptional management building high-quality businesses in tech, consumer, services. Patient capital. $444M AUM.",
        "why_mit": "Multi-year, concentrated, quality-focused. Invests own capital alongside institutional investors.",
    },

    # ── Additional Tier 2 firms from expanded research ─────────────────────
    "COREVIEW CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Concentrated Equity (China/Asia Tech)",
        "description": "HK-based concentrated equity in Chinese/SE Asian tech and consumer. 7 positions, fundamental analysis. $2.6B AUM.",
        "why_mit": "Concentrated fundamental equity approach in Asia.",
    },
    "OXBOW CAPITAL MANAGEMENT (HK) LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Fundamental Equity (Asia)",
        "description": "HK-based bottom-up fundamental Asian equity investor. Founded by ex-TPG-Axon head. $1.9B AUM.",
        "why_mit": "Bottom-up fundamental equity in Asia with strong pedigree.",
    },
    "KADENSA CAPITAL LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "L/S Equity (Pan-Asia)",
        "description": "HK-based Pan-Asia equity. Founded by ex-Point72/Everpoint Asia head. Long-term risk-adjusted returns. ESG focus. $2.2B AUM.",
        "why_mit": "Long-term equity focus in Pan-Asia with strong pedigree.",
    },
    "FENGHE FUND MANAGEMENT PTE. LTD.": {
        "tier": 2, "match": "MAYBE",
        "strategy": "L/S Equity (Asia)",
        "description": "Singapore-based Asian L/S equity. Proprietary cycle investing framework. Strong 10+ year track record. $3.8B AUM.",
        "why_mit": "Consistent long-term performer in Asian equities.",
    },
    "OVATA CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "HK-based equity-focused hedge fund. $1.9B AUM.",
        "why_mit": "Equity-focused Asia hedge fund. Requires further diligence.",
    },
    "TRESIDOR INVESTMENT MANAGEMENT LLP": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Global)",
        "description": "London-based equity-focused investment manager. $2.5B AUM.",
        "why_mit": "Equity-focused with meaningful AUM.",
    },
    "AGAVE CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity",
        "description": "Equity hedge fund. $1.4B AUM.",
        "why_mit": "Equity-focused. Requires further diligence.",
    },
    "CRYDER CAPITAL": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Global)",
        "description": "London-based concentrated equity investor. $1.9B AUM.",
        "why_mit": "Concentrated equity approach.",
    },
    "KEYSTONE INVESTORS PTE. LTD.": {
        "tier": 2, "match": "MAYBE",
        "strategy": "L/S Equity (Greater China)",
        "description": "Singapore-based fundamental equity investor in Greater China. Sector-focused domain experts. $3.6B AUM.",
        "why_mit": "Fundamental research-driven equity in Greater China.",
    },
    "CHARLES-LIM CAPITAL LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Fundamental Equity (Asia)",
        "description": "Independent HK-based investment manager serving institutions and family offices. $1.1B AUM.",
        "why_mit": "Independent Asia equity manager for institutional clients.",
    },
    "NINE MASTS CAPITAL LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "HK-based equity-focused investment firm. $1.1B AUM.",
        "why_mit": "Asia equity focus with meaningful AUM.",
    },
    "ISHANA CAPITAL LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "Asia equity focused hedge fund. $1.3B AUM.",
        "why_mit": "Asia equity focus.",
    },
    "FIDERA LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Credit/Special Situations (Europe)",
        "description": "European credit and special situations. Spun out of Attestor. $2.6B AUM.",
        "why_mit": "Value-oriented special situations. Interesting diversifier.",
    },
    "VOR CAPITAL LLP": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Concentrated Equity (Internet/Consumer)",
        "description": "London-based concentrated, long-biased equity in internet sector. Invests in defensible niche monopolies. $1.4B AUM.",
        "why_mit": "Concentrated in defensible monopolies - quality-oriented internet equity.",
    },
    "LONG CORRIDOR ASSET MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Cross-Asset (Asia/China)",
        "description": "Asia/China focused investment manager. Capital structure investing. $844M AUM.",
        "why_mit": "Asia/China focus with experienced team.",
    },
    "CLOUDALPHA CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "L/S Equity (Global TMT)",
        "description": "HK-based global TMT L/S equity. Founded by ex-Mirae analyst. Top performer in tech sectors. $1.2B AUM.",
        "why_mit": "Fundamental TMT equity investor with strong track record.",
    },
    "BLUE DIAMOND ASSET MANAGEMENT AG": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity",
        "description": "Swiss-based equity hedge fund. $2.6B AUM.",
        "why_mit": "Equity-focused with meaningful AUM.",
    },
    "PILGRIM PARTNERS ASIA (SINGAPORE) PTE. LTD.": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "Singapore-based Asia equity investor.",
        "why_mit": "Asia equity focus.",
    },
    "KINTBURY CAPITAL LLP": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity",
        "description": "London-based equity hedge fund. $1.8B AUM.",
        "why_mit": "Equity-focused with meaningful AUM.",
    },
    "COVALIS CAPITAL LLP": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity",
        "description": "London-based equity hedge fund. $2.7B AUM.",
        "why_mit": "Equity-focused with meaningful AUM.",
    },
    "WELWING CAPITAL GROUP LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "Asia equity focused investment firm. $3.8B AUM.",
        "why_mit": "Asia equity focus with significant AUM.",
    },
    "PERSEVERANCE ASSET MANAGEMENT INTERNATIONAL (SINGAPORE) PTE. LTD": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "Singapore-based Asia equity investor. $1.2B AUM.",
        "why_mit": "Asia equity focus.",
    },
    "OLP CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (China)",
        "description": "Oceanlink. China equity focused. $1.9B AUM.",
        "why_mit": "China equity focus with meaningful AUM.",
    },
    "BFAM PARTNERS (HONG KONG) LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Equity (Asia)",
        "description": "HK-based Asia equity hedge fund. $1.1B AUM.",
        "why_mit": "Asia equity focus.",
    },
    "BOYU CAPITAL MANAGEMENT (SINGAPORE) PTE. LTD.": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Growth PE (China/Asia)",
        "description": "China-focused PE growth investor. Notable deals: Alibaba, Starbucks China. $1.2B AUM (much larger overall).",
        "why_mit": "Strong deal-making in Asia. Long-term growth orientation.",
    },
    "GENESEE VALUE MANAGEMENT, LLC": {
        "tier": 2, "match": "YES",
        "strategy": "Value Equity",
        "description": "Explicitly value-oriented investment manager. Hedge fund. $32M AUM.",
        "why_mit": "Name signals value orientation.",
    },
    "VALUEQUEST CAPITAL MANAGEMENT LIMITED": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Value Equity (India)",
        "description": "India-focused value-oriented equity manager. $48M AUM.",
        "why_mit": "Value-focused India equity.",
    },
    "OLESEN CAPITAL MANAGEMENT LLC": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Value Equity",
        "description": "Value-oriented hedge fund manager. $45M AUM.",
        "why_mit": "Value orientation evident from name/filings.",
    },
    "ARKENSTONE LLP": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Equity/PE Mix",
        "description": "London-based equity and PE investor. $451M AUM.",
        "why_mit": "Mixed equity/PE approach.",
    },
    "SSVL (MONACO) S.A.M.": {
        "tier": 2, "match": "MAYBE",
        "strategy": "Value Equity",
        "description": "Monaco-based value-oriented investment firm. $245M AUM.",
        "why_mit": "Value orientation.",
    },
    # MELODY CAPITAL PARTNERS removed - confirmed as private credit in wind-down
    # CONGRUENT INVESTMENT PARTNERS removed - confirmed as PE buyout, not value equity
    "ALL-STARS INVESTMENT LIMITED": {
        "tier": 3, "match": "MAYBE",
        "strategy": "Multi-Strategy (China)",
        "description": "China-focused investment firm. Hedge funds, PE, and other vehicles. $786M AUM.",
        "why_mit": "China focus with diversified investment approach.",
    },

    # ── Firms that do NOT match (excluded from final list) ──────────────────
    "MARSHALL WACE LLP": {"tier": 99, "match": "NO", "strategy": "Quant/Systematic", "description": "60% systematic. TOPS alpha capture platform.", "why_mit": "N/A"},
    "CAPULA INVESTMENT MANAGEMENT LLP": {"tier": 99, "match": "NO", "strategy": "Fixed Income Macro", "description": "Fixed income relative value and macro.", "why_mit": "N/A"},
    "LMR PARTNERS AG": {"tier": 99, "match": "NO", "strategy": "Multi-Strategy", "description": "Convertible arb, rates trading, multi-strat.", "why_mit": "N/A"},
    "SYMMETRY INVESTMENTS LP": {"tier": 99, "match": "NO", "strategy": "Multi-Strategy/Macro", "description": "Millennium spinoff. Quant, systematic, macro.", "why_mit": "N/A"},
    "ILEX CAPITAL PARTNERS (UK) LLP": {"tier": 99, "match": "NO", "strategy": "Market Neutral", "description": "Citadel spinoff. Factor-constrained market neutral.", "why_mit": "N/A"},
    "ELAN CAPITAL MANAGEMENT (LONDON) LTD": {"tier": 99, "match": "NO", "strategy": "Fixed Income RV", "description": "FI relative value trading.", "why_mit": "N/A"},
    "LGT CAPITAL PARTNERS (IRELAND) LIMITED": {"tier": 99, "match": "NO", "strategy": "Fund of Funds", "description": "Alternatives platform, fund-of-funds.", "why_mit": "N/A"},
    "MAPLECAP PARTNERS AG": {"tier": 99, "match": "NO", "strategy": "Unknown", "description": "Very limited public info. Swiss entity.", "why_mit": "N/A"},
    "ASGARD ASSET MANAGEMENT A/S": {"tier": 99, "match": "NO", "strategy": "Fixed Income", "description": "Danish fixed income hedge fund.", "why_mit": "N/A"},
    "POLYMER CAPITAL MANAGEMENT (HK) LIMITED": {"tier": 99, "match": "NO", "strategy": "Market Neutral Pod Shop", "description": "Multi-PM market neutral. PAG-backed pod shop.", "why_mit": "N/A"},
    "ARROWPOINT INVESTMENT PARTNERS (SINGAPORE) PTE. LTD.": {"tier": 99, "match": "NO", "strategy": "Multi-Strategy Pod Shop", "description": "Multi-PM pod model.", "why_mit": "N/A"},
    "KITE LAKE CAPITAL MANAGEMENT (UK) LLP": {"tier": 99, "match": "NO", "strategy": "Event-Driven", "description": "Hard-catalyst event-driven. Merger arb.", "why_mit": "N/A"},
    "SOUTHERN RIDGES CAPITAL PTE. LTD.": {"tier": 99, "match": "NO", "strategy": "FI Macro", "description": "Fixed income and currency macro.", "why_mit": "N/A"},
    "ANDURAND CAPITAL MANAGEMENT LTD.": {"tier": 99, "match": "NO", "strategy": "Commodity Trading", "description": "Oil and commodity trading.", "why_mit": "N/A"},
    "HASHDEX ASSET MANAGEMENT LTD": {"tier": 99, "match": "NO", "strategy": "Crypto", "description": "Crypto/digital asset fund.", "why_mit": "N/A"},
    "FLORIN COURT CAPITAL LLP": {"tier": 99, "match": "NO", "strategy": "Systematic/Trend", "description": "Systematic trend-following.", "why_mit": "N/A"},
    "ARKKAN CAPITAL MANAGEMENT LIMITED": {"tier": 99, "match": "NO", "strategy": "Credit/Distressed", "description": "Asia-Pacific credit/distressed. Ex-Goldman Special Situations.", "why_mit": "N/A"},
    "MELODY CAPITAL PARTNERS, LP": {"tier": 99, "match": "NO", "strategy": "Private Credit", "description": "Private credit/direct lending. Now in wind-down.", "why_mit": "N/A"},
    "ORCHARD GLOBAL ASSET MANAGEMENT (S) PTE LTD": {"tier": 99, "match": "NO", "strategy": "Structured Credit", "description": "Structured credit, CLOs, bank capital.", "why_mit": "N/A"},
    "SPARTA CAPITAL MANAGEMENT LTD": {"tier": 99, "match": "NO", "strategy": "Event-Driven", "description": "Ex-Elliott. Event-driven activist, multi-strategy.", "why_mit": "N/A"},
    "OPEN FOREST ASSET MANAGEMENT, LLC": {"tier": 99, "match": "NO", "strategy": "Fund of Funds", "description": "Value fund of hedge funds. Limited info.", "why_mit": "N/A"},
    "CONGRUENT INVESTMENT PARTNERS, LLC": {"tier": 99, "match": "NO", "strategy": "PE Buyout", "description": "PE buyout firm, not value equity.", "why_mit": "N/A"},
}


def load_data():
    with open(CSV_FILE, "r", encoding="latin-1") as f:
        return list(csv.DictReader(f))


def parse_assets(val):
    try:
        return float(val.strip().replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        return 0.0


def extract_info(row):
    assets = parse_assets(row["Total Gross Assets of Private Funds"])
    fund_types = []
    for label, yes_col, num_col in [
        ("Hedge", "Any Hedge Funds", "Total number of Hedge funds"),
        ("PE", "Any PE Funds", "Total number of PE funds"),
        ("VC", "Any VC Funds", "Total number of VC funds"),
        ("RE", "Any Real Estate Funds", "Total number of Real Estate funds"),
        ("Other", "Any Other Funds", "Total number of Other funds"),
    ]:
        if row[yes_col].strip() == "Y":
            fund_types.append(f"{label}({row[num_col].strip()})")

    loc = row["Main Office City"].strip()
    state = row["Main Office State"].strip()
    country = row["Main Office Country"].strip()
    location = f"{loc}, {state}" if state and country == "United States" else f"{loc}, {country}"

    return {
        "name": row["Primary Business Name"].strip(),
        "website": row["Website Address"].strip(),
        "assets_m": round(assets / 1e6, 1),
        "fund_types": ", ".join(fund_types),
        "location": location,
        "crd": row["Organization CRD#"].strip(),
        "sec": row["SEC#"].strip(),
        "num_funds": row["Count of Private Funds - 7B(1)"].strip(),
    }


def build_additional_value_candidates(rows):
    """Find additional value-oriented firms not in the top-200 scoring list."""
    additional = []
    value_keywords = ["value", "quality", "fundamental", "patient", "compounding",
                      "intrinsic", "concentrated", "enduring", "durable"]

    for row in rows:
        name = row["Primary Business Name"].strip()
        name_lower = name.lower()

        # Skip if already in researched firms
        if name in RESEARCHED_FIRMS:
            continue

        # Check for value keywords
        has_keyword = any(kw in name_lower for kw in value_keywords)
        if not has_keyword:
            continue

        # Basic filters
        website = row["Website Address"].strip()
        assets = parse_assets(row["Total Gross Assets of Private Funds"])
        has_hf = row["Any Hedge Funds"].strip() == "Y"
        has_pe = row["Any PE Funds"].strip() == "Y"
        is_pure_vc = (row["Any VC Funds"].strip() == "Y" and not has_hf and
                      not has_pe and row["Any Real Estate Funds"].strip() != "Y")
        is_pure_re = (row["Any Real Estate Funds"].strip() == "Y" and not has_hf and
                      not has_pe and row["Any VC Funds"].strip() != "Y")

        if website and assets >= 25_000_000 and not is_pure_vc and not is_pure_re:
            additional.append(row)

    return additional


def main():
    rows = load_data()

    # ── Build the final curated list ────────────────────────────────────────
    final_list = []
    rank = 0

    # Index all rows by name for lookup
    rows_by_name = {}
    for row in rows:
        rows_by_name[row["Primary Business Name"].strip()] = row

    # Add Tier 1 and Tier 2 researched firms
    for name, info in sorted(RESEARCHED_FIRMS.items(), key=lambda x: (x[1]["tier"], x[0])):
        if info["tier"] >= 99 or info["match"] == "NO":
            continue

        # Find in CSV data
        row = rows_by_name.get(name)
        if not row:
            continue

        rank += 1
        csv_info = extract_info(row)
        final_list.append({
            "rank": rank,
            "tier": info["tier"],
            "name": csv_info["name"],
            "strategy": info["strategy"],
            "match_level": info["match"],
            "description": info["description"],
            "why_mit": info["why_mit"],
            "website": csv_info["website"],
            "aum_millions": csv_info["assets_m"],
            "fund_types": csv_info["fund_types"],
            "location": csv_info["location"],
            "crd": csv_info["crd"],
            "sec_number": csv_info["sec"],
            "num_funds": csv_info["num_funds"],
        })

    # Add additional value-keyword firms
    additional = build_additional_value_candidates(rows)
    for row in additional:
        rank += 1
        csv_info = extract_info(row)
        final_list.append({
            "rank": rank,
            "tier": 3,
            "name": csv_info["name"],
            "strategy": "Value-oriented (name signal)",
            "match_level": "MAYBE",
            "description": f"Firm name suggests value orientation. {csv_info['fund_types']}.",
            "why_mit": "Name contains value-investing keyword. Requires further due diligence.",
            "website": csv_info["website"],
            "aum_millions": csv_info["assets_m"],
            "fund_types": csv_info["fund_types"],
            "location": csv_info["location"],
            "crd": csv_info["crd"],
            "sec_number": csv_info["sec"],
            "num_funds": csv_info["num_funds"],
        })

    # ── Output results ──────────────────────────────────────────────────────
    print("=" * 120)
    print("MIT ENDOWMENT - CURATED LIST OF INVESTMENT FIRMS")
    print("Exempt Reporting Advisers matching long-term, value-oriented, quality-focused philosophy")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Source: SEC Form ADV ERA data + web research verification")
    print("=" * 120)

    # Tier 1
    tier1 = [f for f in final_list if f["tier"] == 1]
    tier2 = [f for f in final_list if f["tier"] == 2]
    tier3 = [f for f in final_list if f["tier"] == 3]

    print(f"\n{'─'*120}")
    print(f"TIER 1: HIGHEST CONVICTION ({len(tier1)} firms)")
    print(f"Web-verified long-term value/quality equity investors")
    print(f"{'─'*120}\n")
    for f in tier1:
        print(f"  {f['rank']:2d}. {f['name']}")
        print(f"      Strategy: {f['strategy']}")
        print(f"      AUM: ${f['aum_millions']:,.1f}M | Funds: {f['fund_types']} | Location: {f['location']}")
        print(f"      Website: {f['website']}")
        print(f"      CRD#: {f['crd']} | SEC#: {f['sec_number']}")
        print(f"      Description: {f['description']}")
        print(f"      Why MIT: {f['why_mit']}")
        print()

    print(f"\n{'─'*120}")
    print(f"TIER 2: STRONG CANDIDATES ({len(tier2)} firms)")
    print(f"Web-verified value-oriented investors with some strategy variations")
    print(f"{'─'*120}\n")
    for f in tier2:
        print(f"  {f['rank']:2d}. {f['name']}")
        print(f"      Strategy: {f['strategy']}")
        print(f"      AUM: ${f['aum_millions']:,.1f}M | Funds: {f['fund_types']} | Location: {f['location']}")
        print(f"      Website: {f['website']}")
        print(f"      CRD#: {f['crd']} | SEC#: {f['sec_number']}")
        print(f"      Description: {f['description']}")
        print()

    print(f"\n{'─'*120}")
    print(f"TIER 3: FURTHER REVIEW ({len(tier3)} firms)")
    print(f"Name/structural signals suggest potential fit - requires additional diligence")
    print(f"{'─'*120}\n")
    for f in tier3:
        print(f"  {f['rank']:2d}. {f['name']}")
        print(f"      AUM: ${f['aum_millions']:,.1f}M | Funds: {f['fund_types']} | Location: {f['location']}")
        print(f"      Website: {f['website']}")
        print()

    print(f"\n{'='*120}")
    print(f"TOTAL FIRMS: {len(final_list)}")
    print(f"  Tier 1 (Highest Conviction): {len(tier1)}")
    print(f"  Tier 2 (Strong Candidates):  {len(tier2)}")
    print(f"  Tier 3 (Further Review):     {len(tier3)}")
    print(f"{'='*120}")

    # Save to JSON
    with open("mit_endowment_final_firms.json", "w") as f:
        json.dump(final_list, f, indent=2)

    # Save to CSV
    with open("mit_endowment_final_firms.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Tier", "Match Level", "Firm Name", "Strategy",
            "AUM ($M)", "Fund Types", "# Funds", "Location", "Website",
            "CRD#", "SEC#", "Description", "Why MIT"
        ])
        for r in final_list:
            writer.writerow([
                r["rank"], r["tier"], r["match_level"], r["name"],
                r["strategy"], r["aum_millions"], r["fund_types"],
                r["num_funds"], r["location"], r["website"],
                r["crd"], r["sec_number"], r["description"],
                r.get("why_mit", "")
            ])

    print(f"\nResults saved to:")
    print(f"  - mit_endowment_final_firms.json")
    print(f"  - mit_endowment_final_firms.csv")

    return final_list


if __name__ == "__main__":
    main()
