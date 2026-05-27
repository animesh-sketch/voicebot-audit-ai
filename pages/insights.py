"""
pages/insights.py — Campaign Insights Dashboard.
Interactive analytics, failure intelligence, conversation funnel,
action plan, and PDF report download.
"""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from database.db_manager import (
    get_all_campaigns, get_campaign, get_campaign_insights,
    get_campaign_progress, get_calls_for_campaign,
    close_campaign, get_failures_for_campaign,
)
from database.models import (
    CampaignStatus, FAILURE_TYPE_COLORS, LEAD_CATEGORY_COLORS, STATUS_COLORS,
)
from analytics.insight_engine import generate_campaign_insights
from reports.report_generator import generate_pdf_report
from utils import (
    page_header, section_header, kpi_card, badge, progress_bar,
    info_banner, nav, finding_card, priority_chip,
)

_BG    = "#F4F6F9"
_DARK  = "#1C2833"
_BLUE  = "#2980B9"
_GREEN = "#27AE60"
_RED   = "#E74C3C"
_AMBER = "#F39C12"


def _layout(title="", h=380):
    return dict(
        title=dict(text=title, font=dict(size=13, color=_DARK)),
        paper_bgcolor="white", plot_bgcolor=_BG,
        height=h, margin=dict(l=40, r=20, t=40, b=30),
        font=dict(family="Inter, sans-serif", size=11),
    )


def render():
    page_header("📊 Campaign Insights & Reports",
                "Close campaigns, explore AI-powered insights, and download PDF reports")

    tab_close, tab_view = st.tabs(["🔒 Close Campaign", "📈 View Insights"])

    # ── Tab 1: Close Campaign ─────────────────────────────────────
    with tab_close:
        _render_close_tab()

    # ── Tab 2: View Insights ──────────────────────────────────────
    with tab_view:
        _render_insights_tab()


# ─────────────────────────── Close Tab ───────────────────────────

