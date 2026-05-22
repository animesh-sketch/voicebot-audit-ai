"""
utils.py — Shared UI helpers, CSS injection, and reusable Streamlit components.
"""
import streamlit as st


# ─────────────────────────── CSS ─────────────────────────────────

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap');

/* ── Design tokens ── */
:root {
    --green:      #00D68F;
    --green-dim:  #00A36B;
    --blue:       #0EA5E9;
    --blue-dim:   #0284C7;
    --sky:        #38BDF8;
    --pink:       #F472B6;
    --pink-hot:   #EC4899;
    --purple:     #A78BFA;
    --bg:         #070B14;
    --bg2:        #0D1424;
    --bg3:        #131D30;
    --card:       rgba(19,29,48,0.85);
    --border:     rgba(56,189,248,0.15);
    --border-hot: rgba(244,114,182,0.35);
    --text:       #E2E8F0;
    --text-muted: #64748B;
    --text-dim:   #94A3B8;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

/* ── Main content background ── */
.main .block-container {
    background: var(--bg) !important;
    padding-top: 1.5rem !important;
}
section[data-testid="stMain"] {
    background: radial-gradient(ellipse at 20% 10%, rgba(14,165,233,0.06) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 80%, rgba(244,114,182,0.05) 0%, transparent 60%),
                var(--bg) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        #08101E 0%,
        #0D1832 40%,
        #0A1426 70%,
        #06101C 100%) !important;
    border-right: 1px solid rgba(56,189,248,0.12) !important;
}
[data-testid="stSidebar"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--green), var(--blue), var(--sky), var(--pink));
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(56,189,248,0.1) !important; }

/* ── Nav buttons ── */
div.nav-link button {
    background: transparent !important;
    border: 1px solid transparent !important;
    text-align: left !important;
    padding: 0.55rem 1rem !important;
    border-radius: 10px !important;
    width: 100% !important;
    font-size: 0.88rem !important;
    color: #94A3B8 !important;
    transition: all 0.2s ease !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0.01em !important;
}
div.nav-link button:hover {
    background: rgba(14,165,233,0.1) !important;
    border-color: rgba(14,165,233,0.25) !important;
    color: var(--sky) !important;
    transform: translateX(3px) !important;
}
div.nav-active button {
    background: linear-gradient(90deg, rgba(14,165,233,0.18), rgba(56,189,248,0.08)) !important;
    border: 1px solid rgba(56,189,248,0.35) !important;
    border-left: 3px solid var(--sky) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 0 16px rgba(14,165,233,0.15) !important;
}

