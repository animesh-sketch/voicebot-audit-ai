"""
utils.py — Shared UI helpers, CSS injection, and reusable Streamlit components.
"""
import streamlit as st


# ─────────────────────────── CSS ─────────────────────────────────

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B2A 0%, #1B2838 50%, #0D1B2A 100%) !important;
    border-right: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] * { color: #ECF0F1 !important; }
[data-testid="stSidebar"] hr { border-color: #1e3a5f !important; }

/* ── Nav buttons ── */
div.nav-link button {
    background: transparent !important;
    border: none !important;
    text-align: left !important;
    padding: 0.55rem 1rem !important;
    border-radius: 8px !important;
    width: 100% !important;
    font-size: 0.9rem !important;
    color: #CBD5E0 !important;
    transition: all 0.15s ease !important;
}
div.nav-link button:hover { background: rgba(41,128,185,0.2) !important; color: white !important; }
div.nav-active button {
    background: rgba(41,128,185,0.35) !important;
    border-left: 3px solid #2980B9 !important;
    color: white !important;
    font-weight: 600 !important;
}

/* ── KPI cards ── */
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    text-align: center;
    border-top: 4px solid #2980B9;
    height: 100%;
}
.kpi-card .val  { font-size: 2rem; font-weight: 700; color: #1C2833; line-height: 1.1; }
.kpi-card .lbl  { font-size: 0.75rem; color: #7F8C8D; margin-top: 5px;
                  text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-card .sub  { font-size: 0.78rem; color: #95A5A6; margin-top: 2px; }

/* ── Status badges ── */
.badge { display:inline-block; padding:3px 10px; border-radius:12px;
         font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; }
.badge-active  { background:#D5F5E3; color:#1E8449; }
.badge-inprog  { background:#D6EAF8; color:#1A5276; }
.badge-rtc     { background:#FDEBD0; color:#A04000; }
.badge-closed  { background:#EAECEE; color:#566573; }
.badge-pass    { background:#D5F5E3; color:#1E8449; }
.badge-fail    { background:#FADBD8; color:#922B21; }
.badge-pending { background:#EBF5FB; color:#1A5276; }

/* ── Priority chips ── */
.pri { display:inline-block; padding:2px 8px; border-radius:4px;
       font-size:0.7rem; font-weight:700; text-transform:uppercase; }
.pri-CRITICAL { background:#C0392B; color:white; }
.pri-HIGH     { background:#E74C3C; color:white; }
.pri-MEDIUM   { background:#F39C12; color:white; }
.pri-LOW      { background:#27AE60; color:white; }

/* ── Section header ── */
.sec-hdr {
    background: linear-gradient(90deg, #EBF5FB, #FDFEFE);
    border-left: 4px solid #2980B9;
    padding: 0.45rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.8rem 0 0.4rem 0;
    font-weight: 600;
    color: #1C2833;
    font-size: 0.95rem;
}

/* ── Page header ── */
.page-title { font-size: 1.65rem; font-weight: 700; color: #1C2833; }
.page-sub   { font-size: 0.88rem; color: #7F8C8D; margin-bottom: 1rem; }

/* ── Finding card ── */
.finding {
    background: white;
    border-left: 4px solid #2980B9;
    padding: 0.6rem 1rem;
    margin-bottom: 0.5rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.88rem;
    color: #2C3E50;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ── Progress bar ── */
.prog-wrap { background:#ECF0F1; border-radius:8px; height:16px; overflow:hidden; }
.prog-fill { height:100%; border-radius:8px; transition:width 0.3s; }

/* ── Info banner ── */
.info-banner {
    background: linear-gradient(90deg, #1B2838, #2C3E50);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    color: #ECF0F1;
    margin-bottom: 1rem;
}

/* ── Table tweaks ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── Failure badge colors ── */
.fail-tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.7rem;
            font-weight:600; margin:1px; }
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


def kpi_card(label: str, value: str, sub: str = "", color: str = "#2980B9"):
    st.markdown(
        f"""<div class="kpi-card" style="border-top-color:{color};">
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
