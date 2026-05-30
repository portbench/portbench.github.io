"""
Extract QA sample pairs from qa_dataset/all_pairs.jsonl for the website Dataset Explorer.
Picks 4-5 representative samples per template (T1-T7) spanning different regimes.
Outputs: static/data/qa_samples.json
"""
import json, os, random

JSONL_PATH = r"d:\GitHub\portbench\datasets\qa_dataset\all_pairs.jsonl"
OUT_PATH   = r"d:\GitHub\portbench.github.io\static\data\qa_samples.json"

SAMPLES_PER_TMPL = 4
MAX_QUESTION_LEN = 800
MAX_EXPLANATION_LEN = 400

random.seed(42)

def truncate(s, max_len):
    if not s:
        return ""
    s = str(s)
    if len(s) <= max_len:
        return s
    return s[:max_len].rstrip() + "…"

print("Reading QA pairs...")
by_template = {}
with open(JSONL_PATH, encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        t = item.get("template", "")
        if t not in by_template:
            by_template[t] = {"bull": [], "bear": [], "sideways": []}
        regime = item.get("market_regime", "sideways")
        if regime not in by_template[t]:
            regime = "sideways"
        by_template[t][regime].append(item)

print(f"Templates found: {sorted(by_template.keys())}")

result = {}
for tmpl in ["T1","T2","T3","T4","T5","T6","T7"]:
    if tmpl not in by_template:
        print(f"  WARNING: {tmpl} not found")
        continue

    # Pick samples from different regimes - aim for 1 bull, 1 bear, 2 sideways
    pool = by_template[tmpl]
    candidates = []
    regime_targets = [("sideways", 2), ("bull", 1), ("bear", 1)]
    for regime, target in regime_targets:
        if pool[regime]:
            picked = random.sample(pool[regime], min(target, len(pool[regime])))
            candidates.extend(picked)

    # Deduplicate and trim
    seen_ids = set()
    unique = []
    for item in candidates:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique.append(item)

    # If not enough, fill from any regime
    all_items = pool["bull"] + pool["bear"] + pool["sideways"]
    random.shuffle(all_items)
    for item in all_items:
        if len(unique) >= SAMPLES_PER_TMPL:
            break
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique.append(item)

    samples = unique[:SAMPLES_PER_TMPL]

    result[tmpl] = []
    for item in samples:
        meta = item.get("metadata", {})
        assets = item.get("assets", [])
        sample = {
            "id": item["id"],
            "template": item["template"],
            "complexity": item.get("complexity", 1),
            "split": item.get("split", "train"),
            "market_regime": item.get("market_regime", "sideways"),
            "assets": assets[:6],  # max 6 tickers to show
            "decision_date": item.get("decision_date", ""),
            "context_summary": truncate(item.get("context_summary", ""), 300),
            "question": truncate(item.get("question", ""), MAX_QUESTION_LEN),
            "answer": truncate(item.get("answer", ""), 200),
            "explanation": truncate(item.get("explanation", ""), MAX_EXPLANATION_LEN),
        }
        result[tmpl].append(sample)

    print(f"  {tmpl}: {len(result[tmpl])} samples (regimes: {[s['market_regime'] for s in result[tmpl]]})")

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

size_kb = os.path.getsize(OUT_PATH) / 1024
print(f"\nSaved to {OUT_PATH} ({size_kb:.0f} KB)")
