"""
Extract pipeline evaluation data from EXPERIMENTS/monthly/ for the website Dataset Explorer.
For each model × scenario combination, produces one JSON file with all dates.
Also produces pipeline/index.json listing available models, scenarios, dates.

Outputs:
  static/data/pipeline/index.json
  static/data/pipeline/<model>_<scenario>.json  (one per model-scenario)
"""
import json, os, glob

EXPERIMENTS_ROOT = r"d:\GitHub\portbench\EXPERIMENTS\monthly"
OUT_DIR = r"d:\GitHub\portbench.github.io\static\data\pipeline"

# Model display name mapping
MODEL_DISPLAY = {
    "deepseek-v4-flash": "DeepSeek-V4-Flash",
    "deepseek-v4-pro":   "DeepSeek-V4-Pro",
    "doubao-seed-2-0-lite-260215": "Doubao-Seed-2.0-Lite",
    "doubao-seed-2-0-pro-260215":  "Doubao-Seed-2.0-Pro",
    "glm-5.1":           "GLM-5.1",
    "kimi-k2.6":         "Kimi-K2.6",
    "qwen3.6-35b-a3b":   "Qwen3.6-35B-A3B",
    "qwen3.6-plus":      "Qwen3.6-Plus",
    "qwen3.7-max":       "Qwen3.7-Max",
    "hy3-preview":       "Hunyuan3-Preview",
}

SCENARIO_DISPLAY = {
    "normal":                     "Normal (2024)",
    "stress_2015_china_shock":    "2015 China Shock",
    "stress_2020_covid_flash_crash": "2020 COVID Crash",
    "stress_2022_crypto_collapse": "2022 Crypto Collapse",
}

def safe_float(x):
    try:
        v = float(x)
        return round(v, 4) if v == v else None  # NaN check
    except:
        return None

def clean_stage_output(parsed):
    """Remove raw_llm_output key which is redundant/large."""
    if not isinstance(parsed, dict):
        return parsed
    out = {k: v for k, v in parsed.items() if k != "raw_llm_output"}
    # For S1: limit asset_views to top 20 by abs value
    if "asset_views" in out and isinstance(out["asset_views"], dict):
        views = out["asset_views"]
        if len(views) > 20:
            top = sorted(views.items(), key=lambda x: abs(x[1] if x[1] is not None else 0), reverse=True)[:20]
            out["asset_views"] = dict(top)
    # For S3/weights: limit to top 20 non-zero
    if "weights" in out and isinstance(out["weights"], dict):
        weights = out["weights"]
        nonzero = {k: v for k, v in weights.items() if v and v > 0.001}
        if len(nonzero) > 20:
            top = sorted(nonzero.items(), key=lambda x: x[1], reverse=True)[:20]
            out["weights"] = dict(top)
        else:
            out["weights"] = nonzero
    # For S2/signals: limit to 20
    if "signals" in out and isinstance(out["signals"], dict):
        signals = out["signals"]
        if len(signals) > 20:
            out["signals"] = dict(list(signals.items())[:20])
    return out

def clean_gt(gt):
    """Same cleaning for ground truth."""
    return clean_stage_output(gt)

os.makedirs(OUT_DIR, exist_ok=True)

index = {}  # model_id -> {scenario -> sorted list of dates}

