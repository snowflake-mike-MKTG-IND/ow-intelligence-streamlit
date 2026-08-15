"""Opening Weekend Intelligence — Streamlit replica of the SPCS app's front page (Business view).

Static snapshot: reads bundled data/films.json (no Snowflake connection required),
so it runs on Streamlit Community Cloud (the free tier) with no secrets.
"""
import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Opening Weekend Intelligence", page_icon="🎬", layout="wide")

DATA = json.loads((Path(__file__).parent / "data" / "films.json").read_text())
try:
    DRIVERS = json.loads((Path(__file__).parent / "data" / "drivers.json").read_text())
except Exception:
    DRIVERS = {}

TIER_LABEL = {
    "SMALL": "Small  ·  under $15M",
    "MID": "Mid  ·  $15–50M",
    "LARGE+": "Large+  ·  $50M and up",
}

# Closeness verdict (V31): how close the prediction was, by % error — tier-agnostic.
# label, symbol, color, outcome-tone
VERDICT_META = {
    "HIT": ("Hit", "✓", "#2e9e6b", "hit"),
    "NEAR_HIT": ("Near hit", "≈", "#29b5e8", "near"),
    "CLOSE": ("Close estimate", "·", "#f59e0b", "close"),
    "MISS": ("Miss", "✗", "#e5484d", "miss"),
}
VERDICT_ORDER = ["HIT", "NEAR_HIT", "CLOSE", "MISS"]

# --- "What's driving this call" (ported from the SPCS drivers route) ---
# V31/V30 are demand-forward: only demand/intent/sentiment/context signals enter standalone.
DRIVER_META = {
    "YT_COMMENTS": ("Trailer buzz", "LARGE+"),
    "ROLLING_7D": ("Search interest (7d)", "LARGE+"),
    "NET_INTENT_PCT": ("Purchase intent", "LARGE+"),
    "THEATRICAL_INTENT_PCT": ("Theater excitement", "LARGE+"),
    "ROLLING_14D": ("Search interest (14d)", "LARGE+"),
    "PASS_INTENT_PCT": ("Audience apathy", "SMALL"),
    "SENTIMENT": ("Trailer sentiment", "LARGE+"),
    "GENRE_ACTION_FRANCHISE": ("Action/franchise", "LARGE+"),
    "GENRE_HORROR": ("Horror genre", "MID"),
    "IS_PEAK_SEASON": ("Peak season release", "LARGE+"),
}
DRIVER_IMPORTANCE = {"YT_COMMENTS": 5.0, "ROLLING_7D": 4.6, "NET_INTENT_PCT": 4.2,
    "THEATRICAL_INTENT_PCT": 3.6, "ROLLING_14D": 3.2, "PASS_INTENT_PCT": 2.9,
    "SENTIMENT": 2.4, "GENRE_ACTION_FRANCHISE": 1.8, "GENRE_HORROR": 1.6, "IS_PEAK_SEASON": 1.4}
DRIVER_BINARY = {"GENRE_HORROR", "GENRE_ACTION_FRANCHISE", "IS_PEAK_SEASON"}
PUSH_COLOR = {"LARGE+": "#2e9e6b", "SMALL": "#e5484d", "MID": "#f59e0b"}

def compute_drivers(mid):
    row = DRIVERS.get(str(mid))
    if not row:
        return []
    out = []
    for feat, (label, pushes) in DRIVER_META.items():
        pct = row.get(f"PRANK_{feat}")
        pct = 0.5 if pct is None else pct
        val = row.get(feat) or 0
        if feat in DRIVER_BINARY and val == 0:
            continue
        dev = abs(pct - 0.5)
        score = DRIVER_IMPORTANCE.get(feat, 1) * dev * 2
        if score <= 0.3:
            continue
        pr = round(pct * 100)
        if pr == 0:
            direction = "lowest in the dataset"
        elif pr == 100:
            direction = "highest in the dataset"
        elif pr >= 90:
            direction = f"higher than {pr}% of films"
        elif pr >= 75:
            direction = f"above average (top {100 - pr}%)"
        elif pr <= 10:
            direction = f"lower than {100 - pr}% of films"
        elif pr <= 25:
            direction = f"below average (bottom {pr}%)"
        else:
            direction = f"near average ({pr}th percentile)"
        is_high = pct > 0.5
        push = pushes
        if pushes == "SMALL" and not is_high:
            push = "LARGE+"
        elif pushes == "LARGE+" and not is_high:
            push = "SMALL"
        elif pushes == "MID":
            push = "MID" if is_high else "SMALL"
        out.append({"label": label, "pct": pct, "direction": direction, "push": push, "score": score})
    out.sort(key=lambda x: -x["score"])
    return out[:5]