/* ── KPI cards ── */
.kpi-card {
    background: linear-gradient(135deg, rgba(19,29,48,0.9), rgba(13,20,36,0.95));
    border-radius: 16px;
    padding: 1.3rem 1.4rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    text-align: center;
    border: 1px solid var(--border);
    border-top: 3px solid;
    height: 100%;
    backdrop-filter: blur(12px);
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(255,255,255,0.03), transparent 70%);
    pointer-events: none;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.07);
}
.kpi-card .val  {
    font-size: 2.1rem; font-weight: 800; line-height: 1.1;
    font-family: 'Outfit', sans-serif;
    background: linear-gradient(135deg, #ffffff, #cbd5e1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.kpi-card .lbl  {
    font-size: 0.7rem; color: var(--text-dim); margin-top: 6px;
    text-transform: uppercase; letter-spacing: 0.1em; font-weight: 500;
}
.kpi-card .sub  { font-size: 0.75rem; color: var(--text-muted); margin-top: 3px; }

/* ── Status badges ── */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; border: 1px solid;
}
.badge-active  { background: rgba(0,214,143,0.12); color: var(--green);   border-color: rgba(0,214,143,0.3); }
.badge-inprog  { background: rgba(14,165,233,0.12); color: var(--blue);   border-color: rgba(14,165,233,0.3); }
.badge-rtc     { background: rgba(244,114,182,0.12); color: var(--pink);  border-color: rgba(244,114,182,0.3); }
.badge-closed  { background: rgba(100,116,139,0.12); color: #94A3B8;      border-color: rgba(100,116,139,0.3); }
.badge-pass    { background: rgba(0,214,143,0.12); color: var(--green);   border-color: rgba(0,214,143,0.3); }
.badge-fail    { background: rgba(248,113,113,0.12); color: #F87171;      border-color: rgba(248,113,113,0.3); }
.badge-pending { background: rgba(56,189,248,0.10); color: var(--sky);    border-color: rgba(56,189,248,0.25); }

/* ── Priority chips ── */
.pri { display:inline-block; padding:3px 9px; border-radius:6px;
       font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; }
.pri-CRITICAL { background: linear-gradient(135deg,#7F1D1D,#991B1B); color:#FCA5A5; border:1px solid rgba(248,113,113,0.4); }
.pri-HIGH     { background: linear-gradient(135deg,#7C2D12,#9A3412); color:#FDB88A; border:1px solid rgba(251,146,60,0.4); }
.pri-MEDIUM   { background: linear-gradient(135deg,#78350F,#92400E); color:#FCD34D; border:1px solid rgba(252,211,77,0.4); }
.pri-LOW      { background: linear-gradient(135deg,#052E16,#14532D); color:var(--green); border:1px solid rgba(0,214,143,0.3); }

/* ── Section header ── */
.sec-hdr {
    background: linear-gradient(90deg, rgba(14,165,233,0.1), rgba(14,165,233,0.02));
    border-left: 3px solid var(--blue);
    padding: 0.5rem 1rem;
    border-radius: 0 10px 10px 0;
    margin: 1rem 0 0.5rem 0;
    font-weight: 600;
    color: var(--sky);
    font-size: 0.92rem;
    letter-spacing: 0.02em;
}

/* ── Page header ── */
.page-title {
    font-size: 1.7rem; font-weight: 800;
    font-family: 'Outfit', sans-serif;
    background: linear-gradient(135deg, #ffffff 0%, var(--sky) 50%, var(--blue) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.2;
}
.page-sub { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.2rem; letter-spacing: 0.01em; }

/* ── Finding card ── */
.finding {
    background: linear-gradient(90deg, rgba(14,165,233,0.07), rgba(14,165,233,0.02));
    border-left: 3px solid var(--blue);
    padding: 0.65rem 1rem;
    margin-bottom: 0.5rem;
    border-radius: 0 10px 10px 0;
    font-size: 0.85rem;
    color: var(--text-dim);
    border: 1px solid rgba(14,165,233,0.12);
    border-left: 3px solid var(--blue);
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* ── Progress bar ── */
.prog-wrap { background: rgba(255,255,255,0.06); border-radius:8px; height:10px; overflow:hidden; border:1px solid rgba(255,255,255,0.05); }
.prog-fill { height:100%; border-radius:8px; transition:width 0.4s cubic-bezier(.4,0,.2,1); }

/* ── Info banner ── */
.info-banner {
    background: linear-gradient(135deg, rgba(14,165,233,0.15), rgba(56,189,248,0.08));
    border-radius: 14px;
    border: 1px solid rgba(56,189,248,0.2);
    padding: 1rem 1.5rem;
    color: var(--text);
    margin-bottom: 1rem;
    box-shadow: 0 4px 20px rgba(14,165,233,0.1);
}

/* ── Table tweaks ── */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stDataFrame"] th {
    background: rgba(14,165,233,0.12) !important;
    color: var(--sky) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stDataFrame"] td { color: var(--text-dim) !important; font-size: 0.85rem !important; }
[data-testid="stDataFrame"] tr:hover td { background: rgba(14,165,233,0.05) !important; }

/* ── Failure badge colors ── */
.fail-tag {
    display: inline-block; padding: 2px 8px; border-radius: 5px;
    font-size: 0.68rem; font-weight: 600; margin: 2px;
    background: rgba(244,114,182,0.12); color: var(--pink);
    border: 1px solid rgba(244,114,182,0.25);
}

/* ── Streamlit native widget overrides ── */
.stButton > button {
    background: linear-gradient(135deg, rgba(14,165,233,0.15), rgba(56,189,248,0.1)) !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
    color: var(--sky) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    padding: 0.45rem 1rem !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(14,165,233,0.28), rgba(56,189,248,0.18)) !important;
    border-color: var(--sky) !important;
    box-shadow: 0 0 20px rgba(14,165,233,0.25) !important;
    transform: translateY(-1px) !important;
    color: white !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--blue), var(--sky)) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 16px rgba(14,165,233,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 24px rgba(14,165,233,0.5) !important;
    transform: translateY(-2px) !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: rgba(13,20,36,0.8) !important;
    border: 1px solid rgba(56,189,248,0.2) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-size: 0.88rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px rgba(14,165,233,0.15) !important;
}
label[data-testid="stWidgetLabel"] { color: var(--text-dim) !important; font-size: 0.82rem !important; font-weight: 500 !important; }

/* ── Sliders ── */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--blue) !important;
    box-shadow: 0 0 8px rgba(14,165,233,0.5) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(13,20,36,0.7) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-dim) !important;
    font-weight: 500 !important;
}
.streamlit-expanderContent {
    background: rgba(10,16,28,0.6) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(13,20,36,0.6) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1px solid var(--border) !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: var(--text-muted) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(14,165,233,0.25), rgba(56,189,248,0.15)) !important;
    color: var(--sky) !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
}

/* ── Metric ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(19,29,48,0.9), rgba(13,20,36,0.95)) !important;
    border-radius: 14px !important;
    padding: 1rem 1.2rem !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stMetricValue"] { color: white !important; font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 0.75rem !important; }

/* ── Alert / Info boxes ── */
.stAlert {
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    background: rgba(13,20,36,0.8) !important;
}
div[data-testid="stNotification"] { border-radius: 12px !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: rgba(56,189,248,0.25); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue); }

/* ── Dividers ── */
hr { border-color: rgba(56,189,248,0.1) !important; }

/* ── Multiselect ── */
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(14,165,233,0.18) !important;
    border: 1px solid rgba(56,189,248,0.35) !important;
    color: var(--sky) !important;
    border-radius: 6px !important;
}
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ─────────────────────────── Components ──────────────────────────

def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def section_header(title: str):
    st.markdown(f'<div class="sec-hdr">{title}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", color: str = "#0EA5E9"):
    glow = color.replace("#", "")
    try:
        r = int(glow[0:2], 16)
        g = int(glow[2:4], 16)
        b = int(glow[4:6], 16)
        shadow = f"rgba({r},{g},{b},0.25)"
    except Exception:
        shadow = "rgba(14,165,233,0.25)"
    st.markdown(
        f"""<div class="kpi-card" style="border-top-color:{color};box-shadow:0 4px 24px rgba(0,0,0,0.4),0 0 20px {shadow},inset 0 1px 0 rgba(255,255,255,0.05);">
              <div class="val">{value}</div>
              <div class="lbl">{label}</div>
              {"<div class='sub'>" + sub + "</div>" if sub else ""}
            </div>""",
        unsafe_allow_html=True,
    )


def badge(status: str) -> str:
    cls_map = {
        "active":        "badge-active",
        "in_progress":   "badge-inprog",
        "ready_to_close":"badge-rtc",
        "closed":        "badge-closed",
        "completed":     "badge-pass",
        "audited":       "badge-pass",
        "pending":       "badge-pending",
    }
    cls = cls_map.get(status.lower().replace(" ", "_"), "badge-pending")
    return f'<span class="badge {cls}">{status.replace("_", " ")}</span>'


def priority_chip(priority: str) -> str:
    return f'<span class="pri pri-{priority}">{priority}</span>'


def progress_bar(value: int, total: int, color: str = "#27AE60") -> str:
    pct = int(value / total * 100) if total else 0
    return (
        f'<div class="prog-wrap"><div class="prog-fill" '
        f'style="width:{pct}%;background:{color};"></div></div>'
        f'<small style="color:#7F8C8D;">{value}/{total} ({pct}%)</small>'
    )


def info_banner(text: str, subtitle: str = ""):
    st.markdown(
        f'<div class="info-banner"><b>{text}</b>'
        + (f'<br><span style="font-size:0.85rem;color:#BDC3C7;">{subtitle}</span>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def finding_card(text: str, color: str = "#2980B9"):
    st.markdown(
        f'<div class="finding" style="border-left-color:{color};">🔹 {text}</div>',
        unsafe_allow_html=True,
    )


def nav(page: str, **kwargs):
    st.session_state["page"] = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()
