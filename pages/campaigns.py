"""
pages/campaigns.py — Campaign management: create, list, view progress, close.
"""
import streamlit as st
import plotly.graph_objects as go

from database.db_manager import (
    create_campaign, get_all_campaigns, get_campaign,
    get_campaign_progress, get_calls_for_campaign,
    get_failures_for_campaign, get_campaign_insights,
    close_campaign,
)
from database.models import CampaignStatus, STATUS_COLORS
from analytics.insight_engine import generate_campaign_insights
from utils import (
    page_header, section_header, kpi_card, badge, progress_bar,
    info_banner, nav, finding_card, priority_chip,
)

_GREEN = "#27AE60"
_RED   = "#E74C3C"
_AMBER = "#F39C12"
_BLUE  = "#2980B9"


def render():
    page_header("📋 Campaign Management", "Create and manage voice-bot audit campaigns")

    col_hdr, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("➕ New Campaign", type="primary", use_container_width=True):
            st.session_state["show_create_campaign"] = True

    # ── Create campaign form ──────────────────────────────────────
    if st.session_state.get("show_create_campaign"):
        with st.expander("🆕 Create New Campaign", expanded=True):
            with st.form("new_campaign_form"):
                name   = st.text_input("Campaign Name *", placeholder="e.g. Q2 2025 Lead Gen")
                client = st.text_input("Client Name *",   placeholder="e.g. TechSolutions Inc.")
                col1, col2 = st.columns(2)
                with col1:
                    ok = st.form_submit_button("✅ Create", type="primary", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)

                if ok:
                    if not name.strip() or not client.strip():
                        st.error("Both Campaign Name and Client Name are required.")
                    else:
                        cid = create_campaign(name.strip(), client.strip())
                        st.session_state["show_create_campaign"] = False
                        st.success(f"Campaign '{name}' created! (ID: {cid})")
                        st.rerun()
                if cancel:
                    st.session_state["show_create_campaign"] = False
                    st.rerun()

    st.markdown("---")

    # ── If a specific campaign is selected, show its detail ───────
    sel_id = st.session_state.get("selected_campaign_id")
    if sel_id:
        _render_campaign_detail(sel_id)
        if st.button("← Back to List"):
            st.session_state["selected_campaign_id"] = None
            st.rerun()
        return

    # ── Campaign list ─────────────────────────────────────────────
    campaigns = get_all_campaigns()
    tabs = st.tabs(["🟢 Active", "🔵 In Progress", "🟠 Ready to Close", "⬛ Closed", "📋 All"])
    status_groups = {
        0: CampaignStatus.ACTIVE.value,
        1: CampaignStatus.IN_PROGRESS.value,
        2: CampaignStatus.READY_TO_CLOSE.value,
        3: CampaignStatus.CLOSED.value,
        4: None,   # All
    }

    for tab_idx, tab in enumerate(tabs):
        filter_status = status_groups[tab_idx]
        filtered = [c for c in campaigns if filter_status is None or c["status"] == filter_status]

        with tab:
            if not filtered:
                st.info(f"No {'campaigns' if filter_status is None else filter_status.replace('_',' ').title() + ' campaigns'} found.")
                continue
            _render_campaign_table(filtered)