# ---------- helpers ----------
def money(m):
    if m is None:
        return "—"
    return f"${m:.0f}M" if m >= 100 else f"${m:.1f}M"

def tier_class(tier):
    return {"LARGE+": "tier-large", "MID": "tier-mid"}.get(tier, "tier-small")

def breakout_label(pct):
    if pct < 15:
        return ("Unlikely to break out", "calm")
    if pct < 30:
        return ("Slim breakout chance — roughly 1 in 5", "watch")
    if pct < 50:
        return ("Real breakout chance — roughly 1 in 3", "flag")
    return ("Likely to break out — better than even", "hot")

def pct_off(d):
    """Percent error of the prediction vs actual, or None."""
    actual = d.get("ACTUAL_OW_M")
    err = d.get("ABS_ERROR_M")
    if actual is None or err is None or actual <= 0:
        return None
    return err / actual

def accuracy_bucket(d):
    """How close was the prediction? Tier-agnostic, purely % error.
    <=10% Hit · 11-20% Near hit · 20-25% Close estimate · >25% Miss."""
    r = pct_off(d)
    if r is None:
        return None
    if r <= 0.10:
        return "HIT"
    if r <= 0.20:
        return "NEAR_HIT"
    if r <= 0.25:
        return "CLOSE"
    return "MISS"

def detail_for(mid):
    matches = [d for d in DATA["details"] if d["MOVIE_ID"] == mid]
    if not matches:
        return None
    return next((d for d in matches if d["PREDICTION_TYPE"] == "UPCOMING"), matches[0])

def density_path(peak_pct, p_small, p_large):
    peak = max(5.0, min(195.0, peak_pct / 100 * 200))
    h = 38.0
    ls = 30 + p_small / 100 * 50
    rs = 30 + p_large / 100 * 50
    sx = max(0.0, peak - ls * 2)
    ex = min(200.0, peak + rs * 2)
    return (f"M {sx} 40 Q {peak-ls*0.8} {40-h*0.4}, {peak-ls*0.3} {40-h*0.8} "
            f"Q {peak} {40-h}, {peak} {40-h} Q {peak} {40-h}, {peak+rs*0.3} {40-h*0.8} "
            f"Q {peak+rs*0.8} {40-h*0.4}, {ex} 40 Z")