def _render_close_tab():
    active = [c for c in get_all_campaigns() if c["status"] != CampaignStatus.CLOSED.value]
    if not active:
        info_banner("All campaigns are already closed", "Create a new campaign to continue auditing.")
        return

    camp_opts = {f"{c['campaign_name']}": c["campaign_id"] for c in active}
    chosen    = st.selectbox("Select Campaign to Close", list(camp_opts.keys()), key="close_sel")
    camp_id   = camp_opts[chosen]
    campaign  = get_campaign(camp_id)
    prog      = get_campaign_progress(camp_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Calls", str(prog["total"]), color=_BLUE)
    with c2: kpi_card("Audited",     str(prog["audited"]), color=_GREEN)
    with c3: kpi_card("Pending",     str(prog["pending"]), color=_RED if prog["pending"] else _GREEN)
    with c4:
        pct = prog["pct"]
        kpi_card("Completion", f"{pct:.0f}%", color=_GREEN if pct == 100 else _AMBER)

    st.markdown(progress_bar(prog["audited"], prog["total"]), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if prog["total"] == 0:
        st.warning("No calls imported yet. Import calls before closing.")
        if st.button("📥 Import Calls"):
            nav("call_import", selected_campaign_id=camp_id)
    elif prog["pending"] > 0:
        st.error(
            f"⛔ **{prog['pending']} call(s) still pending audit.** "
            "All calls must be audited before closing."
        )
        st.markdown(
            f'<div style="background:#FADBD8;border-left:4px solid #E74C3C;'
            f'padding:0.7rem 1rem;border-radius:0 8px 8px 0;">'
            f'<b>Pending calls:</b> {prog["pending"]} &nbsp;·&nbsp; '
            f'Audited: {prog["audited"]}/{prog["total"]}</div>',
            unsafe_allow_html=True,
        )
        if st.button("✍️ Go to Audit Interface →"):
            nav("call_audit", selected_campaign_id=camp_id)
    else:
        st.success("✅ All calls audited — campaign is **Ready to Close**.")
        with st.expander("ℹ️ What happens when you close a campaign?", expanded=True):
            st.markdown("""
            | Step | Action |
            |------|--------|
            | 1 | Campaign status → **CLOSED** (audit entries locked) |
            | 2 | **Bot Failure Intelligence Engine** runs on all transcripts |
            | 3 | **Analytics Engine** computes QA scores, failure rates, lead stats |
            | 4 | **Action Plan Generator** produces prioritised recommendations |
            | 5 | Full **Campaign Insight Report** saved and available for download |
            """)
        if st.button(
            f"🔒 Close Campaign & Run Intelligence Engine — \"{campaign['campaign_name']}\"",
            type="primary", use_container_width=True,
        ):
            with st.spinner("🧠 Running Bot Failure Intelligence Engine..."):
                close_campaign(camp_id)
            with st.spinner("📊 Computing analytics and generating insights..."):
                insights = generate_campaign_insights(camp_id)
            avg = insights.get("campaign_summary", {}).get("avg_qa_score", 0)
            failures = insights.get("campaign_summary", {}).get("total_failures", 0)
            st.success(
                f"✅ Campaign closed successfully!\n\n"
                f"**Avg QA Score:** {avg:.1f}%  ·  **Bot Failures Detected:** {failures}"
            )
            st.balloons()
            st.session_state["insights_campaign_id"] = camp_id
            nav("insights", insights_campaign_id=camp_id)


# ─────────────────────────── Insights Tab ────────────────────────

def _render_insights_tab():
    closed = [c for c in get_all_campaigns() if c["status"] == CampaignStatus.CLOSED.value]
    if not closed:
        info_banner("No closed campaigns yet",
                    "Close a campaign to generate insight reports.")
        return

    camp_opts = {
        f"{c['campaign_name']} (closed)": c["campaign_id"]
        for c in closed
    }
    presel = st.session_state.get("insights_campaign_id")
    default_idx = 0
    if presel:
        vals = list(camp_opts.values())
        if presel in vals:
            default_idx = vals.index(presel)

    chosen  = st.selectbox("Select Campaign", list(camp_opts.keys()), index=default_idx, key="ins_sel")
    camp_id = camp_opts[chosen]
    st.session_state["insights_campaign_id"] = camp_id
    campaign = get_campaign(camp_id)

    ins_row = get_campaign_insights(camp_id)
    if not ins_row or not ins_row.get("insights_json"):
        with st.spinner("Generating insights..."):
            generate_campaign_insights(camp_id)
            st.rerun()

    ins     = ins_row["insights_json"]
    summary = ins.get("campaign_summary", {})
    qa      = ins.get("qa_analysis", {})
    fails   = ins.get("failure_analysis", {})
    leads   = ins.get("lead_classification", {})
    conv    = ins.get("conversation_analysis", {})
    entity  = ins.get("entity_accuracy", {})
    plan    = ins.get("action_plan", [])
    gen_at  = ins.get("generated_at", "")

    # ── Header banner ─────────────────────────────────────────────
    st.markdown(
        f"""<div style="background:linear-gradient(90deg,#0D1B2A,#1B2838);
            padding:1.1rem 1.5rem;border-radius:12px;margin-bottom:1rem;">
            <span style="color:white;font-size:1.3rem;font-weight:700;">
                {summary.get('campaign_name','')}
            </span>
            <span style="color:#F39C12;font-size:0.8rem;font-weight:700;
                background:rgba(243,156,18,0.15);padding:2px 8px;border-radius:4px;
                margin-left:10px;">CLOSED</span>
            <br><span style="color:#BDC3C7;font-size:0.82rem;">
                Client: {summary.get('client_name','')} &nbsp;·&nbsp;
                Report: {gen_at}
            </span></div>""",
        unsafe_allow_html=True,
    )

    # ── KPI row ───────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    avg_s = summary.get("avg_qa_score", 0)
    pr    = summary.get("pass_rate", 0)
    with k1: kpi_card("Total Calls",   str(summary.get("total_calls", "—")), color=_BLUE)
    with k2: kpi_card("Audited",       str(summary.get("audited_calls", "—")), color=_GREEN)
    with k3: kpi_card("Avg QA Score",  f"{avg_s:.1f}%",
                      color=_GREEN if avg_s >= 70 else _RED)
    with k4: kpi_card("Pass Rate",     f"{pr:.1f}%",
                      color=_GREEN if pr >= 70 else _RED)
    with k5: kpi_card("Bot Failures",  str(summary.get("total_failures", "—")), color=_AMBER)
    with k6: kpi_card("Failure Rate",  f"{summary.get('failure_rate', 0) * 100:.0f}%",
                      color=_RED if summary.get("failure_rate", 0) > 0.3 else _AMBER)

    issue_analysis = ins.get("issue_analysis", {})

    # ── Insights sub-tabs ─────────────────────────────────────────
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📈 QA Scores", "🤖 Bot Failures", "🎯 Lead Analysis",
        "💬 Conversation", "🏷️ Issue Tags", "🎯 Action Plan", "📄 Download Report",
    ])

    # ── QA Scores ────────────────────────────────────────────────
    with t1:
        _render_qa_tab(qa, qa.get("score_distribution", {}))

    # ── Bot Failures ──────────────────────────────────────────────
    with t2:
        _render_failure_tab(fails)

    # ── Lead Analysis ─────────────────────────────────────────────
    with t3:
        _render_lead_tab(leads, entity)

    # ── Conversation ──────────────────────────────────────────────
    with t4:
        _render_conversation_tab(conv)

    # ── Issue Tags ────────────────────────────────────────────────
    with t5:
        _render_issue_tag_tab(issue_analysis)

    # ── Action Plan ───────────────────────────────────────────────
    with t6:
        _render_action_plan(plan)

    # ── Download Report ───────────────────────────────────────────
    with t7:
        _render_report_tab(campaign, ins)


