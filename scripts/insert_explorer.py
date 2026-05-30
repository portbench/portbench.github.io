"""
Insert Dataset Explorer section into index.html:
- HTML: after the Introduction </section> (before BENCHMARK BANNER)
- CSS: appended to static/css/index.css
The JS is embedded inline in the HTML.
"""
import re

HTML_PATH = r"d:\GitHub\portbench.github.io\index.html"
CSS_PATH  = r"d:\GitHub\portbench.github.io\static\css\index.css"

# ─── 1. Read files ────────────────────────────────────────────────────────────
with open(HTML_PATH, encoding="utf-8") as f:
    html = f.read()

# ─── 2. Build the Dataset Explorer HTML+JS block ─────────────────────────────
EXPLORER_HTML = r"""
<!-- ==================== DATASET EXPLORER BANNER ==================== -->
<section class="hero is-light is-small section-banner">
  <div class="hero-body has-text-centered">
    <h1 class="title is-1" id="explorer">Dataset Explorer</h1>
  </div>
</section>

<!-- ==================== DATASET EXPLORER ==================== -->
<section class="section">
  <div class="container">
    <div class="columns is-centered m-6">
      <div class="column is-full content">
        <p class="has-text-justified" style="margin-bottom:1.2rem;">
          PortBench contributes two datasets and one evaluation methodology.
          Use the tabs below to interactively explore each component.
        </p>
        <!-- Tab nav -->
        <div class="tabs is-centered is-boxed" id="explorer-tabs">
          <ul>
            <li class="is-active" data-tab="market"><a>&#x1F4CA; Market Base Dataset</a></li>
            <li data-tab="qa"><a>&#x2753; QA Dataset (T1&ndash;T7)</a></li>
            <li data-tab="pipeline"><a>&#x2699;&#xFE0F; Pipeline Evaluation</a></li>
          </ul>
        </div>

        <!-- ── Tab 1: Market Base Dataset ──────────────────────── -->
        <div id="tab-market" class="explorer-panel">
          <p class="has-text-justified" style="margin-bottom:1rem; font-size:0.9rem;">
            183 instruments across 6 asset classes, daily data 2015&ndash;2025.
            Each monthly snapshot includes macro indicators, per-asset price summaries, and cross-class correlations.
            Select a date to see the full snapshot.
          </p>
          <div class="explorer-controls">
            <label><b>Date:</b></label>
            <select id="market-date-picker" class="explorer-select"></select>
          </div>
          <div id="market-snapshot-display"><div class="explorer-loading">Loading market data&hellip;</div></div>
        </div>

        <!-- ── Tab 2: QA Dataset ────────────────────────────────── -->
        <div id="tab-qa" class="explorer-panel" style="display:none;">
          <p class="has-text-justified" style="margin-bottom:1rem; font-size:0.9rem;">
            6,269 correlation-aware QA pairs across 7 task templates (T1&ndash;T7),
            spanning complexity levels 1&ndash;4 and three market regimes.
            Select a template to browse sample question&ndash;answer pairs.
          </p>
          <div class="qa-template-buttons" style="margin-bottom:1rem;">
            <button class="qa-tmpl-btn is-active" data-tmpl="T1">T1 &middot; Return Prediction</button>
            <button class="qa-tmpl-btn" data-tmpl="T2">T2 &middot; Risk Assessment</button>
            <button class="qa-tmpl-btn" data-tmpl="T3">T3 &middot; Position Sizing</button>
            <button class="qa-tmpl-btn" data-tmpl="T4">T4 &middot; Min-Variance</button>
            <button class="qa-tmpl-btn" data-tmpl="T5">T5 &middot; Max-Sharpe</button>
            <button class="qa-tmpl-btn" data-tmpl="T6">T6 &middot; Rebalancing</button>
            <button class="qa-tmpl-btn" data-tmpl="T7">T7 &middot; Regime &amp; Allocation</button>
          </div>
          <div id="qa-carousel-display"><div class="explorer-loading">Loading QA data&hellip;</div></div>
        </div>

        <!-- ── Tab 3: Pipeline Evaluation ──────────────────────── -->
        <div id="tab-pipeline" class="explorer-panel" style="display:none;">
          <p class="has-text-justified" style="margin-bottom:1rem; font-size:0.9rem;">
            At each rebalance date a <code>MarketSnapshot</code> is constructed and passed to the LLM
            for five-stage evaluation (S1&ndash;S5).
            Select a model, market scenario, and date to see the model&rsquo;s input and stage-by-stage output vs. ground truth.
          </p>
          <div class="explorer-controls" style="flex-wrap:wrap;">
            <label><b>Model:</b></label>
            <select id="pipeline-model-picker" class="explorer-select"></select>
            <label><b>Scenario:</b></label>
            <select id="pipeline-scenario-picker" class="explorer-select"></select>
            <label><b>Date:</b></label>
            <select id="pipeline-date-picker" class="explorer-select"></select>
          </div>
          <div id="pipeline-display"><div class="explorer-loading">Select a model and scenario to load.</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<script>
(function() {
  /* ── helpers ── */
  function fmt(v, decimals) {
    if (v === null || v === undefined || v !== v) return "N/A";
    var n = parseFloat(v);
    if (isNaN(n)) return String(v);
    return n.toFixed(decimals !== undefined ? decimals : 2);
  }
  function pct(v, decimals) {
    if (v === null || v === undefined) return "N/A";
    return (parseFloat(v) * 100).toFixed(decimals !== undefined ? decimals : 1) + "%";
  }
  function esc(s) {
    return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }
  function regimeStyle(r) {
    if (!r) return "";
    if (r === "bull")    return "color:#15803d;font-weight:700";
    if (r === "bear")    return "color:#b91c1c;font-weight:700";
    if (r === "crisis")  return "color:#b91c1c;font-weight:900";
    return "color:#555";
  }
  function scoreColor(s) {
    if (s === null || s === undefined) return "#555";
    var n = parseFloat(s);
    if (n >= 0.70) return "#15803d";
    if (n >= 0.40) return "#b45309";
    return "#b91c1c";
  }
  function scoreClass(s) {
    if (s === null || s === undefined) return "";
    var n = parseFloat(s);
    if (n >= 0.70) return "high";
    if (n >= 0.40) return "med";
    return "low";
  }

  /* ── Tab switching ── */
  var initialized = {market: false, qa: false, pipeline: false};
  document.querySelectorAll("#explorer-tabs li").forEach(function(li) {
    li.addEventListener("click", function() {
      document.querySelectorAll("#explorer-tabs li").forEach(function(l) { l.classList.remove("is-active"); });
      document.querySelectorAll(".explorer-panel").forEach(function(p) { p.style.display = "none"; });
      li.classList.add("is-active");
      var tab = li.dataset.tab;
      document.getElementById("tab-" + tab).style.display = "";
      if (tab === "market" && !initialized.market)   initMarket();
      if (tab === "qa"     && !initialized.qa)       initQA();
      if (tab === "pipeline" && !initialized.pipeline) initPipeline();
    });
  });

  /* ═══════════════════════════════════════════════════
     TAB 1: MARKET BASE DATASET
  ═══════════════════════════════════════════════════ */
  var marketData = null;
  function initMarket() {
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
  }

  function renderMarketSnapshot(date) {
    var snap = marketData.snapshots[date];
    if (!snap) { document.getElementById("market-snapshot-display").innerHTML = "<p>No data for this date.</p>"; return; }
    var m = snap.macro;

    var html = '<div class="showcase-frame">';
    html += '<div class="showcase-frame-header">';
    html += '<span>MarketSnapshot <span class="meta">(monthly rebalance input)</span></span>';
    html += '<span class="meta">' + esc(date) + ' &nbsp;|&nbsp; Balanced Profile</span>';
    html += '</div><div class="showcase-frame-body">';

    /* Macro box */
    html += '<div class="showcase-inner si-peri">';
    html += '<div class="showcase-inner-header">Macroeconomic Indicators</div>';
    html += '<div class="showcase-inner-body"><div class="macro-grid">';
    var macroItems = [
      ["Fed Funds Rate", m.fed_funds_rate !== null ? fmt(m.fed_funds_rate, 2) + "%" : "N/A"],
      ["VIX", m.vix !== null ? fmt(m.vix, 2) : "N/A"],
      ["Unemployment", m.unemployment !== null ? fmt(m.unemployment, 1) + "%" : "N/A"],
      ["10Y-2Y Spread", m.t10y2y_spread !== null ? fmt(m.t10y2y_spread, 2) : "N/A"],
      ["10Y Breakeven", m.breakeven_10y !== null ? fmt(m.breakeven_10y, 2) + "%" : "N/A"],
      ["HY OAS", m.hy_oas !== null ? fmt(m.hy_oas, 2) : "N/A"],
      ["TED Spread", m.ted_spread !== null ? fmt(m.ted_spread, 2) : "N/A"],
      ["30Y Mortgage", m.mortgage_30y !== null ? fmt(m.mortgage_30y, 2) + "%" : "N/A"],
      ["SOFR", m.sofr !== null ? fmt(m.sofr, 2) + "%" : "N/A"],
      ["IG OAS", m.ig_oas !== null ? fmt(m.ig_oas, 2) : "N/A"],
    ];
    macroItems.forEach(function(kv) {
      html += '<span>' + esc(kv[0]) + ': <b>' + esc(kv[1]) + '</b></span>';
    });
    html += '</div></div></div>';

    /* Per-asset table by class */
    var assetClasses = ["Equities","Bonds","Commodities","Crypto","Real Estate","Cash"];
    var classColors = {"Equities":"si-blue","Bonds":"si-lav","Commodities":"si-cream","Crypto":"si-coral","Real Estate":"si-teal","Cash":"si-peri"};
    assetClasses.forEach(function(cls) {
      var assets = (snap.assets[cls] || []);
      if (!assets.length) return;
      html += '<div class="showcase-inner ' + classColors[cls] + '">';
      html += '<div class="showcase-inner-header">' + esc(cls) + '</div>';
      html += '<div class="showcase-inner-body">';
      html += '<div class="table-wrapper" style="max-height:none;">';
      html += '<table style="font-size:0.78rem;"><thead><tr>';
      html += '<th>Ticker</th><th>Close</th><th>20d Ret</th><th>60d Ret</th><th>Ann.Vol</th><th>Regime</th>';
      html += '</tr></thead><tbody>';
      assets.forEach(function(a) {
        var r20 = a.ret_20d !== null ? ((a.ret_20d >= 0 ? "+" : "") + pct(a.ret_20d, 1)) : "N/A";
        var r60 = a.ret_60d !== null ? ((a.ret_60d >= 0 ? "+" : "") + pct(a.ret_60d, 1)) : "N/A";
        var vol = a.vol !== null ? pct(a.vol, 1) : "N/A";
        var r20c = a.ret_20d !== null ? (a.ret_20d >= 0 ? "color:#15803d" : "color:#b91c1c") : "";
        var r60c = a.ret_60d !== null ? (a.ret_60d >= 0 ? "color:#15803d" : "color:#b91c1c") : "";
        html += '<tr>';
        html += '<td style="font-weight:700">' + esc(a.ticker) + '</td>';
        html += '<td>' + fmt(a.close, 2) + '</td>';
        html += '<td style="' + r20c + '">' + esc(r20) + '</td>';
        html += '<td style="' + r60c + '">' + esc(r60) + '</td>';
        html += '<td>' + esc(vol) + '</td>';
        html += '<td style="' + regimeStyle(a.regime) + '">' + esc(a.regime || "") + '</td>';
        html += '</tr>';
      });
      html += '</tbody></table></div></div></div>';
    });

    /* Correlation box */
    var classes = Object.keys(snap.correlation || {});
    if (classes.length) {
      html += '<div class="showcase-inner si-cream">';
      html += '<div class="showcase-inner-header">Two-Layer Correlation Interface <span style="font-weight:400;font-size:0.72rem;">41-day trailing window</span></div>';
      html += '<div class="showcase-inner-body">';
      html += '<table class="corr-table"><thead><tr><th>Class</th><th>Intra-&rho;</th>';
      classes.forEach(function(c2) { if (c2 !== classes[0]) html += '<th>vs.' + esc(c2.substring(0,4)) + '</th>'; });
      html += '</tr></thead><tbody>';
      classes.forEach(function(c1) {
        html += '<tr><td style="text-align:left">' + esc(c1) + '</td>';
        html += '<td>' + (snap.correlation[c1][c1] !== null ? fmt(snap.correlation[c1][c1], 2) : "N/A") + '</td>';
        classes.forEach(function(c2) {
          if (c2 === c1) return;
          var v = snap.correlation[c1][c2];
          var style = "";
          if (v !== null && Math.abs(parseFloat(v)) > 0.5) style = 'style="font-weight:700;color:#b91c1c"';
          html += '<td ' + style + '>' + (v !== null ? fmt(v, 2) : "N/A") + '</td>';
        });
        html += '</tr>';
      });
      html += '</tbody></table></div></div>';
    }

    html += '</div></div>';  /* close frame-body + frame */
    document.getElementById("market-snapshot-display").innerHTML = html;
  }

  /* ═══════════════════════════════════════════════════
     TAB 2: QA DATASET
  ═══════════════════════════════════════════════════ */
  var qaData = null;
  var qaCurTmpl = "T1";
  var qaCurIdx = 0;
  var QA_COLORS = {
    T1: "si-qa-blue", T2: "si-qa-blue", T3: "si-qa-blue",
    T4: "si-qa-teal",
    T5: "si-qa-orange", T6: "si-qa-orange",
    T7: "si-qa-red"
  };
  var QA_DESC = {
    T1: "Return Prediction · Complexity 1",
    T2: "Risk Assessment (VaR) · Complexity 1",
    T3: "Position Sizing · Complexity 1",
    T4: "Pairwise Min-Variance Allocation · Complexity 2",
    T5: "Max-Sharpe Optimization · Complexity 3",
    T6: "Rebalancing Decision · Complexity 3",
    T7: "Regime Detection &amp; Allocation · Complexity 4"
  };

  function initQA() {
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
  }

  function renderQA() {
    var samples = qaData[qaCurTmpl] || [];
    if (!samples.length) { document.getElementById("qa-carousel-display").innerHTML = "<p>No samples.</p>"; return; }
    var n = samples.length;
    var s = samples[qaCurIdx];
    var color = QA_COLORS[qaCurTmpl] || "si-qa-blue";
    var desc = QA_DESC[qaCurTmpl] || qaCurTmpl;
    var regimeBadge = '<span style="background:#e5e7eb;color:#374151;border-radius:3px;padding:1px 6px;font-size:0.72rem;margin-left:8px;">' + esc(s.market_regime) + '</span>';
    var splitBadge  = '<span style="background:#e5e7eb;color:#374151;border-radius:3px;padding:1px 6px;font-size:0.72rem;margin-left:4px;">' + esc(s.split) + '</span>';
    var assetsBadge = (s.assets||[]).map(function(a){ return '<code style="font-size:0.75rem;background:#f3f4f6;padding:1px 4px;border-radius:2px;">' + esc(a) + '</code>'; }).join(" ");

    var html = '<div class="showcase-inner ' + color + '" style="text-align:left;">';
    html += '<div class="showcase-inner-header">' + qaCurTmpl + ': ' + desc + regimeBadge + splitBadge;
    html += '<span style="font-weight:400;font-size:0.72rem;">' + s.decision_date + '</span></div>';
    html += '<div class="showcase-inner-body">';
    if (s.assets && s.assets.length) {
      html += '<p style="margin-bottom:4px;font-size:0.78rem;"><b>Assets:</b> ' + assetsBadge + '</p>';
    }
    if (s.context_summary) {
      html += '<p style="margin-bottom:6px;font-size:0.78rem;color:#555;font-style:italic;">' + esc(s.context_summary) + '</p>';
    }
    html += '<p style="margin-bottom:6px;font-size:0.82rem;"><b>Question:</b> ' + esc(s.question) + '</p>';
    html += '<p style="margin-bottom:4px;font-size:0.82rem;"><b>Answer:</b> <code>' + esc(s.answer) + '</code></p>';
    if (s.explanation) {
      html += '<p class="showcase-note" style="margin-top:6px;">' + esc(s.explanation) + '</p>';
    }
    html += '</div></div>';

    /* carousel controls */
    html += '<div class="carousel-controls" style="margin-top:0.6rem;">';
    html += '<button class="carousel-btn" id="qa-prev">&#8249;</button>';
    html += '<span class="carousel-counter">' + (qaCurIdx+1) + ' / ' + n + '</span>';
    html += '<button class="carousel-btn" id="qa-next">&#8250;</button>';
    html += '</div>';

    document.getElementById("qa-carousel-display").innerHTML = html;
    document.getElementById("qa-prev").addEventListener("click", function(){
      qaCurIdx = (qaCurIdx - 1 + n) % n; renderQA();
    });
    document.getElementById("qa-next").addEventListener("click", function(){
      qaCurIdx = (qaCurIdx + 1) % n; renderQA();
    });
  }

  /* ═══════════════════════════════════════════════════
     TAB 3: PIPELINE EVALUATION
  ═══════════════════════════════════════════════════ */
  var pipelineIndex = null;
  var pipelineCache = {};
  var pipelineCurrentKey = null;

  function initPipeline() {
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
  }

  function onPipelineModelChange() {
    var modelId = document.getElementById("pipeline-model-picker").value;
    var scenSel = document.getElementById("pipeline-scenario-picker");
    scenSel.innerHTML = "";
    var scenarios = (pipelineIndex[modelId] || {}).scenarios || {};
    Object.keys(scenarios).forEach(function(s) {
      var opt = document.createElement("option");
      opt.value = s;
      opt.textContent = scenarios[s].display || s;
      scenSel.appendChild(opt);
    });
    onPipelineScenarioChange();
  }

  function onPipelineScenarioChange() {
    var modelId = document.getElementById("pipeline-model-picker").value;
    var scenario = document.getElementById("pipeline-scenario-picker").value;
    var dateSel = document.getElementById("pipeline-date-picker");
    dateSel.innerHTML = "";
    var scenInfo = ((pipelineIndex[modelId] || {}).scenarios || {})[scenario];
    if (!scenInfo) return;
    scenInfo.dates.forEach(function(d) {
      var opt = document.createElement("option"); opt.value = d; opt.textContent = d; dateSel.appendChild(opt);
    });
    loadPipelineData(modelId, scenario);
  }

  function onPipelineDateChange() {
    var date = document.getElementById("pipeline-date-picker").value;
    renderPipeline(date);
  }

  function loadPipelineData(modelId, scenario) {
    var modelIdSafe = modelId.replace(/-/g,"_").replace(/\./g,"_");
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
  }

  function renderPipeline(date) {
    var modelId = document.getElementById("pipeline-model-picker").value;
    var scenario = document.getElementById("pipeline-scenario-picker").value;
    var modelIdSafe = modelId.replace(/-/g,"_").replace(/\./g,"_");
    var key = modelIdSafe + "_" + scenario;
    var fileData = pipelineCache[key];
    if (!fileData) return;
    pipelineCurrentKey = key;

    var entry = fileData[date];
    if (!entry) { document.getElementById("pipeline-display").innerHTML = "<p>No data for date " + esc(date) + ".</p>"; return; }

    var snap = entry.snapshot || {};
    var ep   = entry.episode;
    var displayName = (pipelineIndex[modelId] || {}).display || modelId;
    var scenInfo = ((pipelineIndex[modelId] || {}).scenarios || {})[scenario];
    var scenDisplay = scenInfo ? scenInfo.display : scenario;
    var macro = snap.macro_data || {};

    var html = "";

    /* ── Snapshot section ── */
    html += '<div class="showcase-frame">';
    html += '<div class="showcase-frame-header">';
    html += '<span>MarketSnapshot <span class="meta">(model input)</span></span>';
    html += '<span class="meta">' + esc(date) + ' &nbsp;|&nbsp; Balanced Profile &nbsp;|&nbsp; ' + esc(scenDisplay) + '</span>';
    html += '</div><div class="showcase-frame-body">';

    /* Macro */
    html += '<div class="showcase-inner si-peri">';
    html += '<div class="showcase-inner-header">Macroeconomic Indicators &nbsp;';
    html += '<span style="font-weight:400;font-size:0.72rem;">Regime: <b style="' + regimeStyle(snap.market_regime) + '">' + esc(snap.market_regime || "N/A") + '</b> &nbsp;|&nbsp; NAV: <b>$' + fmt(snap.portfolio_value, 0) + '</b></span></div>';
    html += '<div class="showcase-inner-body"><div class="macro-grid">';
    var macroRows = [
      ["Fed Funds", macro.fed_funds_rate, "%", 2],
      ["VIX", macro.vix, "", 2],
      ["Unemployment", macro.unemployment, "%", 1],
      ["10Y-2Y Spread", macro.t10y2y_spread, "", 2],
      ["10Y Breakeven", macro.breakeven_10y, "%", 2],
      ["HY OAS", macro.hy_oas, "", 2],
      ["TED Spread", macro.ted_spread, "", 2],
      ["Mortgage 30Y", macro.mortgage_30y, "%", 2],
    ];
    macroRows.forEach(function(row) {
      var v = row[1] !== null && row[1] !== undefined ? fmt(row[1], row[3]) + row[2] : "N/A";
      html += '<span>' + esc(row[0]) + ': <b>' + esc(v) + '</b></span>';
    });
    html += '</div></div></div>';

    /* Trailing returns */
    var tr = snap.trailing_returns || {};
    var trKeys = Object.keys(tr);
    if (trKeys.length) {
      html += '<div class="showcase-inner si-blue">';
      html += '<div class="showcase-inner-header">60-Day Trailing Returns (representative assets)</div>';
      html += '<div class="showcase-inner-body">';
      html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
      trKeys.forEach(function(t) {
        var v = tr[t];
        var c = v >= 0 ? "#15803d" : "#b91c1c";
        var sign = v >= 0 ? "+" : "";
        html += '<span style="font-size:0.78rem;background:#f3f4f6;padding:2px 7px;border-radius:3px;">';
        html += '<b>' + esc(t) + '</b> <span style="color:' + c + '">' + sign + pct(v,1) + '</span></span>';
      });
      html += '</div></div></div>';
    }

    html += '</div></div>'; /* close snap frame */

    /* ── Pipeline traces ── */
    if (ep && ep.stages && ep.stages.length) {
      var CEPS = ep.ceps_score !== null ? fmt(ep.ceps_score, 3) : "N/A";
      html += '<div class="showcase-frame" style="margin-top:1rem;">';
      html += '<div class="showcase-frame-header">';
      html += '<span>' + esc(displayName) + ' &mdash; Pipeline Trace</span>';
      html += '<span class="meta">CEPS = <b>' + CEPS + '</b> &nbsp;|&nbsp; ' + esc(date) + ' &nbsp;|&nbsp; ' + esc(scenDisplay) + '</span>';
      html += '</div><div class="showcase-frame-body">';

      var STAGE_COLORS = ["si-blue","si-peri","si-cream","si-lav","si-coral"];
      var STAGE_NAMES  = ["S1: Market Interpretation","S2: Signal Generation","S3: Weight Optimization","S4: Execution Simulation (deterministic)","S5: Risk Monitoring (deterministic)"];

      ep.stages.forEach(function(stage, i) {
        var color = STAGE_COLORS[i] || "si-blue";
        var name = STAGE_NAMES[i] || stage.stage_id;
        var score = stage.score;
        var sc = scoreClass(score);
        html += '<div class="showcase-inner ' + color + '">';
        html += '<div class="showcase-inner-header">' + esc(name);
        if (score !== null) html += ' <span class="score-badge ' + sc + '">Score = ' + fmt(score, 3) + '</span>';
        html += '</div><div class="showcase-inner-body">';

        var po = stage.parsed_output || {};
        var gt = stage.ground_truth || {};

        html += '<div class="showcase-two-col">';
        html += '<div><div class="col-label">Model Output</div>' + renderStageOutput(stage.stage_id, po) + '</div>';
        html += '<div><div class="col-label">Ground Truth</div>' + renderStageOutput(stage.stage_id, gt) + '</div>';
        html += '</div>';

        html += '</div></div>';
      });

      /* CEPS summary */
      if (ep.stages.length >= 2) {
        var scores = ep.stages.map(function(s){ return s.score; }).filter(function(s){ return s !== null; });
        var drops = [];
        for (var i = 0; i < scores.length - 1; i++) {
          var d = scores[i] - scores[i+1];
          if (d > 0) drops.push(d);
        }
        var totalDrop = drops.reduce(function(a,b){ return a+b; }, 0);
        html += '<div class="showcase-summary"><b>Scores:</b> ' +
          ep.stages.map(function(s,i){ return "S"+(i+1)+"=" + (s.score !== null ? fmt(s.score,3) : "N/A"); }).join(", ") +
          ' &nbsp;|&nbsp; <b>Cascade drops: ' + fmt(totalDrop,3) + '</b> &nbsp;|&nbsp; <b>CEPS: ' + CEPS + '</b></div>';
      }

      html += '</div></div>'; /* close trace frame */
    } else {
      html += '<div class="highlight-box" style="margin-top:1rem;">No pipeline trace data available for this date.</div>';
    }

    document.getElementById("pipeline-display").innerHTML = html;
  }

  function renderStageOutput(stageId, obj) {
    if (!obj) return "<span style='color:#888'>N/A</span>";
    var lines = [];
    if (stageId === "S1") {
      if (obj.detected_regime) lines.push("<b>Regime:</b> " + esc(obj.detected_regime));
      if (obj.macro_summary) lines.push("<b>Macro:</b> " + esc(obj.macro_summary.substring(0,120)));
      var views = obj.asset_views || {};
      var vkeys = Object.keys(views).slice(0,8);
      if (vkeys.length) lines.push("<b>Views:</b> " + vkeys.map(function(k){ var v=views[k]; return esc(k)+":" + (v>=0?"+":"") + fmt(v,2); }).join(", "));
    } else if (stageId === "S2") {
      var sigs = obj.signals || {};
      var sk = Object.keys(sigs).slice(0,10);
      if (sk.length) lines.push("<b>Signals:</b> " + sk.map(function(k){ return esc(k)+":"+esc(sigs[k]); }).join(", "));
    } else if (stageId === "S3") {
      var wts = obj.weights || {};
      var wk = Object.keys(wts).slice(0,8);
      if (wk.length) lines.push("<b>Weights:</b> " + wk.map(function(k){ return esc(k)+":"+pct(wts[k],1); }).join(", "));
      if (obj.sharpe_estimate !== undefined && obj.sharpe_estimate !== null) lines.push("<b>Sharpe est.:</b> " + fmt(obj.sharpe_estimate,3));
    } else if (stageId === "S4") {
      var orders = obj.orders || [];
      if (orders.length) lines.push("<b>Orders:</b> " + orders.slice(0,4).map(function(o){ return esc(o.asset)+":"+esc(o.direction); }).join(", ") + (orders.length>4?" +more":""));
      if (obj.turnover !== undefined && obj.turnover !== null) lines.push("<b>Turnover:</b> " + pct(obj.turnover,1));
    } else if (stageId === "S5") {
      if (obj.portfolio_var !== undefined) lines.push("<b>VaR:</b> " + pct(obj.portfolio_var,2));
      if (obj.portfolio_drawdown !== undefined) lines.push("<b>MaxDD:</b> " + pct(obj.portfolio_drawdown,2));
      if (obj.rebalance_needed !== undefined) lines.push("<b>Rebalance:</b> " + (obj.rebalance_needed ? "Yes" : "No"));
    }
    return lines.join("<br>") || '<span style="color:#888">—</span>';
  }

  /* ── Auto-init market tab (it's the default) ── */
  initMarket();

})();
</script>

"""

