"""Presentation layer: page styles and static HTML fragments. No app logic lives here."""
import base64
import html
import math

INK = "#0E1218"
SIGNAL = "#2FD5C4"
HEALTHY = "#4ECB8D"
RISK = "#E8674F"


def esc(value):
    return html.escape(str(value))


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

:root {
    --ink: #0E1218;
    --panel: #161C27;
    --panel-2: #1B2230;
    --line: #262E3D;
    --line-2: #33405A;
    --ice: #E8ECF2;
    --muted: #9BA5B4;
    --faint: #6B7586;
    --signal: #2FD5C4;
    --healthy: #4ECB8D;
    --risk: #E8674F;
    --mono: 'Space Mono', ui-monospace, monospace;
}

/* ---------- Streamlit chrome off: this is a site, not a notebook ---------- */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], #MainMenu, footer {
    display: none !important;
}
.stApp, [data-testid="stAppViewContainer"] { background: var(--ink); }
[data-testid="stMainBlockContainer"] {
    max-width: none !important;
    padding: 0 !important;
}
[data-testid="stMain"] { overflow-x: hidden; }

/* ---------- Navbar ---------- */
.st-key-navbar {
    position: sticky;
    top: 0;
    z-index: 1000;
    padding: 12px max(24px, calc((100% - 1136px) / 2)) !important;
    background: rgba(14, 18, 24, 0.86);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--line);
}
.ns-brand { display: flex; align-items: center; gap: 10px; }
.ns-brand img { display: block; }
.ns-brand .ns-wordmark { font-size: 19px; font-weight: 600; letter-spacing: -0.01em; color: var(--ice); }

.st-key-nav [data-testid="stButtonGroup"] { gap: 2px; }
.st-key-nav button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    color: var(--muted) !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    min-height: 36px !important;
}
.st-key-nav button:hover { color: var(--ice) !important; background: rgba(232, 236, 242, 0.05) !important; }
.st-key-nav button[aria-checked="true"] {
    background: rgba(47, 213, 196, 0.12) !important;
}
.st-key-nav button[aria-checked="true"] p { color: var(--signal) !important; }

.st-key-navbar [data-testid="stPopoverButton"] {
    border-radius: 999px !important;
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    font-family: var(--mono);
    font-size: 13px;
    min-height: 36px;
}

/* ---------- Page column ---------- */
.st-key-page {
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    padding: 24px 32px 72px !important;
}

/* ---------- Native widgets ---------- */
.stButton button, .stDownloadButton button {
    border-radius: 10px !important;
    min-height: 44px;
    font-weight: 500;
}
button[kind="primary"], [data-testid="stBaseButton-primary"] {
    color: var(--ink) !important;
    font-weight: 600 !important;
}
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p { color: var(--ink) !important; }
button[kind="primary"]:hover { filter: brightness(1.07); }

[data-testid="stFileUploaderDropzone"] {
    background: rgba(232, 236, 242, 0.02) !important;
    border: 1px dashed var(--line-2) !important;
    border-radius: 14px !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--signal) !important; }

/* Recorder: one confident pill-shaped control */
.st-key-capture [data-testid="stAudioInput"] {
    background: var(--ink) !important;
    border: 1px solid var(--line-2) !important;
    border-radius: 999px !important;
    padding: 6px 8px !important;
    box-shadow: 0 0 0 4px rgba(47, 213, 196, 0.06);
}
.st-key-capture [data-testid="stAudioInput"] > div { background: transparent !important; border: none !important; }
.st-key-capture [data-testid="stAudioInput"] button {
    background: var(--signal) !important;
    color: var(--ink) !important;
    border-radius: 999px !important;
    border: none !important;
}
.st-key-capture [data-testid="stAudioInputActionButton"] {
    width: 48px !important; height: 48px !important; min-width: 48px !important;
    display: inline-flex !important; align-items: center; justify-content: center;
    box-shadow: 0 0 0 6px rgba(47, 213, 196, 0.12);
}
.st-key-capture [data-testid="stAudioInput"] button svg {
    fill: var(--ink) !important; color: var(--ink) !important; width: 24px !important; height: 24px !important;
}

