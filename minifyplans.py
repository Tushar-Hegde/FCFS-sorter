"""
migrate_plans.py
Converts plans.json -> plans_optimized.json

Optimized format per combo:
{
  "id": 1,
  "order": ["CSE1001", "CSE1002L", ...],   # was "picking_order"
  "secs": {
    "CSE1001": {"p": "Dr Smith", "s": "A1+TA1"},  # professor + slots
    "CSE1002": null                                  # null = blank
  }
}

Removed entirely: name, type, tt_code, minute_blocks (all rederivable from CSV).
"is_blank" replaced by null value in secs map.
"""

import json, os, csv, sys

# ── helpers ────────────────────────────────────────────────────────────────────

def load_courses_from_csv(path="CourseList.csv"):
    """Build lookup: (code, professor, slots) -> tt_code"""
    lookup = {}
    if not os.path.exists(path):
        return lookup
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or len(row) < 6 or "course" in row[1].lower():
                continue
            name, code, slots, tt_code, prof, ctype = [x.strip() for x in row[:6]]
            lookup[(code, prof, slots)] = tt_code
    return lookup

def slim_section(sec):
    """Convert a fat section dict to slim form."""
    if sec.get("is_blank"):
        return None   # null in JSON
    return {"p": sec["professor"], "s": sec["slots"]}

def fatten_section(code, slim, courses_dict):
    """Reconstruct a full section dict from slim form + courses_dict."""
    if slim is None:
        # blank
        sections = courses_dict.get(code, [])
        name = sections[0]["name"] if sections else code
        return {
            "code": code, "name": name, "slots": "—",
            "tt_code": "—", "professor": "—", "type": "—",
            "minute_blocks": [], "is_blank": True
        }
    # find the matching section in courses_dict
    candidates = courses_dict.get(code, [])
    match = next((s for s in candidates
                  if s["professor"] == slim["p"] and s["slots"] == slim["s"]), None)
    if match:
        return dict(match, is_blank=False)
    # fallback: reconstruct minimal
    name = candidates[0]["name"] if candidates else code
    return {
        "code": code, "name": name, "slots": slim["s"],
        "tt_code": "—", "professor": slim["p"], "type": "—",
        "minute_blocks": [], "is_blank": False
    }

# ── conversion ─────────────────────────────────────────────────────────────────

def to_optimized(fat_combo):
    secs = {}
    for sec in fat_combo["sections"]:
        secs[sec["code"]] = slim_section(sec)
    return {
        "id":    fat_combo["id"],
        "order": fat_combo["picking_order"],
        "secs":  secs
    }

def to_fat(slim_combo, courses_dict):
    order = slim_combo["order"]
    sections = []
    for code in order:
        slim = slim_combo["secs"].get(code)
        sections.append(fatten_section(code, slim, courses_dict))
    return {
        "id":            slim_combo["id"],
        "picking_order": order,
        "sections":      sections
    }

# ── main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    src  = sys.argv[1] if len(sys.argv) > 1 else "plans.json"
    dst  = sys.argv[2] if len(sys.argv) > 2 else "plans_optimized.json"

    if not os.path.exists(src):
        print(f"ERROR: {src} not found."); sys.exit(1)

    with open(src, encoding="utf-8") as f:
        fat = json.load(f)

    slim_combos = [to_optimized(c) for c in fat.get("combos", [])]
    out = {"combos": slim_combos}

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    # size comparison
    fat_size  = os.path.getsize(src)
    slim_size = os.path.getsize(dst)
    print(f"Converted {len(slim_combos)} combos.")
    print(f"  {src}: {fat_size:,} bytes")
    print(f"  {dst}: {slim_size:,} bytes  ({100*slim_size//fat_size}% of original)")