# ---------- styles ----------
st.markdown("""
<style>
:root{--bg:#f6f8fb;--surface:#fff;--ink:#0f1c2e;--ink-soft:#51607a;--ink-faint:#8190a8;
--line:#e4e9f1;--line-soft:#eef2f7;--blue:#29b5e8;--navy:#11567f;--amber:#f59e0b;--red:#e5484d;--green:#2e9e6b;}
.block-container{padding-top:3rem;max-width:1280px;}
header[data-testid="stHeader"]{background:transparent;}
#MainMenu,footer{visibility:hidden;}
.topbar{display:flex;align-items:center;justify-content:space-between;background:var(--surface);
border:1px solid var(--line);border-radius:14px;padding:14px 22px;margin-bottom:18px;
box-shadow:0 1px 2px rgba(16,35,60,.04),0 8px 24px rgba(16,35,60,.06);}
.brand{display:flex;align-items:center;gap:12px;}
.brand-icon{font-size:22px;}
.brand-title{font-weight:700;font-size:1.05rem;letter-spacing:-.01em;color:var(--ink);}
.brand-sub{font-size:.76rem;color:var(--ink-faint);}
.viewtoggle{display:flex;gap:4px;background:var(--line-soft);padding:4px;border-radius:10px;}
.tb{font-size:.82rem;font-weight:600;color:var(--ink-soft);padding:7px 14px;border-radius:7px;}
.tb.active{background:var(--surface);color:var(--navy);box-shadow:0 1px 3px rgba(16,35,60,.12);}
.tb.disabled{opacity:.45;}
/* film list buttons */
div[data-testid="stButton"]>button{width:100%;text-align:left;justify-content:flex-start;
border:none;border-bottom:1px solid var(--line-soft);border-radius:0;background:transparent;
color:var(--ink);font-size:.9rem;font-weight:500;padding:9px 6px;}
div[data-testid="stButton"]>button:hover{background:var(--line-soft);color:var(--navy);}
div[data-testid="stButton"]>button:focus{box-shadow:none;}
/* card */
.pred-card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:26px 28px;
box-shadow:0 1px 2px rgba(16,35,60,.04),0 8px 24px rgba(16,35,60,.06);}
.pred-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:6px;}
.film-title{font-size:1.7rem;font-weight:750;letter-spacing:-.02em;color:var(--ink);line-height:1.15;}
.film-sub{font-size:.82rem;color:var(--ink-faint);margin-top:4px;}
.breakout-flag{display:flex;align-items:center;gap:5px;font-size:.74rem;font-weight:700;color:#b3791a;
background:#fff4e1;border:1px solid #ffe3b0;padding:5px 10px;border-radius:8px;white-space:nowrap;}
.mini-tier{font-size:.68rem;font-weight:700;padding:2px 7px;border-radius:5px;white-space:nowrap;}
.tier-small{background:#eaf6fb;color:#1b7aa3;}
.tier-mid{background:#fff4e1;color:#b3791a;}
.tier-large{background:#e9f7f0;color:#1f7a52;}
.outcome{display:flex;gap:26px;flex-wrap:wrap;background:var(--line-soft);border-radius:12px;
padding:14px 18px;margin:16px 0;border-left:4px solid var(--green);}
.outcome.hit{border-left-color:var(--green);}
.outcome.near{border-left-color:var(--blue);}
.outcome.close{border-left-color:var(--amber);}
.outcome.miss{border-left-color:var(--red);}
.outcome-item{display:flex;flex-direction:column;gap:3px;}
.outcome-label{font-size:.68rem;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-faint);}
.outcome-val{font-size:1.02rem;font-weight:700;color:var(--ink);}
.pred-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:26px;margin-top:20px;}
@media(max-width:820px){.pred-grid{grid-template-columns:1fr;}}
.metric-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-faint);}
.metric-big{font-size:2.9rem;font-weight:800;letter-spacing:-.03em;color:var(--navy);line-height:1;margin:6px 0 10px;}
.tier-pill{display:inline-block;font-size:.8rem;font-weight:700;padding:5px 12px;border-radius:8px;}
.range-block{margin-top:22px;}
.range-row{display:flex;justify-content:space-between;font-size:.74rem;color:var(--ink-soft);font-weight:600;margin-bottom:4px;}
.range-track-wrap{position:relative;height:44px;}
.density-svg{position:absolute;inset:0;width:100%;height:40px;}
.range-track{position:absolute;bottom:0;left:0;right:0;height:6px;background:var(--line);border-radius:3px;}
.range-marker{position:absolute;top:-3px;width:3px;height:12px;border-radius:2px;transform:translateX(-50%);}
.range-marker.point{background:var(--navy);width:4px;height:14px;top:-4px;}
.range-marker.base{background:var(--ink-faint);}
.range-caption{font-size:.68rem;color:var(--ink-faint);margin-top:8px;}
.breakout-box{display:flex;align-items:center;gap:14px;border-radius:12px;padding:14px 16px;margin-bottom:16px;}
.tone-calm{background:#eef7f2;}.tone-watch{background:#fff7e9;}.tone-flag{background:#fff1e6;}.tone-hot{background:#fdecec;}
.breakout-pct{font-size:1.9rem;font-weight:800;color:var(--navy);line-height:1;}
.breakout-title{font-size:.82rem;font-weight:700;color:var(--ink);}
.breakout-text{font-size:.74rem;color:var(--ink-soft);}
.prob-title{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-faint);margin-bottom:8px;}
.prob-row{display:flex;align-items:center;gap:10px;margin-bottom:7px;}
.prob-name{font-size:.78rem;font-weight:600;width:48px;color:var(--ink-soft);}
.prob-bar{flex:1;height:8px;background:var(--line);border-radius:4px;overflow:hidden;}
.prob-fill{height:100%;border-radius:4px;}
.prob-fill.tier-small{background:var(--blue);}.prob-fill.tier-mid{background:var(--amber);}.prob-fill.tier-large{background:var(--green);}
.prob-val{font-size:.76rem;font-weight:700;width:36px;text-align:right;color:var(--ink);}
.summary{display:flex;gap:10px;background:#fff9ec;border:1px solid #ffe8bf;border-radius:12px;
padding:14px 16px;margin-top:20px;font-size:.86rem;color:#5c4a20;line-height:1.5;}
.drivers-section{margin-top:22px;border-top:1px solid var(--line-soft);padding-top:18px;}
.drivers-title{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-faint);margin-bottom:14px;}
.driver-row{display:grid;grid-template-columns:1.5fr 1.1fr auto;align-items:center;gap:16px;margin-bottom:13px;}
.driver-label{font-weight:600;font-size:.9rem;color:var(--ink);display:block;line-height:1.2;}
.driver-detail{font-size:.74rem;color:var(--ink-faint);}
.driver-bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;}
.driver-fill{height:100%;border-radius:4px;}
.driver-push{font-size:.76rem;font-weight:700;white-space:nowrap;}
.context{background:linear-gradient(180deg,#f0f8fc,#ffffff);border:1px solid var(--line);border-radius:14px;
padding:16px 20px;margin-bottom:18px;box-shadow:0 1px 2px rgba(16,35,60,.04);}
.context-title{font-weight:700;font-size:.92rem;color:var(--navy);margin-bottom:6px;}
.context p{font-size:.83rem;color:var(--ink-soft);line-height:1.55;margin:4px 0 0;}
.context b{color:var(--ink);font-weight:650;}
.context .src{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;}
.context .pill{font-size:.7rem;font-weight:600;color:#1b7aa3;background:#eaf6fb;border:1px solid #d3ecf5;border-radius:999px;padding:3px 10px;}
.badge{font-weight:800;margin-left:6px;}
.badge-bullseye{color:var(--green);}.badge-hit{color:var(--blue);}.badge-correct-tier{color:var(--amber);}.badge-miss{color:var(--red);}
</style>
""", unsafe_allow_html=True)