/* ---------- Cards ---------- */
.st-key-capture, [class*="st-key-card-"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 22px 24px !important;
}
.st-key-capture { padding: 26px 26px 24px !important; }

.ns-card-title { margin: 0; font-size: 17px; font-weight: 600; color: var(--ice); }
.ns-card-sub { margin: 4px 0 0; font-size: 13.5px; color: var(--muted); line-height: 1.5; }

/* ---------- Hero ---------- */
.ns-hero { padding: 40px 0 8px; }
.ns-status {
    display: inline-flex; align-items: center; gap: 8px;
    margin: 0 0 22px; padding: 6px 12px 6px 10px;
    border: 1px solid var(--line); border-radius: 999px;
    font-size: 13px; color: var(--muted);
}
.ns-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--healthy); box-shadow: 0 0 0 3px rgba(78, 203, 141, 0.18); }
.ns-dot.off { background: var(--risk); box-shadow: 0 0 0 3px rgba(232, 103, 79, 0.18); }
.ns-hero h1 {
    margin: 0;
    font-size: clamp(36px, 4.6vw, 58px);
    line-height: 1.04;
    font-weight: 600;
    letter-spacing: -0.03em;
    color: var(--ice);
    max-width: 14ch;
}
.ns-lede { margin: 22px 0 0; max-width: 52ch; font-size: 17px; line-height: 1.65; color: var(--muted); }
.ns-steps { list-style: none; margin: 34px 0 0; padding: 0 !important; display: grid; gap: 0; max-width: 460px; }
.ns-steps li { margin: 0 !important; display: grid; grid-template-columns: 34px 1fr; gap: 14px; align-items: start; padding: 12px 0; border-top: 1px solid var(--line); }
.ns-steps li:last-child { border-bottom: 1px solid var(--line); }
.ns-steps .n { font-family: var(--mono); font-size: 13px; color: var(--signal); padding-top: 2px; }
.ns-steps strong { display: block; font-weight: 600; color: var(--ice); font-size: 15px; }
.ns-steps span.d { display: block; color: var(--muted); font-size: 14px; margin-top: 2px; }

