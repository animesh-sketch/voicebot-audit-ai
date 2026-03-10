"""
app.py — VoiceBot Audit AI | Main Streamlit Entry Point
Handles navigation, session state, and page routing.
"""
import os
import sys

# ── Ensure project root is on sys.path for submodule imports ─────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from database.db_manager import init_db, get_platform_stats
from utils import inject_css, nav

# ── Page imports ─────────────────────────────────────────────────
from pages import dashboard, campaigns, call_import, audit_template, call_audit, insights

# ─────────────────────────── App Config ──────────────────────────

st.set_page_config(
    page_title="VoiceBot Audit AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


# ─────────────────────────── Session Init ────────────────────────

def _init_state():
    defaults = {
        "page":                  "dashboard",
        "selected_campaign_id":  None,
        "audit_call_id":         None,
        "insights_campaign_id":  None,
        "show_create_campaign":  False,
        "confirm_close_id":      None,
        "auditor_name":          "QA Auditor",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────── Sidebar ─────────────────────────────

def _render_sidebar():
    with st.sidebar:
        # ── Brand header ──────────────────────────────────────────
        st.markdown(
            """<div style="text-align:center;padding:1.2rem 0 0.8rem;">
                <div style="font-size:2.5rem;">🎙️</div>
                <div style="font-size:1.1rem;font-weight:700;color:white;margin-top:4px;">
                    VoiceBot Audit AI
                </div>
                <div style="font-size:0.72rem;color:#7F8C8D;margin-top:2px;">
                    Campaign Intelligence Platform
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown('<hr style="border-color:#1e3a5f;margin:0.5rem 0;">', unsafe_allow_html=True)

        # ── Navigation ────────────────────────────────────────────
        current = st.session_state.get("page", "dashboard")

        nav_items = [
            ("dashboard",      "🏠", "Dashboard"),
            ("campaigns",      "📋", "Campaigns"),
            ("call_import",    "📥", "Import Calls"),
            ("audit_template", "📝", "Audit Templates"),
            ("call_audit",     "✍️", "Call Auditing"),
            ("insights",       "📊", "Insights & Reports"),
        ]

        for key, icon, label in nav_items:
            is_active = current == key
            wrapper_cls = "nav-active" if is_active else "nav-link"
            st.markdown(f'<div class="{wrapper_cls}">', unsafe_allow_html=True)
            if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                nav(key)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#1e3a5f;margin:0.8rem 0;">', unsafe_allow_html=True)

        # ── Live platform stats ───────────────────────────────────
        try:
            stats = get_platform_stats()
            st.markdown(
                f"""<div style="padding:0 0.5rem;font-size:0.78rem;color:#95A5A6;">
                    <div style="margin-bottom:6px;">
                        <span style="color:#ECF0F1;">📋 Campaigns:</span>
                        <b style="color:#27AE60;float:right;">{stats['campaigns']}</b>
                    </div>
                    <div style="margin-bottom:6px;">
                        <span style="color:#ECF0F1;">📞 Total Calls:</span>
                        <b style="color:#2980B9;float:right;">{stats['total_calls']}</b>
                    </div>
                    <div style="margin-bottom:6px;">
                        <span style="color:#ECF0F1;">✅ Audited:</span>
                        <b style="color:#27AE60;float:right;">{stats['audited']}</b>
                    </div>
                    <div style="margin-bottom:6px;">
                        <span style="color:#ECF0F1;">🤖 Failures:</span>
                        <b style="color:#E74C3C;float:right;">{stats['failures']}</b>
                    </div>
                    <div>
                        <span style="color:#ECF0F1;">📈 Avg Score:</span>
                        <b style="color:{'#27AE60' if stats['avg_score'] >= 70 else '#E74C3C'};float:right;">
                            {stats['avg_score']:.1f}%
                        </b>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        except Exception:
            pass

        st.markdown('<hr style="border-color:#1e3a5f;margin:0.8rem 0;">', unsafe_allow_html=True)

        # ── Seed data button (dev helper) ─────────────────────────
        with st.expander("🔧 Dev Tools"):
            if st.button("🌱 Load Demo Data", use_container_width=True):
                with st.spinner("Seeding demo data..."):
                    try:
                        import subprocess
                        result = subprocess.run(
                            [sys.executable, "seed_data.py"],
                            capture_output=True, text=True,
                            cwd=os.path.dirname(os.path.abspath(__file__))
                        )
                        if result.returncode == 0:
                            st.success("Demo data loaded!")
                            st.rerun()
                        else:
                            st.error(result.stderr[:200])
                    except Exception as e:
                        st.error(str(e))

            if st.button("🗑️ Reset Database", use_container_width=True):
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voicebot_audit.db")
                if os.path.exists(db_path):
                    os.remove(db_path)
                init_db()
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.success("Database reset!")
                st.rerun()

        st.markdown(
            '<div style="position:absolute;bottom:1rem;left:0;right:0;text-align:center;'
            'font-size:0.7rem;color:#4A5568;">v1.0.0 · VoiceBot Audit AI</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────── Router ──────────────────────────────

_PAGE_MAP = {
    "dashboard":      dashboard.render,
    "campaigns":      campaigns.render,
    "call_import":    call_import.render,
    "audit_template": audit_template.render,
    "call_audit":     call_audit.render,
    "insights":       insights.render,
}


def main():
    inject_css()
    _init_state()
    _render_sidebar()

    page = st.session_state.get("page", "dashboard")
    renderer = _PAGE_MAP.get(page, dashboard.render)

    try:
        renderer()
    except Exception as e:
        st.error(f"Page error: {e}")
        import traceback
        with st.expander("Stack trace"):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
