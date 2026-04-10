#!/usr/bin/env python3
"""
GovCon Pipeline — Nightly Data Fetcher
Runs via GitHub Actions. Pulls from SAM.gov + SBIR and writes data/opportunities.json.
Requires SAM_API_KEY environment variable (set as GitHub Secret).
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

# ── Config ────────────────────────────────────────────────────
API_KEY   = os.environ.get("SAM_API_KEY", "")
OUT_FILE  = os.path.join(os.path.dirname(__file__), "..", "data", "opportunities.json")

# NAICS codes for digital services / IT / AI
NAICS_CODES = ["541511", "541512", "541519", "518210", "541715"]

# Set-asides to prioritize (used for scoring, not filtering)
PRIORITY_SET_ASIDES = ["HUBZone", "Small Business", "WOSB", "8(a)", "SDVOSB"]


# ── Scoring ───────────────────────────────────────────────────
def score(opp: dict) -> int:
    s = 0
    if opp.get("naics") in NAICS_CODES:
        s += 30
    else:
        s += 10
    sa = opp.get("setAside", "")
    if any(p.lower() in sa.lower() for p in PRIORITY_SET_ASIDES):
        s += 25
    val = opp.get("value", 0)
    if 500_000 <= val <= 10_000_000:
        s += 15
    elif val > 0:
        s += 5
    if opp.get("type") in ("Solicitation", "RFP", "RFQ", "Presolicitation"):
        s += 10
    kw = (opp.get("title", "") + " " + opp.get("description", "")).lower()
    for word in ["digital", "ai", "ml", "data", "cloud", "agile", "devops", "python", "react", "aws", "moderniz"]:
        if word in kw:
            s += 2
    return min(s, 99)


# ── SAM.gov Fetch ─────────────────────────────────────────────
def fetch_sam() -> list:
    if not API_KEY:
        print("⚠  SAM_API_KEY not set — skipping SAM.gov fetch")
        return []

    today    = datetime.now(timezone.utc)
    from_dt  = (today - timedelta(days=60)).strftime("%m/%d/%Y")
    to_dt    = today.strftime("%m/%d/%Y")

    # Pass each NAICS code as a separate ncode param (comma-separated not supported)
    ncode_params = "&".join(f"ncode={n}" for n in NAICS_CODES)

    url = (
        f"https://api.sam.gov/prod/opportunities/v2/search"
        f"?api_key={API_KEY}"
        f"&limit=100"
        f"&postedFrom={urllib.parse.quote(from_dt)}"
        f"&postedTo={urllib.parse.quote(to_dt)}"
        f"&ptype=o&ptype=p&ptype=k&ptype=r&ptype=s"
        f"&{ncode_params}"
    )

    print(f"Fetching SAM.gov: {url[:80]}…")
    try:
        req  = urllib.request.Request(url, headers={"User-Agent": "GovConPipeline/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"⚠  SAM.gov error: {e.code} {e.reason} — {body}")
        return []
    except Exception as e:
        print(f"⚠  SAM.gov error: {e}")
        return []

    raw  = data.get("opportunitiesData", [])
    opps = []
    for o in raw:
        naics = str(o.get("naicsCode") or "541512")
        # Only keep if NAICS matches our targets
        if not any(naics.startswith(n[:4]) for n in NAICS_CODES):
            continue
        opps.append({
            "id":         o.get("noticeId") or o.get("id", ""),
            "source":     "SAM.gov",
            "title":      o.get("title", ""),
            "agency":     o.get("fullParentPathName") or o.get("departmentName") or "Federal Agency",
            "naics":      naics,
            "setAside":   o.get("typeOfSetAsideDescription") or o.get("typeOfSetAside") or "",
            "type":       o.get("baseType") or o.get("type") or "Solicitation",
            "postedDate": (o.get("postedDate") or "")[:10],
            "dueDate":    (o.get("responseDeadLine") or "")[:10],
            "value":      int(o.get("award", {}).get("amount") or 0),
            "description": o.get("description") or "",
            "solNum":     o.get("solicitationNumber") or "",
            "url":        f"https://sam.gov/opp/{o.get('noticeId', '')}/view",
        })

    print(f"  → {len(opps)} SAM.gov opportunities fetched")
    return opps


# ── SBIR Fetch ────────────────────────────────────────────────
def fetch_sbir() -> list:
    opps = []
    # Single request for all open solicitations to avoid rate limiting
    url = "https://api.www.sbir.gov/public/api/solicitations?open=1&rows=50"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GovConPipeline/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            items = json.loads(resp.read())
        for item in (items if isinstance(items, list) else []):
            opps.append({
                "id":         f"SBIR-{item.get('solicitation_id', '')}",
                "source":     "SBIR",
                "title":      item.get("solicitation_title", ""),
                "agency":     item.get("agency", ""),
                "naics":      "541715",
                "setAside":   "Small Business",
                "type":       f"SBIR {item.get('program', 'Phase I')}",
                "postedDate": (item.get("open_date") or "")[:10],
                "dueDate":    (item.get("close_date") or "")[:10],
                "value":      int(item.get("award_ceiling") or 0),
                "description": item.get("program_descriptions") or "",
                "solNum":     str(item.get("solicitation_number") or ""),
                "url":        f"https://sbir.gov/sbirsearch/detail/{item.get('solicitation_id','')}",
            })
    except Exception as e:
        print(f"⚠  SBIR fetch error: {e}")
    print(f"  → {len(opps)} SBIR opportunities fetched")
    return opps


# ── Main ──────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"GovCon Pipeline — Data Fetch  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}")

    sam_opps  = fetch_sam()
    sbir_opps = fetch_sbir()
    all_opps  = sam_opps + sbir_opps

    # De-duplicate by id
    seen = set()
    unique = []
    for o in all_opps:
        if o["id"] not in seen:
            seen.add(o["id"])
            o["score"] = score(o)
            unique.append(o)

    # Sort by score descending
    unique.sort(key=lambda x: x["score"], reverse=True)

    # Load existing seed data if API returned nothing
    if not unique:
        print("⚠  No live data fetched — keeping existing data unchanged")
        return

    output = {
        "meta": {
            "lastUpdated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source":      "github-actions",
            "count":       len(unique),
        },
        "opportunities": unique,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓  Saved {len(unique)} opportunities → data/opportunities.json")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
