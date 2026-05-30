"""
Convert JSON data files to JS data files (window.PORTBENCH_* globals).
This makes them loadable via <script src=...> which works with file:// protocol.
"""
import json, os, re

DATA_DIR = r"d:\GitHub\portbench.github.io\static\data"

def nan_to_null(content):
    return re.sub(r'\bNaN\b', 'null', content)

def json_to_js(json_path, js_path, var_name):
    with open(json_path, encoding="utf-8") as f:
        content = f.read()
    content = nan_to_null(content)
    js_content = f"window.{var_name}={content};\n"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    size_kb = os.path.getsize(js_path) / 1024
    print(f"  {os.path.basename(js_path)} ({size_kb:.0f} KB)")

print("Converting data files to JS...")
json_to_js(
    os.path.join(DATA_DIR, "market_dataset.json"),
    os.path.join(DATA_DIR, "market_dataset.js"),
    "PORTBENCH_MARKET"
)
json_to_js(
    os.path.join(DATA_DIR, "qa_samples.json"),
    os.path.join(DATA_DIR, "qa_samples.js"),
    "PORTBENCH_QA"
)
json_to_js(
    os.path.join(DATA_DIR, "pipeline", "index.json"),
    os.path.join(DATA_DIR, "pipeline", "index.js"),
    "PORTBENCH_PIPELINE_INDEX"
)

# Also convert individual pipeline files (for dynamic script loading)
print("Converting pipeline detail files...")
pipeline_dir = os.path.join(DATA_DIR, "pipeline")
count = 0
for fn in os.listdir(pipeline_dir):
    if fn.endswith(".json") and fn != "index.json":
        stem = fn[:-5]
        json_to_js(
            os.path.join(pipeline_dir, fn),
            os.path.join(pipeline_dir, stem + ".js"),
            f"PORTBENCH_PIPELINE_{stem.upper()}"
        )
        count += 1
print(f"Converted {count} pipeline files.")