# ─────────────────────────── Sub-renderers ───────────────────────

def _render_qa_tab(qa: dict, dist: dict):
    section_header("📈 QA Score Analysis")
    avg = qa.get("avg_score", 0)

    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1: kpi_card("Average Score",    f"{avg:.1f}%",             color=_GREEN if avg >= 70 else _RED)
    with qa2: kpi_card("Min Score",        f"{qa.get('min_score',0):.1f}%", color=_RED)
    with qa3: kpi_card("Max Score",        f"{qa.get('max_score',0):.1f}%", color=_GREEN)
    with qa4: kpi_card("Pass Rate (≥70%)", f"{qa.get('pass_rate',0):.1f}%",
                       color=_GREEN if qa.get("pass_rate", 0) >= 70 else _RED)

    if dist:
        st.markdown("")
        labels = list(dist.keys())
        counts = [int(dist[l]) for l in labels]
        bar_cols = [_RED, _AMBER, _AMBER, _GREEN, _GREEN][:len(labels)]
        fig = go.Figure(go.Bar(
            x=labels, y=counts,
            marker_color=bar_cols,
            text=counts, textposition="outside",
            hovertemplate="Score band: %{x}<br>Calls: %{y}<extra></extra>",
        ))
        fig.update_layout(**_layout("QA Score Distribution", 360))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    fields = qa.get("field_breakdown", [])
    if fields:
        section_header("📊 Field Breakdown")
        df = pd.DataFrame(fields).sort_values("percentage")
        bar_c = [_GREEN if p >= 70 else _RED for p in df["percentage"]]
        fig2 = go.Figure(go.Bar(
            x=df["percentage"], y=df["field_name"],
            orientation="h",
            marker_color=bar_c,
            text=[f"{p:.0f}%" for p in df["percentage"]],
            textposition="inside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig2.add_vline(x=70, line_dash="dash", line_color=_AMBER,
                       annotation_text="70% threshold", annotation_font_color=_AMBER)
        fig2.update_layout(**_layout("", max(320, 60 + len(df) * 45)), xaxis_range=[0, 108])
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # Table
        df_show = df[["field_name", "avg_score", "max_score", "percentage"]].copy()
        df_show.columns = ["Field", "Avg Score", "Max Score", "Score %"]
        df_show["Score %"] = df_show["Score %"].map(lambda x: f"{x:.1f}%")
        st.dataframe(df_show, use_container_width=True, hide_index=True)


def _render_failure_tab(fails: dict):
    section_header("🤖 Bot Failure Intelligence")

    f1, f2, f3 = st.columns(3)
    with f1: kpi_card("Total Failures",     str(fails.get("total_failures", 0)), color=_RED)
    with f2: kpi_card("Calls Affected",     str(fails.get("total_unique_failure_calls", 0)), color=_AMBER)
    with f3: kpi_card("Avg Confidence",     f"{fails.get('avg_confidence', 0):.0%}", color=_BLUE)

    dist = fails.get("failure_distribution", {})
    if dist:
        st.markdown("")
        short_labels = [k.replace(" Failure", "").replace(" Detection", "") for k in dist]
        bar_colors   = [FAILURE_TYPE_COLORS.get(k, "#95A5A6") for k in dist]
        fig = go.Figure(go.Bar(
            x=short_labels, y=list(dist.values()),
            marker_color=bar_colors,
            text=list(dist.values()), textposition="outside",
            hovertemplate="%{x}: %{y} occurrences<extra></extra>",
        ))
        fig.update_layout(**_layout("Failure Distribution", 360))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Failure rates table
        section_header("📊 Failure Rates (% of calls)")
        rates = fails.get("failure_rates", {})
        df_f = pd.DataFrame([
            {
                "Failure Type": ft,
                "Count": dist.get(ft, 0),
                "Call Rate": f"{rates.get(ft, 0) * 100:.1f}%",
                "Severity": "🔴 Critical" if rates.get(ft, 0) >= 0.3
                             else "🟠 High" if rates.get(ft, 0) >= 0.15
                             else "🟡 Medium",
            }
            for ft in sorted(dist, key=lambda x: -dist[x])
        ])
        st.dataframe(df_f, use_container_width=True, hide_index=True)

    top = fails.get("top_failures", [])
    if top:
        section_header("🔍 Top Detected Failure Instances")
        for f in top:
            color = FAILURE_TYPE_COLORS.get(f["failure_type"], "#7F8C8D")
            st.markdown(
                f'<div style="background:white;border-left:4px solid {color};'
                f'padding:0.5rem 1rem;border-radius:0 8px 8px 0;margin:4px 0;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.05);">'
                f'<b style="color:{color};">{f["failure_type"]}</b> '
                f'<code style="font-size:0.75rem;">{f["call_id"]}</code> '
                f'<span style="float:right;color:#7F8C8D;">{f["confidence_score"]:.0%} confidence</span><br>'
                f'<span style="font-size:0.87rem;">{f["failure_reason"]}</span></div>',
                unsafe_allow_html=True,
            )
    elif not dist:
        st.info("No bot failures detected. Great job!")


def _render_lead_tab(leads: dict, entity: dict):
    section_header("🎯 Lead Classification Analysis")
    mismatch_rate = leads.get("mismatch_rate", 0)
    l1, l2, l3, l4 = st.columns(4)
    with l1: kpi_card("Total Calls",    str(leads.get("total", 0)), color=_BLUE)
    with l2: kpi_card("Hot Lead Rate",  f"{leads.get('hot_lead_rate', 0) * 100:.0f}%", color=_RED)
    with l3: kpi_card("Entity Capture", f"{entity.get('capture_rate', 0) * 100:.0f}%",
                      color=_GREEN if entity.get("capture_rate", 0) >= 0.7 else _AMBER)
    with l4: kpi_card("Lead Mismatch",  f"{mismatch_rate * 100:.0f}%",
                      color=_RED if mismatch_rate > 0.20 else _GREEN)

    dist = leads.get("distribution", {})
    col_pie, col_bar = st.columns(2)
    with col_pie:
        if dist:
            fig = go.Figure(go.Pie(
                labels=list(dist.keys()),
                values=list(dist.values()),
                hole=0.45,
                marker_colors=[LEAD_CATEGORY_COLORS.get(k, "#95A5A6") for k in dist],
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}<extra></extra>",
            ))
            fig.update_layout(**_layout("Lead Category Distribution", 340),
                              showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_bar:
        if dist:
            sorted_dist = sorted(dist.items(), key=lambda x: -x[1])
            fig2 = go.Figure(go.Bar(
                x=[v for _, v in sorted_dist],
                y=[k for k, _ in sorted_dist],
                orientation="h",
                marker_color=[LEAD_CATEGORY_COLORS.get(k, "#95A5A6") for k, _ in sorted_dist],
                text=[v for _, v in sorted_dist],
                textposition="outside",
            ))
            fig2.update_layout(**_layout("Lead Counts", 340), xaxis_title="Count")
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Entity capture per-field breakdown ────────────────────────
    entity_breakdown = entity.get("field_breakdown", [])
    if entity_breakdown:
        section_header("📦 Entity Capture Accuracy — Per Field")
        e1, e2 = st.columns(2)
        with e1:
            df_ent = pd.DataFrame(entity_breakdown).sort_values("percentage")
            bar_c  = [_GREEN if p >= 70 else _AMBER if p >= 50 else _RED for p in df_ent["percentage"]]
            fig_e = go.Figure(go.Bar(
                x=df_ent["percentage"], y=df_ent["field_name"],
                orientation="h", marker_color=bar_c,
                text=[f"{p:.0f}%" for p in df_ent["percentage"]],
                textposition="inside",
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            ))
            fig_e.add_vline(x=70, line_dash="dash", line_color=_AMBER,
                            annotation_text="70% target")
            fig_e.update_layout(**_layout("Entity Field Capture Rates", max(280, 60 + len(df_ent) * 45)),
                                xaxis_range=[0, 108])
            st.plotly_chart(fig_e, use_container_width=True, config={"displayModeBar": False})
        with e2:
            df_show = pd.DataFrame(entity_breakdown).sort_values("percentage", ascending=False)
            df_show["Score %"] = df_show["percentage"].map(lambda x: f"{x:.1f}%")
            st.dataframe(
                df_show[["field_name", "avg_score", "max_score", "Score %", "count"]].rename(columns={
                    "field_name": "Entity Field", "avg_score": "Avg Score",
                    "max_score": "Max Score", "count": "Audits",
                }),
                use_container_width=True, hide_index=True,
            )

    # ── Lead classification mismatch details ──────────────────────
    mismatch_pairs = leads.get("mismatch_pairs", [])
    if mismatch_pairs:
        section_header(f"⚠️ Lead Classification Mismatches — {leads.get('mismatch_count', 0)} calls")
        st.markdown(
            f"Bot and auditor disagreed on **{mismatch_rate * 100:.0f}%** of assessed calls. "
            "Use these to retrain your lead classification model."
        )
        df_mm = pd.DataFrame(mismatch_pairs).rename(columns={
            "call_id": "Call ID", "bot_label": "Bot Classification", "audit_label": "Auditor Assessment",
        })
        st.dataframe(df_mm, use_container_width=True, hide_index=True)


def _render_issue_tag_tab(issue_analysis: dict):
    section_header("🏷️ Issue Tag Analysis")
    if not issue_analysis:
        st.info("No issue tag data available.")
        return

    tagged = issue_analysis.get("total_tagged_calls", 0)
    dist   = issue_analysis.get("tag_distribution", {})

    it1, it2 = st.columns(2)
    with it1: kpi_card("Calls with Issues", str(tagged), color=_AMBER)
    with it2: kpi_card("Distinct Issue Types", str(len(dist)), color=_BLUE)

    if not dist:
        st.info("No issues were tagged in this campaign.")
        return

    st.markdown("")
    _TAG_COLORS = {
        "Latency":                  _AMBER,
        "Hallucination":            _RED,
        "STT Error":                "#8E44AD",
        "Intent Misclassification": _BLUE,
        "Conversation Drop":        "#E67E22",
        "Language Switch":          "#16A085",
    }

    sorted_dist = sorted(dist.items(), key=lambda x: -x[1])

    col_chart, col_table = st.columns(2)
    with col_chart:
        bar_colors = [_TAG_COLORS.get(k, "#95A5A6") for k, _ in sorted_dist]
        fig = go.Figure(go.Bar(
            x=[k for k, _ in sorted_dist],
            y=[v for _, v in sorted_dist],
            marker_color=bar_colors,
            text=[v for _, v in sorted_dist],
            textposition="outside",
            hovertemplate="%{x}: %{y} calls<extra></extra>",
        ))
        fig.update_layout(**_layout("Issue Tag Distribution", 360))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_table:
        total_tags = sum(v for _, v in sorted_dist)
        df_tags = pd.DataFrame([
            {
                "Issue Tag":  k,
                "Count":      v,
                "% of Tagged Calls": f"{v / tagged * 100:.0f}%" if tagged else "—",
            }
            for k, v in sorted_dist
        ])
        st.dataframe(df_tags, use_container_width=True, hide_index=True)

    # Root cause summary for high-frequency tags
    section_header("🔍 Root Cause Summary")
    _ROOT_CAUSE_HINTS = {
        "Latency":                  "High latency signals slow NLU/TTS pipelines or network issues. Profile pipeline stages and enable response streaming.",
        "Hallucination":            "Bot provided incorrect information. Audit and constrain the knowledge base; add confidence gating on all factual responses.",
        "STT Error":                "Speech-to-text transcription failures detected. Review STT model accuracy on this domain's vocabulary and accents.",
        "Intent Misclassification": "Bot misunderstood customer intent multiple times. Add training utterances for misclassified intents and introduce clarification turns.",
        "Conversation Drop":        "Calls ended abruptly without resolution. Instrument drop points and add re-engagement and graceful handoff logic.",
        "Language Switch":          "Customer attempted to switch language but bot did not handle it. Enable automatic language detection and escalation to bilingual agents.",
    }
    for tag, count in sorted_dist:
        hint = _ROOT_CAUSE_HINTS.get(tag, "Review calls tagged with this issue for patterns.")
        color = _TAG_COLORS.get(tag, "#95A5A6")
        st.markdown(
            f'<div style="background:white;border-left:4px solid {color};'
            f'padding:0.5rem 1rem;border-radius:0 8px 8px 0;margin:4px 0;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.05);">'
            f'<b style="color:{color};">🏷️ {tag}</b> '
            f'<span style="color:#7F8C8D;font-size:0.78rem;">({count} call{"s" if count != 1 else ""})</span><br>'
            f'<span style="font-size:0.87rem;">{hint}</span></div>',
            unsafe_allow_html=True,
        )


def _render_conversation_tab(conv: dict):
    section_header("💬 Conversation Flow Analysis")
    cv1, cv2, cv3, cv4 = st.columns(4)
    with cv1: kpi_card("Avg Duration",   f"{conv.get('avg_duration', 0):.0f}s", color=_BLUE)
    with cv2: kpi_card("Short Calls",    str(conv.get("short_calls", 0)), color=_AMBER)
    with cv3: kpi_card("Conv Drops",     str(conv.get("conversation_drops", 0)), color=_RED)
    with cv4: kpi_card("Drop Rate",      f"{conv.get('drop_rate', 0) * 100:.0f}%",
                       color=_RED if conv.get("drop_rate", 0) > 0.2 else _GREEN)

    dur_dist = conv.get("duration_distribution", {})
    if dur_dist:
        labels = list(dur_dist.keys())
        values = [int(dur_dist[l]) for l in labels]
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker_color=_BLUE,
            text=values, textposition="outside",
            hovertemplate="%{x}: %{y} calls<extra></extra>",
        ))
        fig.update_layout(**_layout("Call Duration Distribution", 340), yaxis_title="Calls")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Drop-off funnel (simplified)
    if conv.get("total_calls", 0) or dur_dist:
        total = sum(values) if dur_dist else 1
        drop  = conv.get("conversation_drops", 0)
        completed = total - drop
        fig2 = go.Figure(go.Funnel(
            y=["Calls Initiated", "Completed Conversations", "Calls with Bot Failures", "Clean Calls"],
            x=[total, completed, max(total - completed, 0), max(completed - drop, 0)],
            marker_color=[_BLUE, _GREEN, _AMBER, _GREEN],
        ))
        fig2.update_layout(**_layout("Conversation Drop-off Funnel", 320))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})