# Walk EXPERIMENTS/monthly/
for provider_dir in glob.glob(os.path.join(EXPERIMENTS_ROOT, "*")):
    provider = os.path.basename(provider_dir)
    if provider in ("baseline", "sigma_ablation", "_env_meta.json", "_last_run_config.yaml",
                    "analysis_report.md", "comparison_figures"):
        continue
    if not os.path.isdir(provider_dir):
        continue

    for model_dir in glob.glob(os.path.join(provider_dir, "*")):
        model_id = os.path.basename(model_dir)
        if not os.path.isdir(model_dir):
            continue

        # Find run timestamp directory
        run_dirs = [d for d in glob.glob(os.path.join(model_dir, "*")) if os.path.isdir(d)]
        if not run_dirs:
            continue
        run_dir = sorted(run_dirs)[-1]  # latest run

        balanced_dir = os.path.join(run_dir, "balanced")
        if not os.path.isdir(balanced_dir):
            continue

        display_name = MODEL_DISPLAY.get(model_id, model_id)

        for scenario_dir in glob.glob(os.path.join(balanced_dir, "*")):
            scenario = os.path.basename(scenario_dir)
            if not os.path.isdir(scenario_dir):
                continue

            snapshots_dir = os.path.join(scenario_dir, "snapshots")
            episodes_dir_glob = os.path.join(scenario_dir, "pipeline_logs", "*", "episodes")

            if not os.path.isdir(snapshots_dir):
                continue

            # Find episodes dir
            episodes_dirs = glob.glob(episodes_dir_glob)
            episodes_dir = episodes_dirs[0] if episodes_dirs else None

            # Read all snapshot files
            snap_files = sorted(glob.glob(os.path.join(snapshots_dir, "*.json")))
            if not snap_files:
                continue

            # Build date-indexed data
            date_data = {}
            for sf in snap_files:
                date_str = os.path.splitext(os.path.basename(sf))[0]
                try:
                    with open(sf, encoding="utf-8") as f:
                        snap = json.load(f)
                except:
                    continue

                # Extract comprehensive snapshot
                macro = snap.get("macro_data", {})
                trailing = snap.get("trailing_returns", {})

                # Keep all non-zero trailing returns (limit to top 60 by abs value)
                trailing_clean = {}
                for k, v in trailing.items():
                    if v is not None:
                        try:
                            fv = round(float(v), 4)
                            if abs(fv) > 0.0001:
                                trailing_clean[k] = fv
                        except Exception:
                            pass
                if len(trailing_clean) > 60:
                    top_t = sorted(trailing_clean.items(), key=lambda x: abs(x[1]), reverse=True)[:60]
                    trailing_clean = dict(top_t)

                # Current weights: keep non-zero, limit to top 50
                weights_raw = snap.get("current_weights", {})
                weights_clean = {}
                for k, v in weights_raw.items():
                    if v is not None:
                        try:
                            fv = round(float(v), 4)
                            if fv > 0.0001:
                                weights_clean[k] = fv
                        except Exception:
                            pass
                if len(weights_clean) > 50:
                    top_w = sorted(weights_clean.items(), key=lambda x: x[1], reverse=True)[:50]
                    weights_clean = dict(top_w)

                # News text preview (truncated)
                news_raw = snap.get("news_text_preview", "")
                news_clean = str(news_raw)[:300] if news_raw else ""

                date_data[date_str] = {
                    "snapshot": {
                        "macro_data": {k: safe_float(v) for k, v in macro.items()},
                        "market_regime": snap.get("market_regime", ""),
                        "portfolio_value": safe_float(snap.get("portfolio_value")),
                        "trailing_returns": trailing_clean,
                        "current_weights": weights_clean,
                        "assets": snap.get("assets", []),
                        "news_text_preview": news_clean,
                    },
                    "episode": None,
                }

            # Read episode files
            if episodes_dir and os.path.isdir(episodes_dir):
                ep_files = sorted(glob.glob(os.path.join(episodes_dir, "*.json")))
                for ef in ep_files:
                    basename = os.path.basename(ef)
                    # Filename: 2015-08-07_0001.json
                    date_str = "_".join(basename.split("_")[:-1]) if "_" in basename else basename.replace(".json","")
                    if date_str not in date_data:
                        continue
                    try:
                        with open(ef, encoding="utf-8") as f:
                            ep = json.load(f)
                    except:
                        continue

                    stages_out = []
                    for stage in ep.get("stages", []):
                        stages_out.append({
                            "stage_id": stage.get("stage_id"),
                            "score": safe_float(stage.get("score")),
                            "parsed_output": clean_stage_output(stage.get("parsed_output", {})),
                            "ground_truth": clean_gt(stage.get("ground_truth", {})),
                        })
                    date_data[date_str]["episode"] = {
                        "ceps_score": safe_float(ep.get("ceps_score")),
                        "stages": stages_out,
                    }

            if not date_data:
                continue

            # Output file name
            safe_model = model_id.replace("-", "_").replace(".", "_")
            out_key = f"{safe_model}_{scenario}"
            out_file = os.path.join(OUT_DIR, f"{out_key}.json")

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(date_data, f, separators=(",", ":"))

            size_kb = os.path.getsize(out_file) / 1024
            dates = sorted(date_data.keys())
            print(f"  {display_name} / {scenario}: {len(dates)} dates, {size_kb:.0f} KB → {out_key}.json")

            # Add to index
            if model_id not in index:
                index[model_id] = {"display": display_name, "scenarios": {}}
            index[model_id]["scenarios"][scenario] = {
                "display": SCENARIO_DISPLAY.get(scenario, scenario),
                "dates": dates,
                "file": f"{out_key}.json",
            }

# Write index
index_path = os.path.join(OUT_DIR, "index.json")
with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index, f, indent=2)

print(f"\nSaved index to {index_path}")
print(f"Models: {sorted(index.keys())}")
total_files = sum(len(v['scenarios']) for v in index.values())
print(f"Total model-scenario files: {total_files}")
