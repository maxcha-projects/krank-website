#!/usr/bin/env python3
"""
update_from_csv.py — Update index.html from krank-index CSV data
─────────────────────────────────────────────────────────────────
Reads the enriched CSV files from the krank-index pipeline and
patches the celebrity JS objects in index.html.

Sources:
    ../krank-index/data/celebrities.csv   → igFollowers, ytFollowers
    ../krank-index/outputs/media_scores.csv → media, mediaVolume, mediaQuality, mediaRecency

Usage:
    python3 update_from_csv.py           # update + git commit & push
    python3 update_from_csv.py --dry-run # preview changes, no write
"""

import re, csv, subprocess, argparse
from datetime import date
from pathlib import Path

HTML_FILE        = "index.html"
CELEBRITIES_CSV  = "../krank-index/data/celebrities.csv"
MEDIA_SCORES_CSV = "../krank-index/outputs/media_scores.csv"


# ── Load data ────────────────────────────────────────────────────

def load_celebrities():
    """Returns {NAME_UPPER: {igFollowers, ytFollowers, followers}}"""
    data = {}
    with open(CELEBRITIES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["Name"].strip().upper()
            ig   = row.get("Instagram Followers", "").strip()
            yt   = row.get("YouTube Subscribers", "").strip()

            entry = {}
            ig_m, yt_m = None, None

            if ig:
                try:
                    ig_m = round(int(ig) / 1_000_000, 3)
                    entry["igFollowers"] = ig_m
                except ValueError:
                    pass

            if yt:
                try:
                    yt_m = round(int(yt) / 1_000_000, 3)
                    entry["ytFollowers"] = yt_m
                except ValueError:
                    pass

            # Combined followers for the legacy `followers` field
            total = (ig_m or 0) + (yt_m or 0)
            if total > 0:
                entry["followers"] = round(total, 3)

            if entry:
                data[name] = entry
    return data


def load_media_scores():
    """Returns {NAME_UPPER: {media, mediaVolume, mediaQuality, mediaRecency}}"""
    data = {}
    with open(MEDIA_SCORES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["Name"].strip().upper()
            entry = {}
            for src_key, dst_key in [
                ("MediaScore",   "media"),
                ("MediaVolume",  "mediaVolume"),
                ("MediaQuality", "mediaQuality"),
                ("MediaRecency", "mediaRecency"),
            ]:
                val = row.get(src_key, "").strip()
                if val:
                    try:
                        entry[dst_key] = round(float(val), 1)
                    except ValueError:
                        pass
            if entry:
                data[name] = entry
    return data


# ── Regex patterns for in-line JS field replacement ──────────────

PATTERNS = {
    "followers":      (r'followers:[\d.]+',      lambda v: f"followers:{v}"),
    "igFollowers":    (r'igFollowers:[\d.]+',    lambda v: f"igFollowers:{v}"),
    "ytFollowers":    (r'ytFollowers:[\d.]+',    lambda v: f"ytFollowers:{v}"),
    "media":          (r'\bmedia:[\d.]+',          lambda v: f"media:{v}"),
    "mediaVolume":    (r'mediaVolume:[\d.]+',    lambda v: f"mediaVolume:{v}"),
    "mediaQuality":   (r'mediaQuality:[\d.]+',   lambda v: f"mediaQuality:{v}"),
    "mediaRecency":   (r'mediaRecency:[\d.]+',   lambda v: f"mediaRecency:{v}"),
}

# Fields to inject if not already present on the line
INJECTABLE = {"igFollowers", "ytFollowers", "mediaVolume", "mediaQuality", "mediaRecency"}

# Known name mismatches between HTML and data sources
ALIASES = {
    "KIM DO-YEONG": "KIM DO-YOUNG",   # HTML uses DO-YEONG, data uses DO-YOUNG
}


def fmt(v):
    """Format number: one decimal if needed, else integer."""
    if isinstance(v, float) and v != int(v):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(int(v)) if isinstance(v, float) else str(v)


# ── Patch HTML ───────────────────────────────────────────────────

def update_html(celeb_data: dict, media_data: dict, dry_run: bool = False):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_names = []
    unchanged_names = []

    for i, line in enumerate(lines):
        m = re.search(r"name:'([^']+)'", line)
        if not m:
            continue

        html_name = m.group(1).strip().upper()
        lookup    = ALIASES.get(html_name, html_name)

        # Merge all data for this celebrity
        entry = {}
        entry.update(celeb_data.get(lookup, {}))
        entry.update(media_data.get(lookup, {}))

        if not entry:
            unchanged_names.append(m.group(1))
            continue

        original = line
        for field, value in entry.items():
            pat_info = PATTERNS.get(field)
            if not pat_info:
                continue
            pattern, replacer = pat_info
            val_str = fmt(value)

            if re.search(pattern, line):
                line = re.sub(pattern, replacer(val_str), line)
            elif field in INJECTABLE:
                # Append before closing brace on this line
                line = re.sub(r'(})', rf",{field}:{val_str}\1", line, count=1)

        if line != original:
            lines[i] = line
            updated_names.append(m.group(1))

    print(f"Updated : {len(updated_names)} celebrities")
    print(f"No data : {len(unchanged_names)} celebrities")

    if dry_run:
        print("\n[DRY RUN] Sample changes (first 5 updated):")
        idx = 0
        for i, line in enumerate(lines):
            m = re.search(r"name:'([^']+)'", line)
            if m and m.group(1) in updated_names[:5]:
                orig = open(HTML_FILE).readlines()[i]
                if orig != line:
                    print(f"  {m.group(1)}")
                    print(f"    WAS: {orig.strip()[:120]}")
                    print(f"    NOW: {line.strip()[:120]}")
                idx += 1
                if idx >= 5:
                    break
        return

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"\n✓ Saved {HTML_FILE}")
    return updated_names


def git_commit_push(updated_count: int):
    today = date.today().strftime("%Y-%m-%d")
    msg   = f"Weekly update – {today} ({updated_count} celebrities updated)"
    subprocess.run(["git", "add", HTML_FILE], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if result.returncode == 0:
        print("No changes detected — nothing to commit.")
        return
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)
    print(f'\n✓ Pushed: "{msg}"')


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    args = parser.parse_args()

    print(f"Loading {CELEBRITIES_CSV} …")
    celeb_data = load_celebrities()
    print(f"  → {len(celeb_data)} rows with follower data")

    print(f"Loading {MEDIA_SCORES_CSV} …")
    media_data = load_media_scores()
    print(f"  → {len(media_data)} rows with media scores\n")

    updated = update_html(celeb_data, media_data, dry_run=args.dry_run)

    if not args.dry_run and updated:
        git_commit_push(len(updated))

    print("\nDone.")


if __name__ == "__main__":
    main()