def _render_campaign_table(campaigns: list):
    for camp in campaigns:
        prog = get_campaign_progress(camp["campaign_id"])
        ins  = get_campaign_insights(camp["campaign_id"])
        avg_s = ins["avg_qa_score"] if ins else None

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1.5, 2.4, 1.4, 1.4, 1.4])
            with c1:
                st.markdown(f"**{camp['campaign_name']}**")
                st.caption(f"👤 {camp['client_name']} &nbsp;·&nbsp; 📅 {(camp.get('created_at') or '')[:10]}")
            with c2:
                st.markdown(badge(camp["status"]), unsafe_allow_html=True)
            with c3:
                st.markdown(progress_bar(prog["audited"], prog["total"]), unsafe_allow_html=True)
            with c4:
                if avg_s is not None:
                    color = _GREEN if avg_s >= 70 else _RED
                    st.markdown(
                        f"<b style='font-size:1.2rem;color:{color};'>{avg_s:.1f}%</b>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("—")
            with c5:
                if st.button("🔍 View", key=f"camp_view_{camp['campaign_id']}", use_container_width=True):
                    st.session_state["selected_campaign_id"] = camp["campaign_id"]
                    st.rerun()
            with c6:
                if camp["status"] == CampaignStatus.CLOSED.value:
                    if st.button("📊 Insights", key=f"camp_ins_{camp['campaign_id']}", use_container_width=True, type="primary"):
                        nav("insights", insights_campaign_id=camp["campaign_id"])
                elif camp["status"] == CampaignStatus.READY_TO_CLOSE.value:
                    if st.button("🔒 Close", key=f"camp_close_{camp['campaign_id']}", use_container_width=True, type="primary"):
                        st.session_state["confirm_close_id"] = camp["campaign_id"]
                        st.rerun()
                else:
                    if st.button("✍️ Audit", key=f"camp_aud_{camp['campaign_id']}", use_container_width=True):
                        nav("call_audit", selected_campaign_id=camp["campaign_id"])

        # Confirm close dialog
        if st.session_state.get("confirm_close_id") == camp["campaign_id"]:
            with st.expander("⚠️ Confirm Campaign Close", expanded=True):
                st.warning(
                    f"Close **{camp['campaign_name']}**? This will:\n"
                    "- Lock all audit entries\n"
                    "- Run the Bot Failure Intelligence Engine on all calls\n"
                    "- Auto-generate the full Campaign Insight Report\n\n"
                    "**This action cannot be undone.**"
                )
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ Yes, Close & Generate Insights", type="primary",
                                 key=f"confirm_yes_{camp['campaign_id']}", use_container_width=True):
                        with st.spinner("Running intelligence engine and generating insights..."):
                            close_campaign(camp["campaign_id"])
                            insights = generate_campaign_insights(camp["campaign_id"])
                        st.session_state["confirm_close_id"] = None
                        avg = insights.get("campaign_summary", {}).get("avg_qa_score", 0)
                        st.success(f"✅ Campaign closed! Avg QA score: **{avg:.1f}%**")
                        st.balloons()
                        st.session_state["insights_campaign_id"] = camp["campaign_id"]
                        nav("insights", insights_campaign_id=camp["campaign_id"])
                with cc2:
                    if st.button("Cancel", key=f"confirm_no_{camp['campaign_id']}", use_container_width=True):
                        st.session_state["confirm_close_id"] = None
                        st.rerun()

        st.divider()


