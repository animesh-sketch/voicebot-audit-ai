"""
pages/dashboard.py — Main SaaS dashboard with platform overview,
Plotly charts, and quick-access campaign cards.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

from database.db_manager import (
    get_all_campaigns, get_campaign_progress, get_platform_stats,
    get_failures_for_campaign, get_campaign_insights,
)
from database.models import (
    FAILURE_TYPE_COLORS, LEAD_CATEGORY_COLORS, STATUS_COLORS, CampaignStatus
)
from utils import (
    page_header, section_header, kpi_card, badge, progress_bar,
    info_banner, nav, finding_card,
)

# ── Colour helpers ────────────────────────────────────────────────
_BG    = "#F4F6F9"
_DARK  = "#1C2833"
_BLUE  = "#2980B9"
_GREEN = "#27AE60"
_RED   = "#E74C3C"
_AMBER = "#F39C12"


def _base_layout(title: str, h: int = 380) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=14, color=_DARK)),
        paper_bgcolor="white", plot_bgcolor=_BG,
        height=h, margin=dict(l=40, r=20, t=45, b=30),
        font=dict(family="Inter, sans-serif", size=11, color=_DARK),
    )


def render():
    page_header("🏠 Platform Dashboard", "Real-time overview of all VoiceBot audit campaigns")

    stats = get_platform_stats()
    campaigns = get_all_campaigns()

    # ── KPI row ───────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: kpi_card("Campaigns",     str(stats["campaigns"]),    color="#2980B9")
    with c2: kpi_card("Active",        str(stats["active"]),       color="#27AE60")
    with c3: kpi_card("Closed",        str(stats["closed"]),       color="#7F8C8D")
    with c4: kpi_card("Total Calls",   str(stats["total_calls"]),  color="#8E44AD")
    with c5: kpi_card("Audited",       str(stats["audited"]),      color="#2980B9")
    with c6:
        avg = stats["avg_score"]
        kpi_card("Avg QA Score",
                 f"{avg:.1f}%",
                 color=_GREEN if avg >= 70 else _RED)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        section_header("📊 Failure Distribution (All Campaigns)")
        # Aggregate failure types
        fail_agg: dict[str, int] = {}
        for camp in campaigns:
            fails = get_failures_for_campaign(camp["campaign_id"])
            for f in fails:
                ft = f["failure_type"]
                fail_agg[ft] = fail_agg.get(ft, 0) + 1

        if fail_agg:
            df_fail = pd.DataFrame([
                {"Failure Type": k.replace(" Failure", "").replace(" Detection", ""), "Count": v}
                for k, v in sorted(fail_agg.items(), key=lambda x: -x[1])
            ])
            bar_colors = [FAILURE_TYPE_COLORS.get(k, "#95A5A6") for k in fail_agg]
            fig = go.Figure(go.Bar(
                x=df_fail["Count"], y=df_fail["Failure Type"],
                orientation="h",
                marker_color=[FAILURE_TYPE_COLORS.get(k + " Failure", FAILURE_TYPE_COLORS.get(k, "#95A5A6"))
                              for k in (df_fail["Failure Type"] + " Failure").tolist()],
                text=df_fail["Count"], textposition="outside",
                hovertemplate="%{y}: %{x}<extra></extra>",
            ))
            fig.update_layout(**_base_layout("", 360), xaxis_title="Count", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No failure data yet. Close a campaign to run the intelligence engine.")

    with col_right:
        section_header("📋 Campaign Status Breakdown")
        status_counts = {}
        for c in campaigns:
            s = c["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        if status_counts:
            fig2 = go.Figure(go.Pie(
                labels=list(status_counts.keys()),
                values=list(status_counts.values()),
                hole=0.55,
                marker_colors=[STATUS_COLORS.get(k, "#95A5A6") for k in status_counts],
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}<extra></extra>",
            ))
            fig2.update_layout(**_base_layout("", 340), showlegend=False,
                               margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No campaigns yet.")

    # ── Lead classification aggregate ─────────────────────────────
    col_ll, col_lr = st.columns(2)

    with col_ll:
        section_header("🎯 Lead Classification (Platform-wide)")
        all_leads: dict[str, int] = {}
        for camp in campaigns:
            ins = get_campaign_insights(camp["campaign_id"])
            if ins and ins.get("insights_json"):
                dist = ins["insights_json"].get("lead_classification", {}).get("distribution", {})
                for k, v in dist.items():
                    all_leads[k] = all_leads.get(k, 0) + int(v)

        if all_leads:
            fig3 = go.Figure(go.Pie(
                labels=list(all_leads.keys()),
                values=list(all_leads.values()),
                hole=0.4,
                marker_colors=[LEAD_CATEGORY_COLORS.get(k, "#95A5A6") for k in all_leads],
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}<extra></extra>",
            ))
            fig3.update_layout(**_base_layout("", 320),
                               showlegend=False, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Close a campaign to see lead classification data.")

    with col_lr:
        section_header("📈 Avg QA Score per Campaign")
        scores_data = []
        for c in campaigns:
            ins = get_campaign_insights(c["campaign_id"])
            if ins and ins.get("avg_qa_score"):
                scores_data.append({
                    "Campaign": c["campaign_name"][:22],
                    "Score": ins["avg_qa_score"],
                })

        if scores_data:
            df_scores = pd.DataFrame(scores_data)
            bar_c = [_GREEN if s >= 70 else _RED for s in df_scores["Score"]]
            fig4 = go.Figure(go.Bar(
                x=df_scores["Score"], y=df_scores["Campaign"],
                orientation="h",
                marker_color=bar_c,
                text=[f"{s:.1f}%" for s in df_scores["Score"]],
                textposition="inside",
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            ))
            fig4.add_vline(x=70, line_dash="dash", line_color=_AMBER,
                           annotation_text="70% threshold", annotation_font_color=_AMBER)
            fig4.update_layout(**_base_layout("", 320),
                               xaxis_title="Avg QA Score (%)", xaxis_range=[0, 105])
            st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Close campaigns to see QA score comparison.")

    # ── Campaigns table ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋 All Campaigns")

    if not campaigns:
        info_banner("No campaigns yet", "Create your first campaign to get started.")
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            if st.button("➕ Create Campaign", type="primary", use_container_width=True):
                nav("campaigns")
        return

    for camp in campaigns:
        prog = get_campaign_progress(camp["campaign_id"])
        ins  = get_campaign_insights(camp["campaign_id"])
        avg_s = ins["avg_qa_score"] if ins else None

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([2.8, 1.8, 2.2, 1.5, 1.2, 1.5])
            with c1:
                st.markdown(f"**{camp['campaign_name']}**")
                st.caption(f"Client: {camp['client_name']} · {(camp['created_at'] or '')[:10]}")
            with c2:
                st.markdown(badge(camp["status"]), unsafe_allow_html=True)
            with c3:
                st.markdown(
                    progress_bar(prog["audited"], prog["total"]),
                    unsafe_allow_html=True,
                )
            with c4:
                if avg_s is not None:
                    color = _GREEN if avg_s >= 70 else _RED
                    st.markdown(
                        f"<span style='font-size:1.2rem;font-weight:700;color:{color};'>{avg_s:.1f}%</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("—")
            with c5:
                if st.button("Audit", key=f"d_aud_{camp['campaign_id']}", use_container_width=True):
                    nav("call_audit", selected_campaign_id=camp["campaign_id"])
            with c6:
                if camp["status"] == CampaignStatus.CLOSED.value:
                    if st.button("Insights", key=f"d_ins_{camp['campaign_id']}", use_container_width=True, type="primary"):
                        nav("insights", insights_campaign_id=camp["campaign_id"])
                else:
                    if st.button("Details", key=f"d_det_{camp['campaign_id']}", use_container_width=True):
                        nav("campaigns", selected_campaign_id=camp["campaign_id"])
        st.divider()

    # ── Quick actions ─────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("⚡ Quick Actions")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("➕ New Campaign",    type="primary", use_container_width=True):
            nav("campaigns")
    with qa2:
        if st.button("📥 Import Calls",                   use_container_width=True):
            nav("call_import")
    with qa3:
        if st.button("✍️ Audit Calls",                    use_container_width=True):
            nav("call_audit")
    with qa4:
        if st.button("📊 View Insights",                  use_container_width=True):
            nav("insights")
