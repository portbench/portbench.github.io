"""
Update index.html to:
1. Add <script> tags for core data JS files in <head>
2. Replace fetch() calls with window globals
3. Use dynamic <script> injection for pipeline detail files
4. Update intro text to describe contribution logic
"""

HTML_PATH = r"d:\GitHub\portbench.github.io\index.html"

with open(HTML_PATH, encoding="utf-8") as f:
    html = f.read()

# ── 1. Add <script> tags before </head> ─────────────────────────────────────
DATA_SCRIPTS = """\
  <script src="./static/data/market_dataset.js"></script>
  <script src="./static/data/qa_samples.js"></script>
  <script src="./static/data/pipeline/index.js"></script>
</head>"""

html = html.replace("</head>", DATA_SCRIPTS, 1)

# ── 2. Fix intro text ────────────────────────────────────────────────────────
OLD_INTRO = """        <p class="has-text-justified" style="margin-bottom:1.2rem;">
          PortBench contributes two datasets and one evaluation methodology.
          Use the tabs below to interactively explore each component.
        </p>"""

NEW_INTRO = """        <p class="has-text-justified" style="margin-bottom:1.2rem;">
          PortBench is built upon the <b>Market Base Dataset</b>, a 10-year collection of 183 instruments
          across six heterogeneous asset classes (2015&ndash;2025).
          On top of this foundation, we construct a <b>dual-layer evaluation framework</b>:
          a <em>static</em> <b>QA Dataset</b> of 6,269 correlation-aware question&ndash;answer pairs
          generated automatically from the historical data,
          and a <em>dynamic</em> <b>Five-Stage Pipeline Evaluation</b> that reconstructs
          a live <code>MarketSnapshot</code> at each rebalance date and evaluates the LLM
          end-to-end across S1&ndash;S5.
          Explore each layer below.
        </p>"""

html = html.replace(OLD_INTRO, NEW_INTRO, 1)

# ── 3. Replace initMarket() fetch with global ────────────────────────────────
OLD_INIT_MARKET = """  function initMarket() {
    initialized.market = true;
    fetch("./static/data/market_dataset.json")
      .then(function(r){ return r.json(); })
      .then(function(data){
        marketData = data;
        var sel = document.getElementById("market-date-picker");
        data.dates.forEach(function(d) {
          var opt = document.createElement("option"); opt.value = d; opt.textContent = d; sel.appendChild(opt);
        });
        // default to a middle-ish date with good data
        var midIdx = Math.floor(data.dates.length * 0.75);
        sel.selectedIndex = midIdx;
        sel.addEventListener("change", function() { renderMarketSnapshot(sel.value); });
        renderMarketSnapshot(sel.value);
      })
      .catch(function(e){ document.getElementById("market-snapshot-display").innerHTML = "<p style='color:red'>Failed to load market data.</p>"; });
  }"""

NEW_INIT_MARKET = """  function initMarket() {
    initialized.market = true;
    var data = window.PORTBENCH_MARKET;
    if (!data) { document.getElementById("market-snapshot-display").innerHTML = "<p style='color:red'>Market data not loaded.</p>"; return; }
    marketData = data;
    var sel = document.getElementById("market-date-picker");
    data.dates.forEach(function(d) {
      var opt = document.createElement("option"); opt.value = d; opt.textContent = d; sel.appendChild(opt);
    });
    var midIdx = Math.floor(data.dates.length * 0.75);
    sel.selectedIndex = midIdx;
    sel.addEventListener("change", function() { renderMarketSnapshot(sel.value); });
    renderMarketSnapshot(sel.value);
  }"""

html = html.replace(OLD_INIT_MARKET, NEW_INIT_MARKET, 1)

# ── 4. Replace initQA() fetch with global ────────────────────────────────────
OLD_INIT_QA = """  function initQA() {
    initialized.qa = true;
    fetch("./static/data/qa_samples.json")
      .then(function(r){ return r.json(); })
      .then(function(data){
        qaData = data;
        document.querySelectorAll(".qa-tmpl-btn").forEach(function(btn) {
          btn.addEventListener("click", function() {
            document.querySelectorAll(".qa-tmpl-btn").forEach(function(b){ b.classList.remove("is-active"); });
            btn.classList.add("is-active");
            qaCurTmpl = btn.dataset.tmpl;
            qaCurIdx = 0;
            renderQA();
          });
        });
        renderQA();
      })
      .catch(function(){ document.getElementById("qa-carousel-display").innerHTML = "<p style='color:red'>Failed to load QA data.</p>"; });
  }"""

NEW_INIT_QA = """  function initQA() {
    initialized.qa = true;
    var data = window.PORTBENCH_QA;
    if (!data) { document.getElementById("qa-carousel-display").innerHTML = "<p style='color:red'>QA data not loaded.</p>"; return; }
    qaData = data;
    document.querySelectorAll(".qa-tmpl-btn").forEach(function(btn) {
      btn.addEventListener("click", function() {
        document.querySelectorAll(".qa-tmpl-btn").forEach(function(b){ b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        qaCurTmpl = btn.dataset.tmpl;
        qaCurIdx = 0;
        renderQA();
      });
    });
    renderQA();
  }"""

html = html.replace(OLD_INIT_QA, NEW_INIT_QA, 1)