# ---------- top bar ----------
st.markdown("""
<div class="topbar">
  <div class="brand">
    <span class="brand-icon">🎬</span>
    <div>
      <div class="brand-title">Opening Weekend Intelligence</div>
      <div class="brand-sub">Live pre-release predictions (2026) · V31 pedigree-gated distributional model on Snowflake</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="context">
  <div class="context-title">🧩 How these predictions are made</div>
  <p>Every opening-weekend call is built entirely from <b>open, public data</b> — no proprietary studio numbers. Signals are refreshed in the weeks before release and scored against public box-office results.</p>
  <div class="src">
    <span class="pill">Google Trends search interest</span>
    <span class="pill">Wikipedia pageviews</span>
    <span class="pill">YouTube trailer sentiment &amp; intent</span>
    <span class="pill">TMDB metadata</span>
    <span class="pill">Public box-office actuals</span>
  </div>
  <p>The entire pipeline — data refresh, feature engineering, validation gates, model scoring (V31 pedigree-gated distributional model), and this app — is built and operated <b>agentically by Cortex Code</b> on Snowflake.</p>
</div>
""", unsafe_allow_html=True)

# ---------- state ----------
if "segment" not in st.session_state:
    st.session_state.segment = "upcoming"
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

left, right = st.columns([1, 2.5], gap="large")