def _render_campaign_detail(campaign_id: str):
    camp  = get_campaign(campaign_id)
    if not camp:
        st.error("Campaign not found.")
        return

    prog  = get_campaign_progress(campaign_id)
    calls = get_calls_for_campaign(campaign_id)
    fails = get_failures_for_campaign(campaign_id)
    ins   = get_campaign_insights(campaign_id)

    # ── Header banner ─────────────────────────────────────────────
    status_color = STATUS_COLORS.get(camp["status"], "#7F8C8D")
    st.markdown(
        f"""<div style="background:linear-gradient(90deg,#1C2833,#2C3E50);
            padding:1rem 1.5rem;border-radius:12px;margin-bottom:1rem;">
            <span style="color:#ECF0F1;font-size:1.3rem;font-weight:700;">
                {camp['campaign_name']}
            </span>
            <br><span style="color:#BDC3C7;font-size:0.82rem;">
                Client: {camp['client_name']} &nbsp;·&nbsp;
                Created: {(camp.get('created_at') or '')[:10]} &nbsp;·&nbsp;
                Status: <b style="color:{status_color}">{camp['status']}</b>
            </span></div>""",
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────────
    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    with kc1: kpi_card("Total Calls",   str(prog["total"]),   color=_BLUE)
    with kc2: kpi_card("Audited",       str(prog["audited"]), color=_GREEN)
    with kc3: kpi_card("Pending",       str(prog["pending"]), color=_AMBER if prog["pending"] else _GREEN)
    with kc4: kpi_card("Completion",    f"{prog['pct']:.0f}%", color=_BLUE)
    with kc5:
        avg_s = ins["avg_qa_score"] if ins else 0
        kpi_card("Avg QA Score", f"{avg_s:.1f}%" if avg_s else "—",
                 color=_GREEN if avg_s >= 70 else _RED)

    st.markdown(progress_bar(prog["audited"], prog["total"]), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────
    t_calls, t_fails, t_actions = st.tabs(["📞 Calls", "🤖 Bot Failures", "🎯 Action Plan"])

    with t_calls:
        section_header("Call List")
        if not calls:
            st.info("No calls in this campaign. Import calls first.")
        else:
            import pandas as pd
            rows = []
            for c in calls:
                audit_status = "Audited" if c.get("audit_id") else "Pending"
                rows.append({
                    "Call ID":     c["call_id"],
                    "Link":        c.get("call_link", "—")[:40],
                    "Duration":    f"{(c.get('duration') or 0) // 60}m {(c.get('duration') or 0) % 60}s",
                    "Date":        (c.get("timestamp") or "—")[:10],
                    "Lead":        c.get("lead_category", "UNKNOWN"),
                    "Status":      audit_status,
                    "Score":       f"{c['percentage_score']:.1f}%" if c.get("percentage_score") else "—",
                })
            df = pd.DataFrame(rows)
            filt = st.selectbox("Filter", ["All", "Audited", "Pending"], key="det_filter")
            if filt != "All":
                df = df[df["Status"] == filt]
            st.dataframe(df, use_container_width=True, hide_index=True)

    with t_fails:
        section_header("Detected Bot Failures")
        if not fails:
            st.info("No failures detected yet. Close the campaign to run the intelligence engine.")
        else:
            import pandas as pd
            df_f = pd.DataFrame(fails)[
                ["failure_type", "failure_reason", "confidence_score", "call_id"]
            ].rename(columns={
                "failure_type":     "Failure Type",
                "failure_reason":   "Reason",
                "confidence_score": "Confidence",
                "call_id":          "Call ID",
            })
            df_f["Confidence"] = df_f["Confidence"].map(lambda x: f"{x:.0%}")
            st.dataframe(df_f, use_container_width=True, hide_index=True)

    with t_actions:
        if ins and ins.get("insights_json"):
            plan = ins["insights_json"].get("action_plan", [])
            section_header("Prioritised Action Plan")
            if not plan:
                st.info("No recommendations generated.")
            else:
                for item in plan:
                    pri = item["priority"]
                    st.markdown(
                        f'{priority_chip(pri)} &nbsp; <b>{item["recommendation"]}</b> '
                        f'<span style="color:#7F8C8D;font-size:0.82rem;"> — {item.get("owner","")}'
                        f' ({item.get("timeline","")})</span>',
                        unsafe_allow_html=True,
                    )
                    for act in item.get("actions", [])[:3]:
                        st.markdown(f"  &nbsp;&nbsp;&nbsp;• {act}")
                    st.markdown("")
        else:
            st.info("Action plan available after campaign is closed.")

    # ── Close campaign button ─────────────────────────────────────
    if camp["status"] == CampaignStatus.READY_TO_CLOSE.value:
        st.markdown("---")
        st.success("✅ All calls audited — this campaign is ready to close.")
        if st.button("🔒 Close Campaign & Generate Insights", type="primary", use_container_width=True):
            with st.spinner("Running intelligence engine..."):
                close_campaign(campaign_id)
                generate_campaign_insights(campaign_id)
            st.balloons()
            nav("insights", insights_campaign_id=campaign_id)

    elif camp["status"] == CampaignStatus.IN_PROGRESS.value or camp["status"] == CampaignStatus.ACTIVE.value:
        st.markdown("---")
        st.warning(f"⏳ {prog['pending']} call(s) still pending audit before this campaign can be closed.")
        if st.button("✍️ Go to Audit Interface", use_container_width=True):
            nav("call_audit", selected_campaign_id=campaign_id)
