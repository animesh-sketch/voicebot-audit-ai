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
            """<div style="text-align:center;padding:1.4rem 0 1rem;">
                <div style="font-size:2.6rem;filter:drop-shadow(0 0 12px rgba(14,165,233,0.6));">🎙️</div>
                <div style="font-size:1.05rem;font-weight:800;margin-top:8px;
                            font-family:'Outfit',sans-serif;letter-spacing:0.02em;
                            background:linear-gradient(135deg,#ffffff,#38BDF8,#0EA5E9);
                            -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    AuditSense AI
                </div>
                <div style="font-size:0.68rem;color:#475569;margin-top:3px;letter-spacing:0.08em;text-transform:uppercase;">
                    Campaign Intelligence Platform
                </div>
                <div style="margin-top:10px;height:2px;
                            background:linear-gradient(90deg,transparent,#0EA5E9,#38BDF8,#F472B6,transparent);
                            border-radius:2px;opacity:0.6;">
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown('<hr style="border-color:rgba(56,189,248,0.1);margin:0.4rem 0;">', unsafe_allow_html=True)

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

        st.markdown('<hr style="border-color:rgba(56,189,248,0.1);margin:0.8rem 0;">', unsafe_allow_html=True)

        # ── Live platform stats ───────────────────────────────────
        try:
            stats = get_platform_stats()
            score_color = "#00D68F" if stats['avg_score'] >= 70 else "#F472B6"
            st.markdown(
                f"""<div style="padding:0 0.3rem;">
                    <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.1em;
                                color:#475569;margin-bottom:8px;font-weight:600;">Platform Stats</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                margin-bottom:6px;padding:4px 0;">
                        <span style="font-size:0.78rem;color:#64748B;">📋 Campaigns</span>
                        <b style="color:#38BDF8;font-size:0.82rem;">{stats['campaigns']}</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                margin-bottom:6px;padding:4px 0;">
                        <span style="font-size:0.78rem;color:#64748B;">📞 Total Calls</span>
                        <b style="color:#0EA5E9;font-size:0.82rem;">{stats['total_calls']}</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                margin-bottom:6px;padding:4px 0;">
                        <span style="font-size:0.78rem;color:#64748B;">✅ Audited</span>
                        <b style="color:#00D68F;font-size:0.82rem;">{stats['audited']}</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                margin-bottom:6px;padding:4px 0;">
                        <span style="font-size:0.78rem;color:#64748B;">🤖 Failures</span>
                        <b style="color:#F472B6;font-size:0.82rem;">{stats['failures']}</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                padding:5px 8px;border-radius:8px;
                                background:rgba(14,165,233,0.07);border:1px solid rgba(56,189,248,0.12);">
                        <span style="font-size:0.78rem;color:#94A3B8;">📈 Avg Score</span>
                        <b style="color:{score_color};font-size:0.88rem;">{stats['avg_score']:.1f}%</b>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        except Exception:
            pass

        st.markdown('<hr style="border-color:rgba(56,189,248,0.1);margin:0.8rem 0;">', unsafe_allow_html=True)

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
            '<div style="position:absolute;bottom:1rem;left:0;right:0;text-align:center;">'
            '<span style="font-size:0.65rem;color:#334155;letter-spacing:0.08em;">v1.0.0 · </span>'
            '<span style="font-size:0.65rem;background:linear-gradient(90deg,#38BDF8,#F472B6);'
            '-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:600;">AuditSense AI</span>'
            '</div>',
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