/* ---------- Capture card ---------- */
.ns-cap-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.ns-mono { font-family: var(--mono); color: var(--ice); }
.ns-scope {
    position: relative;
    margin-top: 6px;
    height: 132px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background-color: #0B0F15;
    background-image:
        linear-gradient(rgba(232, 236, 242, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(232, 236, 242, 0.04) 1px, transparent 1px);
    background-size: 100% 22px, 30px 100%;
    overflow: hidden;
}
.st-key-capture [data-testid="stImage"] img {
    border-radius: 12px;
    border: 1px solid var(--line);
}
.ns-prompt { margin: 0; text-align: center; font-size: 15px; font-weight: 500; color: var(--ice); }
.ns-scope img {
    position: absolute; inset: 0; width: 100%; height: 100%;
    filter: drop-shadow(0 0 6px rgba(47, 213, 196, 0.45));
}
.ns-hint { margin: 2px 0 0; text-align: center; font-size: 13px; color: var(--faint); }
.ns-or { display: flex; align-items: center; gap: 12px; color: var(--faint); font-size: 13px; margin: 2px 0; }
.ns-or::before, .ns-or::after { content: ""; flex: 1; height: 1px; background: var(--line); }

/* ---------- Sections ---------- */
.ns-section { padding: 72px 0 0; }
.ns-section h2 { margin: 0; font-size: 30px; font-weight: 600; letter-spacing: -0.02em; color: var(--ice); }
.ns-section .intro { margin: 10px 0 0; max-width: 60ch; color: var(--muted); font-size: 16px; line-height: 1.6; }
.ns-groups { margin-top: 30px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.ns-group { border: 1px solid var(--line); border-radius: 16px; padding: 22px; background: linear-gradient(180deg, var(--panel), rgba(22, 28, 39, 0.4)); }
.ns-group h3 { margin: 0 0 4px; font-size: 16px; font-weight: 600; color: var(--ice); }
.ns-group .why { margin: 0 0 16px; color: var(--muted); font-size: 14px; line-height: 1.5; }
.ns-group dl { margin: 0 !important; padding: 0 !important; display: grid; gap: 12px; }
.ns-group dl > div, .ns-group dt, .ns-group dd { margin-left: 0 !important; padding-left: 0 !important; }
.ns-group dt { font-size: 14.5px; color: var(--ice); font-weight: 500; }
.ns-group dd { margin: 2px 0 0; font-size: 13.5px; color: var(--faint); line-height: 1.45; }

/* ---------- Page headers ---------- */
.ns-pagehead { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; padding: 24px 0 8px; }
.ns-pagehead h1 { margin: 0; font-size: 36px; font-weight: 600; letter-spacing: -0.025em; color: var(--ice); }
.ns-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.ns-chip { padding: 5px 11px; border-radius: 999px; border: 1px solid var(--line); font-size: 13px; color: var(--muted); }
.ns-chip b { font-family: var(--mono); font-weight: 400; color: var(--ice); }

/* ---------- Result panel ---------- */
.ns-result {
    position: relative;
    border-radius: 20px;
    border: 1px solid var(--line);
    background: var(--panel);
    padding: 28px 30px;
    overflow: hidden;
    height: 100%;
    box-sizing: border-box;
}
.ns-result::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--state); }
.ns-result.healthy { --state: var(--healthy); }
.ns-result.risk { --state: var(--risk); }
.ns-result .top { display: flex; justify-content: space-between; gap: 24px; align-items: center; }
.ns-result .k { margin: 0; font-size: 13.5px; color: var(--muted); }
.ns-result h2 { margin: 6px 0 0; font-size: clamp(40px, 5vw, 60px); line-height: 1; font-weight: 600; letter-spacing: -0.03em; color: var(--state); }
.ns-result .explain { margin: 14px 0 0; max-width: 46ch; color: var(--ice); font-size: 15.5px; line-height: 1.55; }
.ns-ring { position: relative; width: 116px; height: 116px; flex: none; }
.ns-ring img { display: block; width: 116px; height: 116px; }
.ns-ring .v { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ns-ring .v b { font-family: var(--mono); font-size: 24px; font-weight: 400; color: var(--ice); }
.ns-ring .v span { font-size: 12px; color: var(--muted); }
.ns-obs { margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--line); }
.ns-obs ul { margin: 8px 0 0; padding: 0; list-style: none; display: grid; gap: 6px; }
.ns-obs li { position: relative; padding-left: 18px; color: var(--ice); font-size: 15px; line-height: 1.5; }
.ns-obs li::before { content: ""; position: absolute; left: 0; top: 0.6em; width: 7px; height: 7px; border-radius: 50%; background: var(--state); }
.ns-caveat { margin: 18px 0 0; font-size: 13px; color: var(--faint); }

.ns-stat { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding: 14px 0 4px; border-top: 1px solid var(--line); margin-top: 6px; }
.ns-stat b { font-family: var(--mono); font-weight: 400; font-size: 26px; color: var(--ice); }
.ns-stat span { font-size: 13px; color: var(--muted); }

.ns-callout { display: flex; gap: 12px; padding: 14px 18px; border-radius: 14px; border: 1px solid rgba(242, 166, 90, 0.35); background: rgba(242, 166, 90, 0.07); color: var(--ice); font-size: 14.5px; line-height: 1.5; }
.ns-callout.info { border-color: rgba(47, 213, 196, 0.3); background: rgba(47, 213, 196, 0.06); }
.ns-callout strong { display: block; margin-bottom: 4px; }
.ns-callout ul { margin: 4px 0 0; padding-left: 18px !important; }
.ns-callout li { font-size: 14.5px; margin: 2px 0 0 !important; }
.ns-obs ul { padding: 0 !important; }
.ns-obs li { margin: 0 !important; }