# ── 5. Replace initPipeline() fetch with global ──────────────────────────────
OLD_INIT_PIPELINE = """  function initPipeline() {
    initialized.pipeline = true;
    fetch("./static/data/pipeline/index.json")
      .then(function(r){ return r.json(); })
      .then(function(data){
        pipelineIndex = data;
        var modelSel = document.getElementById("pipeline-model-picker");
        Object.keys(data).sort().forEach(function(modelId) {
          var opt = document.createElement("option");
          opt.value = modelId;
          opt.textContent = data[modelId].display;
          modelSel.appendChild(opt);
        });
        modelSel.addEventListener("change", onPipelineModelChange);
        document.getElementById("pipeline-scenario-picker").addEventListener("change", onPipelineScenarioChange);
        document.getElementById("pipeline-date-picker").addEventListener("change", onPipelineDateChange);
        onPipelineModelChange();
      })
      .catch(function(){ document.getElementById("pipeline-display").innerHTML = "<p style='color:red'>Failed to load pipeline index.</p>"; });
  }"""

NEW_INIT_PIPELINE = """  function initPipeline() {
    initialized.pipeline = true;
    var data = window.PORTBENCH_PIPELINE_INDEX;
    if (!data) { document.getElementById("pipeline-display").innerHTML = "<p style='color:red'>Pipeline index not loaded.</p>"; return; }
    pipelineIndex = data;
    var modelSel = document.getElementById("pipeline-model-picker");
    Object.keys(data).sort().forEach(function(modelId) {
      var opt = document.createElement("option");
      opt.value = modelId;
      opt.textContent = data[modelId].display;
      modelSel.appendChild(opt);
    });
    modelSel.addEventListener("change", onPipelineModelChange);
    document.getElementById("pipeline-scenario-picker").addEventListener("change", onPipelineScenarioChange);
    document.getElementById("pipeline-date-picker").addEventListener("change", onPipelineDateChange);
    onPipelineModelChange();
  }"""

html = html.replace(OLD_INIT_PIPELINE, NEW_INIT_PIPELINE, 1)

# ── 6. Replace loadPipelineData() fetch with dynamic <script> loading ────────
OLD_LOAD_PIPELINE = """  function loadPipelineData(modelId, scenario) {
    var modelIdSafe = modelId.replace(/-/g,"_").replace(/\\./g,"_");
    var key = modelIdSafe + "_" + scenario;
    if (pipelineCache[key]) { renderPipeline(document.getElementById("pipeline-date-picker").value); return; }
    document.getElementById("pipeline-display").innerHTML = '<div class="explorer-loading">Loading pipeline data&hellip;</div>';
    fetch("./static/data/pipeline/" + key + ".json")
      .then(function(r){ return r.json(); })
      .then(function(data){
        pipelineCache[key] = data;
        pipelineCurrentKey = key;
        renderPipeline(document.getElementById("pipeline-date-picker").value);
      })
      .catch(function(e){ document.getElementById("pipeline-display").innerHTML = "<p style='color:red'>Failed to load pipeline data for " + key + ".</p>"; console.error(e); });
  }"""

NEW_LOAD_PIPELINE = """  function loadPipelineData(modelId, scenario) {
    var modelIdSafe = modelId.replace(/-/g,"_").replace(/\\./g,"_");
    var key = modelIdSafe + "_" + scenario;
    if (pipelineCache[key]) { renderPipeline(document.getElementById("pipeline-date-picker").value); return; }
    document.getElementById("pipeline-display").innerHTML = '<div class="explorer-loading">Loading pipeline data&hellip;</div>';
    var varName = "PORTBENCH_PIPELINE_" + key.toUpperCase();
    // Try window global first (script already loaded)
    if (window[varName]) {
      pipelineCache[key] = window[varName];
      pipelineCurrentKey = key;
      renderPipeline(document.getElementById("pipeline-date-picker").value);
      return;
    }
    // Load via dynamic <script> tag (works with file://)
    var script = document.createElement("script");
    script.src = "./static/data/pipeline/" + key + ".js";
    script.onload = function() {
      if (window[varName]) {
        pipelineCache[key] = window[varName];
        pipelineCurrentKey = key;
        renderPipeline(document.getElementById("pipeline-date-picker").value);
      } else {
        document.getElementById("pipeline-display").innerHTML = "<p style='color:red'>Data variable not found: " + varName + "</p>";
      }
    };
    script.onerror = function() {
      document.getElementById("pipeline-display").innerHTML = "<p style='color:red'>Failed to load: " + key + ".js</p>";
    };
    document.head.appendChild(script);
  }"""

html = html.replace(OLD_LOAD_PIPELINE, NEW_LOAD_PIPELINE, 1)

# ── 7. Write back ────────────────────────────────────────────────────────────
with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html)

# Verify replacements happened
checks = [
    ("DATA_SCRIPTS", "market_dataset.js" in html),
    ("INTRO_TEXT", "dual-layer evaluation framework" in html),
    ("initMarket uses global", "PORTBENCH_MARKET" in html),
    ("initQA uses global", "PORTBENCH_QA" in html),
    ("initPipeline uses global", "PORTBENCH_PIPELINE_INDEX" in html),
    ("loadPipeline uses script tag", "PORTBENCH_PIPELINE_" in html and "createElement" in html),
]
print("Verification:")
for name, result in checks:
    print(f"  {name}: {'OK' if result else 'FAILED'}")

print(f"\nDone. HTML size: {len(html)} bytes")