with left:
    seg_label = st.selectbox("Predictions", ["Upcoming predictions", "Released predictions"],
                             label_visibility="collapsed")
    segment = "upcoming" if seg_label.startswith("Upcoming") else "past"
    if segment != st.session_state.segment:
        st.session_state.segment = segment
        st.session_state.selected_id = None

    films = list(DATA[segment])
    # Live predictions only — drop the OOF holdout backtest (2022-2026 historical).
    films = [f for f in films if f.get("PREDICTION_TYPE") != "OOF_BACKTEST"]
    # attach accuracy buckets for past
    if segment == "past":
        for f in films:
            f["_bucket"] = accuracy_bucket(detail_for(f["MOVIE_ID"]) or {})
        counts = {b: sum(1 for f in films if f.get("_bucket") == b) for b in VERDICT_ORDER}
        acc = st.radio(
            "Accuracy",
            ["ALL"] + VERDICT_ORDER,
            format_func=lambda b: "All" if b == "ALL" else f"{VERDICT_META[b][0]} ({counts[b]})",
            horizontal=True, label_visibility="collapsed")
        if acc != "ALL":
            films = [f for f in films if f.get("_bucket") == acc]

    q = st.text_input("Search", placeholder="Search films…", label_visibility="collapsed")
    if q.strip():
        needle = q.strip().lower()
        films = [f for f in films if needle in f["MOVIE_TITLE"].lower()]

    if st.session_state.selected_id not in [f["MOVIE_ID"] for f in films]:
        st.session_state.selected_id = films[0]["MOVIE_ID"] if films else None

    st.caption(f"{len(films)} film{'s' if len(films) != 1 else ''}")
    for f in films:
        flag = "▲ " if (f.get("PRED_TIER", "").upper() != "LARGE+" and f.get("P_LARGE_PCT", 0) >= 30) else ""
        badge = f"  {VERDICT_META[f['_bucket']][1]}" if segment == "past" and f.get("_bucket") else ""
        label = f"{flag}{f['MOVIE_TITLE']}{badge}"
        if st.button(label, key=f"film_{f['MOVIE_ID']}", use_container_width=True):
            st.session_state.selected_id = f["MOVIE_ID"]
    if not films:
        st.info("No films match your search.")