# ─── 3. CSS to add ──────────────────────────────────────────────────────────
CSS_ADD = """
/* ── Dataset Explorer ── */
.explorer-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.explorer-select {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
  background: #fff;
  cursor: pointer;
}
.qa-template-buttons { display: flex; flex-wrap: wrap; gap: 6px; }
.qa-tmpl-btn {
  padding: 5px 12px;
  border: 1px solid #3273dc;
  border-radius: 4px;
  cursor: pointer;
  background: #fff;
  color: #3273dc;
  font-size: 0.82rem;
  transition: background 0.15s, color 0.15s;
}
.qa-tmpl-btn.is-active, .qa-tmpl-btn:hover {
  background: #3273dc;
  color: #fff;
}
.explorer-loading {
  text-align: center;
  padding: 2rem;
  color: #888;
  font-style: italic;
}
"""

# ─── 4. Insert HTML into index.html ──────────────────────────────────────────
# Find the comment "<!-- ==================== BENCHMARK BANNER"
BANNER_MARKER = "<!-- ==================== BENCHMARK BANNER ==================== -->"
if BANNER_MARKER not in html:
    print("ERROR: Could not find BENCHMARK BANNER marker in index.html")
    exit(1)

html_new = html.replace(BANNER_MARKER, EXPLORER_HTML + "\n" + BANNER_MARKER)

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_new)
print("Updated index.html")

# ─── 5. Append CSS ───────────────────────────────────────────────────────────
with open(CSS_PATH, "a", encoding="utf-8") as f:
    f.write(CSS_ADD)
print("Updated index.css")

print("Done.")