/* ---------- Biomarker panel ---------- */
.ns-panel { border: 1px solid var(--line); border-radius: 18px; background: var(--panel); padding: 22px 24px 10px; }
.ns-panel .legend { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; font-size: 12.5px; color: var(--faint); }
.ns-panel .legend i { display: inline-block; width: 18px; height: 6px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
.bm-group { margin-top: 20px; }
.bm-group h4 { margin: 0 0 4px; font-size: 13px; font-weight: 500; color: var(--signal); }
.bm-row {
    display: grid;
    grid-template-columns: minmax(150px, 1.2fr) minmax(90px, 1fr) 104px 84px;
    gap: 16px;
    align-items: center;
    padding: 12px 0;
    border-top: 1px solid var(--line);
}
.bm-name span { display: block; color: var(--ice); font-size: 14.5px; font-weight: 500; }
.bm-name small { display: block; color: var(--faint); font-size: 12.5px; margin-top: 2px; }
.bm-track { position: relative; height: 6px; border-radius: 3px; background: rgba(232, 236, 242, 0.07); }
.bm-zone { position: absolute; top: 0; bottom: 0; border-radius: 3px; background: rgba(78, 203, 141, 0.28); }
.bm-tick { position: absolute; top: -4px; bottom: -4px; width: 2px; margin-left: -1px; background: rgba(232, 236, 242, 0.55); border-radius: 1px; }
.bm-mark { position: absolute; top: 50%; width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; border: 2px solid var(--ink); }
.bm-mark.ok { background: var(--healthy); }
.bm-mark.bad { background: var(--risk); }
.bm-val { font-family: var(--mono); font-size: 14.5px; color: var(--ice); text-align: right; white-space: nowrap; }
.bm-pill { justify-self: end; padding: 3px 10px; border-radius: 999px; font-size: 12.5px; font-weight: 500; }
.bm-pill.ok { color: var(--healthy); background: rgba(78, 203, 141, 0.12); }
.bm-pill.bad { color: var(--risk); background: rgba(232, 103, 79, 0.12); }

/* ---------- History ---------- */
.ns-summary { display: grid; grid-template-columns: repeat(4, 1fr); border: 1px solid var(--line); border-radius: 16px; background: var(--panel); }
.ns-summary div { padding: 18px 22px; border-left: 1px solid var(--line); }
.ns-summary div:first-child { border-left: none; }
.ns-summary dt { font-size: 13px; color: var(--muted); }
.ns-summary dd { margin: 6px 0 0; font-size: 20px; color: var(--ice); font-weight: 500; }
.ns-summary dd.mono { font-family: var(--mono); font-size: 17px; font-weight: 400; }

/* ---------- Empty states ---------- */
.ns-empty { text-align: center; padding: 72px 24px 20px; }
.ns-empty svg { opacity: 0.9; }
.ns-empty h2 { margin: 18px 0 0; font-size: 26px; font-weight: 600; color: var(--ice); letter-spacing: -0.02em; }
.ns-empty p { margin: 10px auto 0; max-width: 46ch; color: var(--muted); font-size: 15.5px; line-height: 1.6; }

/* ---------- Footer ---------- */
.ns-footer { border-top: 1px solid var(--line); background: #0B0E14; }
.ns-footer .inner { max-width: 1200px; box-sizing: border-box; margin: 0 auto; padding: 36px 32px 44px; display: grid; grid-template-columns: 1fr 1.6fr; gap: 32px; }
.ns-footer p { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.6; }
.ns-footer p + p { margin-top: 8px; color: var(--faint); font-size: 13px; }

/* ---------- Small screens ---------- */
@media (max-width: 900px) {
    .ns-groups { grid-template-columns: 1fr; }
    .ns-summary { grid-template-columns: repeat(2, 1fr); }
    .ns-summary div:nth-child(3) { border-left: none; }
    .ns-summary div:nth-child(n+3) { border-top: 1px solid var(--line); }
    .ns-footer .inner { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
    .st-key-page { padding: 12px 16px 56px !important; }
    .st-key-navbar { padding: 10px 16px !important; }
    .ns-hero { padding-top: 16px; }
    .bm-row { grid-template-columns: 1fr auto; gap: 8px 12px; }
    .bm-row .bm-bar { grid-column: 1 / -1; order: 3; }
    .bm-val { text-align: left; }
    .ns-result .top { flex-direction: column; align-items: flex-start; }
    .ns-footer .inner { padding: 28px 16px 36px; }
}
</style>
"""


# st.html sanitizes inline <svg>, so vector art ships as data-URI images instead.
def _img(svg, width, height, cls=""):
    data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<img class="{cls}" src="data:image/svg+xml;base64,{data}" '
            f'width="{width}" height="{height}" alt="" aria-hidden="true">')


def _bars_svg(size, heights, fill_bg, fill_bar, radius):
    bar_w, gap = size * 0.08, size * 0.055
    total = len(heights) * bar_w + (len(heights) - 1) * gap
    x = (size - total) / 2
    rects = []
    for h in heights:
        bh = size * h
        rects.append(
            f'<rect x="{x:.2f}" y="{(size - bh) / 2:.2f}" width="{bar_w:.2f}" '
            f'height="{bh:.2f}" rx="{bar_w / 2:.2f}" fill="{fill_bar}"/>'
        )
        x += bar_w + gap
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<rect width="{size}" height="{size}" rx="{radius}" fill="{fill_bg}"/>{"".join(rects)}</svg>'
    )
    return _img(svg, size, size)


def brand():
    mark = _bars_svg(30, [0.2, 0.42, 0.62, 0.42, 0.26], SIGNAL, INK, 8)
    return f'<div class="ns-brand">{mark}<span class="ns-wordmark">NeuroSentinel</span></div>'


def hero(language_code, model_ok):
    language = "Hindi (experimental)" if language_code == "hi" else "English"
    if model_ok:
        status = f'<span class="ns-dot"></span>Ready to record in {language}'
    else:
        status = '<span class="ns-dot off"></span>Classifier unavailable on this server'
    return f"""
<section class="ns-hero">
  <p class="ns-status">{status}</p>
  <h1>A one-minute voice check for early signs of cognitive decline.</h1>
  <p class="ns-lede">Speak naturally for 30 to 60 seconds. NeuroSentinel measures nine speech
  biomarkers, from pauses and pace to vocabulary and voice quality, and compares them with
  patterns learned from 157 clinical recordings.</p>
  <ol class="ns-steps">
    <li><span class="n">01</span><div><strong>Record or upload</strong><span class="d">Use the microphone, or drop in a .wav file.</span></div></li>
    <li><span class="n">02</span><div><strong>Run the analysis</strong><span class="d">Takes a few seconds. No third-party services involved.</span></div></li>
    <li><span class="n">03</span><div><strong>Review and export</strong><span class="d">See the result, the full biomarker panel and a PDF report.</span></div></li>
  </ol>
</section>"""


def capture_header(patient_id):
    return f"""
<div class="ns-cap-head">
  <p class="ns-card-title">New recording</p>
  <p class="ns-card-sub">Patient <span class="ns-mono">{esc(patient_id)}</span></p>
</div>"""


def _wave_path(width=600, height=132):
    # Speech-like trace: a fast carrier inside syllable-shaped bursts, grouped into phrases.
    points = []
    for x in range(0, width + 1):
        t = x / width
        phrase = math.sin(t * math.pi) ** 0.5
        syllables = abs(math.sin(t * math.pi * 9.5 + 0.7)) ** 2.2
        pause = 0.15 if 0.46 < t < 0.53 else 1.0
        envelope = phrase * (0.08 + 0.92 * syllables) * pause
        carrier = math.sin(x * 1.37) * 0.7 + math.sin(x * 2.91 + 1.3) * 0.3
        y = height / 2 + envelope * height * 0.42 * carrier
        points.append(f"{x},{y:.1f}")
    return "M" + " L".join(points)


_SCOPE_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 132" preserveAspectRatio="none">
<style>
.mid {{ stroke: rgba(232,236,242,0.12); stroke-width: 1; }}
.trace {{ fill: none; stroke: {SIGNAL}; stroke-width: 1.6; stroke-dasharray: 1; stroke-dashoffset: 1;
         animation: draw 1.8s cubic-bezier(.4,0,.2,1) .15s forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .trace {{ animation: none; stroke-dashoffset: 0; }} }}
</style>
<line class="mid" x1="0" y1="66" x2="600" y2="66" vector-effect="non-scaling-stroke"/>
<path class="trace" pathLength="1" vector-effect="non-scaling-stroke" d="{_wave_path()}"/>
</svg>"""

SCOPE = f'<div class="ns-scope">{_img(_SCOPE_SVG, 600, 132, "trace-img")}</div>'


def divider(text):
    return f'<div class="ns-or">{esc(text)}</div>'


def hint(text):
    return f'<p class="ns-hint">{esc(text)}</p>'


MEASURES = """
<section class="ns-section">
  <h2>What it measures</h2>
  <p class="intro">Nine biomarkers across three dimensions of speech, drawn from research on how
  speech changes with cognitive decline. Together they make up the patient's speech profile.</p>
  <div class="ns-groups">
    <div class="ns-group">
      <h3>Timing and fluency</h3>
      <p class="why">How smoothly speech flows, and how quickly it starts.</p>
      <dl>
        <div><dt>Pause rate</dt><dd>Share of the recording spent in pauses longer than 0.25 s.</dd></div>
        <div><dt>Speech rate</dt><dd>Words spoken per second.</dd></div>
        <div><dt>Initial latency</dt><dd>Time before the first word.</dd></div>
      </dl>
    </div>
    <div class="ns-group">
      <h3>Language</h3>
      <p class="why">How much is said, and how varied the vocabulary is.</p>
      <dl>
        <div><dt>Vocabulary richness</dt><dd>Unique words divided by total words.</dd></div>
        <div><dt>Word count</dt><dd>Total words in the transcript.</dd></div>
      </dl>
    </div>
    <div class="ns-group">
      <h3>Voice acoustics</h3>
      <p class="why">Articulation, clarity and expressiveness of the voice itself.</p>
      <dl>
        <div><dt>Acoustic texture</dt><dd>Average of 13 MFCCs, a proxy for articulation.</dd></div>
        <div><dt>MFCC delta</dt><dd>How quickly the spectral shape changes.</dd></div>
        <div><dt>Brightness</dt><dd>Spectral centroid of the voice, in Hz.</dd></div>
        <div><dt>Emotional range</dt><dd>Variance in pitch across the recording.</dd></div>
      </dl>
    </div>
  </div>
</section>"""


def page_header(title, patient_id, language_code=None):
    chips = f'<span class="ns-chip">Patient <b>{esc(patient_id)}</b></span>'
    if language_code:
        language = "Hindi (experimental)" if language_code == "hi" else "English"
        chips += f'<span class="ns-chip">{language}</span>'
    return f'<div class="ns-pagehead"><h1>{esc(title)}</h1><div class="ns-meta">{chips}</div></div>'


def card_title(title, sub=None):
    sub_html = f'<p class="ns-card-sub">{esc(sub)}</p>' if sub else ""
    return f'<div><p class="ns-card-title">{esc(title)}</p>{sub_html}</div>'


def _ring(fraction, color):
    radius = 50
    circumference = 2 * math.pi * radius
    filled = max(0.0, min(1.0, fraction)) * circumference
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="116" height="116" viewBox="0 0 116 116">
<g transform="rotate(-90 58 58)">
<circle cx="58" cy="58" r="{radius}" fill="none" stroke="rgba(232,236,242,0.08)" stroke-width="8"/>
<circle cx="58" cy="58" r="{radius}" fill="none" stroke="{color}" stroke-width="8"
        stroke-linecap="round" stroke-dasharray="{filled:.1f} {circumference:.1f}"/>
</g></svg>"""
    return f"""
<div class="ns-ring">
  {_img(svg, 116, 116)}
  <div class="v"><b>{fraction * 100:.0f}%</b><span>confidence</span></div>
</div>"""


def result_panel(label, confidence, summary):
    healthy = label == "Healthy"
    state = "healthy" if healthy else "risk"
    if healthy:
        explain = "No speech pattern associated with cognitive decline crossed the screening threshold."
    else:
        explain = ("Speech patterns in this recording resemble the dementia group in the training "
                   "recordings. A clinical follow-up is recommended.")
    observations = "".join(f"<li>{esc(item.strip())}</li>" for item in str(summary).split("|") if item.strip())
    return f"""
<section class="ns-result {state}">
  <div class="top">
    <div>
      <p class="k">Screening result</p>
      <h2>{esc(label)}</h2>
      <p class="explain">{explain}</p>
    </div>
    {_ring(confidence, HEALTHY if healthy else RISK)}
  </div>
  <div class="ns-obs">
    <p class="k">Clinical observations</p>
    <ul>{observations}</ul>
  </div>
  <p class="ns-caveat">Screening aid, not a diagnosis. A healthy result does not rule out cognitive decline.</p>
</section>"""


def trial_stat(accuracy, total):
    tests = "test" if total == 1 else "tests"
    return f'<div class="ns-stat"><span>Live trial accuracy</span><b>{accuracy:.1f}%</b></div><p class="ns-card-sub">Across {total} {tests} confirmed this session.</p>'


def callout(title, body_html, kind="warn"):
    cls = "ns-callout info" if kind == "info" else "ns-callout"
    return f'<div class="{cls}"><div><strong>{esc(title)}</strong>{body_html}</div></div>'


def notes_callout(notes):
    items = "".join(f"<li>{esc(n)}</li>" for n in notes)
    return callout("Recording quality", f"<ul>{items}</ul>")


def _row(name, hint_text, value, status, ok, position, lo, hi, threshold, good_side):
    def pct(v):
        return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))
    thr = pct(threshold)
    zone = f"left:0;width:{thr:.1f}%" if good_side == "below" else f"left:{thr:.1f}%;width:{100 - thr:.1f}%"
    cls = "ok" if ok else "bad"
    return f"""
<div class="bm-row">
  <div class="bm-name"><span>{name}</span><small>{hint_text}</small></div>
  <div class="bm-bar"><div class="bm-track">
    <span class="bm-zone" style="{zone}"></span>
    <span class="bm-tick" style="left:{thr:.1f}%"></span>
    <span class="bm-mark {cls}" style="left:{pct(position):.1f}%"></span>
  </div></div>
  <div class="bm-val">{value}</div>
  <div class="bm-pill {cls}">{status}</div>
</div>"""


def biomarker_panel(data):
    v = lambda key: data[key][0]  # noqa: E731
    pr, vr, wc = v('pause_rate'), v('vocab_richness'), v('word_count')
    sr, il, at = v('speech_rate'), v('initial_latency'), v('acoustic_texture')
    md, sb, er = v('mfcc_delta'), v('speech_brightness'), v('emotional_range')

    # Thresholds and status words mirror the clinical cutoffs used throughout the app
    # (mean -/+ 1 std of the real Healthy class in data/dataset.csv).
    groups = [
        ("Timing and fluency", [
            _row("Pause rate", "Share of time spent pausing", f"{pr:.2f}",
                 "Risk" if pr > 0.35 else "Normal", not pr > 0.35, pr, 0, 1, 0.35, "below"),
            _row("Speech rate", "Words per second", f"{sr:.1f} wps",
                 "Good" if sr > 1.9 else "Slow", sr > 1.9, sr, 0, 4, 1.9, "above"),
            _row("Initial latency", "Delay before the first word", f"{il:.2f}s",
                 "Fast" if il < 3.0 else "Delayed", il < 3.0, il, 0, 8, 3.0, "below"),
        ]),
        ("Language", [
            _row("Vocabulary richness", "Unique ÷ total words", f"{vr:.2f}",
                 "Good" if vr > 0.55 else "Low", vr > 0.55, vr, 0, 1, 0.55, "above"),
            _row("Word count", "Words transcribed", f"{wc}",
                 "Good" if wc > 80 else "Low", wc > 80, wc, 0, 200, 80, "above"),
        ]),
        ("Voice acoustics", [
            _row("Acoustic texture", "Mean of 13 MFCCs", f"{at:.2f}",
                 "Clear" if at > -30 else "Muffled", at > -30, at, -60, 20, -30, "above"),
            _row("MFCC delta", "Rate of spectral change", f"{md:.4f}",
                 "Stable" if abs(md) < 0.015 else "Variable", abs(md) < 0.015, abs(md), 0, 0.06, 0.015, "below"),
            _row("Brightness", "Spectral centroid", f"{sb:.0f} Hz",
                 "Good" if sb > 1600 else "Low", sb > 1600, sb, 0, 4000, 1600, "above"),
            _row("Emotional range", "Pitch variance", f"{er:,.1f}",
                 "Expressive" if er > 1000000 else "Flat", er > 1000000, er, 0, 3000000, 1000000, "above"),
        ]),
    ]
    body = "".join(
        f'<div class="bm-group"><h4>{title}</h4>{"".join(rows)}</div>' for title, rows in groups
    )
    return f"""
<section class="ns-panel">
  {card_title("Biomarker panel", "Each value is plotted against the healthy range from the training data.")}
  <div class="legend">
    <span><i style="background:rgba(78,203,141,0.45)"></i>Healthy range</span>
    <span><i style="background:rgba(232,236,242,0.55);width:2px;height:12px"></i>Threshold</span>
  </div>
  {body}
</section>"""


def history_summary(h_df):
    total = len(h_df)
    flagged = int((h_df["risk_label"] != "Healthy").sum()) if "risk_label" in h_df.columns else 0
    latest = h_df.iloc[-1]
    latest_label = latest.get("risk_label", "—")
    color = HEALTHY if latest_label == "Healthy" else RISK
    last_seen = str(latest.get("timestamp", "—"))[:16]
    return f"""
<dl class="ns-summary">
  <div><dt>Assessments</dt><dd class="mono">{total}</dd></div>
  <div><dt>Flagged for follow-up</dt><dd class="mono">{flagged}</dd></div>
  <div><dt>Latest result</dt><dd style="color:{color}">{esc(latest_label)}</dd></div>
  <div><dt>Last assessed</dt><dd class="mono">{esc(last_seen)}</dd></div>
</dl>"""


def empty_state(title, text):
    icon = _bars_svg(56, [0.16, 0.3, 0.46, 0.3, 0.18], "#161C27", SIGNAL, 16)
    return f'<div class="ns-empty">{icon}<h2>{esc(title)}</h2><p>{esc(text)}</p></div>'


def footer():
    return f"""
<div class="ns-footer" role="contentinfo">
  <div class="inner">
    <div>{brand()}</div>
    <div>
      <p>Research-grade screening aid, not a diagnostic tool. Results should be reviewed by a qualified clinician.</p>
      <p>Audio is analysed on the machine running NeuroSentinel and is not sent to third-party services. Version 1.2, clinical research build.</p>
    </div>
  </div>
</div>"""
