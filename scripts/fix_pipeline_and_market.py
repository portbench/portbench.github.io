"""
Post-process pipeline data: compute CEPS from stage scores, filter bad cases.
Also rebuild market_dataset.json to only include dates with news.
Outputs updated JS files.
"""
import json, os, re

PIPELINE_DIR = r"d:\GitHub\portbench.github.io\static\data\pipeline"
MARKET_JSON  = r"d:\GitHub\portbench.github.io\static\data\market_dataset.json"
MARKET_JS    = r"d:\GitHub\portbench.github.io\static\data\market_dataset.js"

LAMBDA = 0.1  # CEPS cascade penalty weight

def compute_ceps(scores):
    """Compute CEPS from a list of 5 stage scores using the paper formula:
    CEPS = clip(mean - lambda * sum(max(s[t] - s[t+1], 0)), 0, 1)
    """
    valid = [s for s in scores if s is not None]
    if len(valid) < 2:
        return 0.0
    mean_score = sum(valid) / len(valid)
    cascade = 0.0
    for i in range(len(valid) - 1):
        drop = valid[i] - valid[i + 1]
        if drop > 0:
            cascade += drop
    ceps = mean_score - LAMBDA * cascade
    return round(max(0.0, min(1.0, ceps)), 6)

def is_good_episode(ep):
    """Returns True if episode has complete, error-free stage data with real model output."""
    if not ep:
        return False
    stages = ep.get("stages", [])
    if len(stages) < 5:
        return False
    for s in stages:
        sid = s.get("stage_id", "")
        score = s.get("score")
        error = s.get("error", "")
        po = s.get("parsed_output", {}) or {}
        gt = s.get("ground_truth", {}) or {}

        # Must have a valid score
        if score is None:
            return False
        # Must have no error
        if error:
            return False
        # Must have ground truth
        if not gt:
            return False

        # LLM stages (S1-S3): must have real model output
        if sid == "S1":
            views = po.get("asset_views", {})
            if not views or len(views) < 3:
                return False
            gt_views = gt.get("asset_views", {})
            if not gt_views:
                return False
        elif sid == "S2":
            signals = po.get("signals", {})
            if not signals or len(signals) < 3:
                return False
            gt_signals = gt.get("signals", {})
            if not gt_signals:
                return False
        elif sid == "S3":
            weights = po.get("weights", {})
            if not weights or len(weights) < 3:
                return False
            gt_weights = gt.get("weights", {})
            if not gt_weights:
                return False
        # S4 and S5 are deterministic — accept even if fields are sparse

    return True

print("=" * 60)
print("FIXING PIPELINE DATA")
print("=" * 60)

# ── 1. Fix pipeline files ────────────────────────────────────────────────────
index_path = os.path.join(PIPELINE_DIR, "index.json")
with open(index_path, encoding="utf-8") as f:
    index = json.load(f)

total_before = 0
total_after = 0
fixed_ceps = 0

for model_id, model_info in sorted(index.items()):
    for scenario, scen_info in sorted(model_info["scenarios"].items()):
        in_file = os.path.join(PIPELINE_DIR, scen_info["file"])
        if not os.path.exists(in_file):
            continue

        with open(in_file, encoding="utf-8") as f:
            data = json.load(f)

        good_dates = []
        all_dates = sorted(data.keys())

        for date_str in all_dates:
            entry = data[date_str]
            ep = entry.get("episode")

            if not is_good_episode(ep):
                continue

            # Compute CEPS from stage scores
            scores = [s.get("score") for s in ep["stages"]]
            ep["ceps_score"] = compute_ceps(scores)
            if ep["ceps_score"] > 0:
                fixed_ceps += 1
            good_dates.append(date_str)

        # Filter to good dates only
        filtered = {d: data[d] for d in good_dates}

        removed = len(all_dates) - len(good_dates)
        total_before += len(all_dates)
        total_after += len(good_dates)

        # Write filtered JSON
        with open(in_file, "w", encoding="utf-8") as f:
            json.dump(filtered, f, separators=(",", ":"))

        # Write JS
        js_file = in_file.replace(".json", ".js")
        stem = os.path.splitext(scen_info["file"])[0].upper()
        var_name = "PORTBENCH_PIPELINE_" + stem
        with open(js_file, "w", encoding="utf-8") as f:
            f.write("window.%s=" % var_name)
            json.dump(filtered, f, separators=(",", ":"))
            f.write(";")

        # Update index
        scen_info["dates"] = good_dates

        if removed > 0 or len(good_dates) > 0:
            print("  %-22s / %-30s: %d dates (%d removed)" % (
                model_info["display"], scen_info["display"], len(good_dates), removed))

print("\nPipeline: %d -> %d total dates, %d CEPS recomputed (was 0.0)" % (
    total_before, total_after, fixed_ceps))

# Write updated index
with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index, f, indent=2)

# Write index JS
with open(index_path.replace(".json", ".js"), "w", encoding="utf-8") as f:
    f.write("window.PORTBENCH_PIPELINE_INDEX=")
    json.dump(index, f, separators=(",", ":"))
    f.write(";")

print("Updated pipeline/index.json and index.js")

# ── 2. Filter market dataset to news-rich dates ──────────────────────────────
print()
print("=" * 60)
print("FILTERING MARKET DATASET")
print("=" * 60)

with open(MARKET_JSON, encoding="utf-8") as f:
    mdata = json.load(f)

before = len(mdata["dates"])
# Keep only dates with >=3 news snippets for a richer display
mdata["dates"] = [d for d in mdata["dates"] if len(mdata["snapshots"][d].get("news", [])) >= 3]
mdata["snapshots"] = {d: mdata["snapshots"][d] for d in mdata["dates"]}
after = len(mdata["dates"])

print("Market dates: %d -> %d (removed %d with <3 news)" % (before, after, before - after))

# Remove NaN just in case
content = json.dumps(mdata, separators=(",", ":"), allow_nan=False)
content = re.sub(r'\bNaN\b', 'null', content)
with open(MARKET_JSON, "w", encoding="utf-8") as f:
    f.write(content)

with open(MARKET_JS, "w", encoding="utf-8") as f:
    f.write("window.PORTBENCH_MARKET=" + content + ";")

size_kb = os.path.getsize(MARKET_JS) / 1024
print("Regenerated market_dataset.js (%d KB)" % size_kb)

print()
print("DONE.")