with right:
    d = detail_for(st.session_state.selected_id) if st.session_state.selected_id else None
    if not d:
        st.markdown("<div style='color:#8190a8;padding:48px;text-align:center'>"
                    "Select a film to see its opening-weekend prediction.</div>", unsafe_allow_html=True)
    else:
        is_released = d["PREDICTION_TYPE"] != "UPCOMING"
        bk_text, tone = breakout_label(d["BREAKOUT_PCT"])
        lo = d["BEAR_OW_M"]
        hi = max(d["BULL_OW_M"], lo + 1)
        span = hi - lo
        def pos(v):
            return f"{min(100, max(0, (v - lo) / span * 100)):.1f}%"
        peak_pct = (d["PRED_OW_M"] - lo) / span * 100
        dpath = density_path(peak_pct, d["P_SMALL_PCT"], d["P_LARGE_PCT"])

        rel = d.get("RELEASE_DATE")
        try:
            from datetime import date
            rel_fmt = date.fromisoformat(rel).strftime("%B %-d, %Y") if rel else "Release TBD"
        except Exception:
            rel_fmt = rel or "Release TBD"
        ptype = {"OOF_BACKTEST": "Backtested (held-out)", "UPCOMING": "Upcoming"}.get(d["PREDICTION_TYPE"], "Released")

        breakout_chip = ""
        if d["PRED_TIER"].upper() != "LARGE+" and d["P_LARGE_PCT"] >= 30:
            breakout_chip = '<div class="breakout-flag">▲ Breakout watch</div>'

        outcome = ""
        if is_released and d.get("ACTUAL_OW_M") is not None:
            b = accuracy_bucket(d)
            vlabel, vsym, vcolor, vtone = VERDICT_META.get(b, ("—", "", "#8190a8", ""))
            r = pct_off(d)
            off_txt = f"{r*100:.0f}% off" if r is not None else "—"
            outcome = f"""<div class="outcome {vtone}">
              <div class="outcome-item"><span class="outcome-label">Actual opening</span><span class="outcome-val">{money(d['ACTUAL_OW_M'])}</span></div>
              <div class="outcome-item"><span class="outcome-label">Dollar miss</span><span class="outcome-val">{money(d.get('ABS_ERROR_M'))}</span></div>
              <div class="outcome-item"><span class="outcome-label">Off by</span><span class="outcome-val">{off_txt}</span></div>
              <div class="outcome-item"><span class="outcome-label">Accuracy</span><span class="outcome-val" style="color:{vcolor}">{vsym} {vlabel}</span></div>
            </div>"""

        probs = [("Small", d["P_SMALL_PCT"], "tier-small"), ("Mid", d["P_MID_PCT"], "tier-mid"), ("Large+", d["P_LARGE_PCT"], "tier-large")]
        prob_rows = "".join(
            f'<div class="prob-row"><span class="prob-name">{name}</span>'
            f'<div class="prob-bar"><div class="prob-fill {cls}" style="width:{pct}%"></div></div>'
            f'<span class="prob-val">{pct}%</span></div>'
            for name, pct, cls in probs)

        summary = f'<div class="summary"><span>⚠️</span><p>{d["SUMMARY_TEXT"]}</p></div>' if d.get("SUMMARY_TEXT") else ""

        drivers = compute_drivers(st.session_state.selected_id)
        drivers_html = ""
        if drivers:
            rows = "".join(
                f'<div class="driver-row">'
                f'<div class="driver-info"><span class="driver-label">{dr["label"]}</span>'
                f'<span class="driver-detail">{dr["direction"]}</span></div>'
                f'<div class="driver-bar"><div class="driver-fill" style="width:{min(100, dr["pct"]*100):.0f}%;background:{PUSH_COLOR[dr["push"]]}"></div></div>'
                f'<span class="driver-push" style="color:{PUSH_COLOR[dr["push"]]}">→ {dr["push"]}</span>'
                f'</div>'
                for dr in drivers)
            drivers_html = f'<div class="drivers-section"><div class="drivers-title">What\'s driving this call</div><div class="drivers-list">{rows}</div></div>'

        st.markdown(f"""
<div class="pred-card">
  <div class="pred-head">
    <div>
      <div class="film-title">{d['MOVIE_TITLE']}</div>
      <div class="film-sub">{rel_fmt} · {ptype} · {d['MODEL_VERSION']}</div>
    </div>
    {breakout_chip}
  </div>
  {outcome}
  <div class="pred-grid">
    <div class="pred-primary">
      <div class="metric-label">Predicted opening weekend</div>
      <div class="metric-big">{money(d['PRED_OW_M'])}</div>
      <span class="tier-pill {tier_class(d['PRED_TIER'])}">{TIER_LABEL.get(d['PRED_TIER'], d['PRED_TIER'])}</span>
      <div class="range-block">
        <div class="range-row"><span>Bear {money(d['BEAR_OW_M'])}</span><span>Bull {money(d['BULL_OW_M'])}</span></div>
        <div class="range-track-wrap">
          <svg class="density-svg" viewBox="0 0 200 40" preserveAspectRatio="none">
            <path d="{dpath}" fill="url(#g)" opacity="0.6"/>
            <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#4aa9cf"/><stop offset="50%" stop-color="#11567f"/><stop offset="100%" stop-color="#2e9e6b"/>
            </linearGradient></defs>
          </svg>
          <div class="range-track">
            <div class="range-marker base" style="left:{pos(d['BASE_OW_M'])}"></div>
            <div class="range-marker point" style="left:{pos(d['PRED_OW_M'])}"></div>
          </div>
        </div>
        <div class="range-caption">Probability density across the range. Darker = higher model confidence.</div>
      </div>
    </div>
    <div class="pred-secondary">
      <div class="breakout-box tone-{tone}">
        <div class="breakout-pct">{d['BREAKOUT_PCT']}%</div>
        <div class="breakout-meta"><div class="breakout-title">Chance of a Large+ breakout</div><div class="breakout-text">{bk_text}</div></div>
      </div>
      <div class="prob-split"><div class="prob-title">How confident, by tier</div>{prob_rows}</div>
    </div>
  </div>
  {drivers_html}
  {summary}
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='color:#8190a8;font-size:.78rem;margin-top:18px'>Powered by Snowflake · "
            "Predictions are calibrated tier calls with breakout odds, not precise dollar guarantees · "
            "Live pre-release predictions only (no holdout backtests) · static snapshot of the OW_INTELLIGENCE model output.</div>", unsafe_allow_html=True)