def _render_action_plan(plan: list):
    section_header("🎯 Prioritised Action Plan")
    if not plan:
        st.info("No action items generated.")
        return

    # Summary table
    df_plan = pd.DataFrame([
        {
            "Priority":       item["priority"],
            "Category":       item["category"],
            "Finding":        item["finding"][:70] + ("…" if len(item["finding"]) > 70 else ""),
            "Recommendation": item["recommendation"][:70],
            "Owner":          item.get("owner", "—"),
            "Timeline":       item.get("timeline", "—"),
        }
        for item in plan
    ])

    def style_pri(val):
        colors = {"CRITICAL": "#C0392B", "HIGH": "#E74C3C", "MEDIUM": "#F39C12", "LOW": "#27AE60"}
        c = colors.get(val, "#7F8C8D")
        return f"background-color:{c};color:white;font-weight:bold;border-radius:4px;padding:2px 6px;"

    st.dataframe(df_plan.style.applymap(style_pri, subset=["Priority"]),
                 use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📝 Detailed Action Items")

    for item in plan:
        pri   = item["priority"]
        pri_c = {"CRITICAL": "#C0392B", "HIGH": "#E74C3C", "MEDIUM": "#F39C12", "LOW": "#27AE60"}.get(pri, "#7F8C8D")
        with st.expander(
            f"{priority_chip(pri)} {item['recommendation']}  "
            f"— {item.get('owner','')} ({item.get('timeline','')})",
            expanded=(pri in ("CRITICAL", "HIGH")),
        ):
            st.markdown(f"**Finding:** {item['finding']}")
            st.markdown(f"**Expected Impact:** {item.get('expected_impact','')}")
            st.markdown("**Steps:**")
            for act in item.get("actions", []):
                st.markdown(f"  - {act}")


def _render_report_tab(campaign: dict, ins: dict):
    section_header("📄 Download Campaign PDF Report")
    st.markdown(
        "The PDF report includes: **Cover page**, **Campaign Summary**, "
        "**QA Score Analysis**, **Bot Failure Analysis**, **Entity & Lead Stats**, "
        "**Conversation Analysis**, and the full **Action Plan**."
    )
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("📥 Generate PDF Report", type="primary", use_container_width=True):
            with st.spinner("Building report..."):
                try:
                    pdf_bytes = generate_pdf_report(campaign, ins)
                    fname = (
                        f"report_{campaign['campaign_name'].replace(' ','_')}_"
                        f"{datetime.now().strftime('%Y%m%d')}.pdf"
                    )
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"PDF generation error: {e}")
    with col_info:
        st.caption(f"Generated: {ins.get('generated_at', '—')}")
        st.caption(f"Avg QA Score: {ins.get('campaign_summary', {}).get('avg_qa_score', 0):.1f}%")
        st.caption(f"Bot Failures: {ins.get('campaign_summary', {}).get('total_failures', 0)}")
