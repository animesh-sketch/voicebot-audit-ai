"""
pages/call_audit.py — Call Audit Interface.
Auditors review transcripts, score calls, tag issues, and submit results.
"""
import streamlit as st

from database.db_manager import (
    get_all_campaigns, get_campaign, get_calls_for_campaign,
    get_call, get_template_fields, submit_audit, get_audit_for_call,
    get_failures_for_call, get_campaign_progress, update_call_lead_category,
)
from database.models import LeadCategory, IssueTag, CampaignStatus, FAILURE_TYPE_COLORS
from utils import (
    page_header, section_header, kpi_card, badge, progress_bar,
    info_banner, nav, finding_card,
)

_GREEN = "#27AE60"
_RED   = "#E74C3C"
_AMBER = "#F39C12"
_BLUE  = "#2980B9"

_ISSUE_TAG_COLORS = {
    "Latency":                  "#F39C12",
    "Hallucination":            "#E74C3C",
    "STT Error":                "#8E44AD",
    "Intent Misclassification": "#2980B9",
    "Conversation Drop":        "#E67E22",
}


def render():
    page_header("✍️ Call Audit Interface", "Review calls, score quality, and tag bot failures")

    campaigns = get_all_campaigns()
    non_closed = [c for c in campaigns if c["status"] != CampaignStatus.CLOSED.value]

    if not non_closed:
        info_banner("No active campaigns available for auditing",
                    "All campaigns are closed. Create a new one to start auditing.")
        if st.button("📋 Go to Campaigns"):
            nav("campaigns")
        return

    camp_opts = {f"{c['campaign_name']} ({c['campaign_id']})": c["campaign_id"]
                 for c in non_closed}
    presel = st.session_state.get("selected_campaign_id")
    default_idx = 0
    if presel:
        vals = list(camp_opts.values())
        if presel in vals:
            default_idx = vals.index(presel)

    chosen_key  = st.selectbox("Select Campaign", list(camp_opts.keys()), index=default_idx)
    campaign_id = camp_opts[chosen_key]
    st.session_state["selected_campaign_id"] = campaign_id
    campaign = get_campaign(campaign_id)

    prog   = get_campaign_progress(campaign_id)
    calls  = get_calls_for_campaign(campaign_id)
    fields = get_template_fields(campaign_id)

    # ── Campaign progress header ──────────────────────────────────
    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1: kpi_card("Total Calls",  str(prog["total"]),   color=_BLUE)
    with pc2: kpi_card("Audited",      str(prog["audited"]), color=_GREEN)
    with pc3: kpi_card("Pending",      str(prog["pending"]), color=_AMBER if prog["pending"] else _GREEN)
    with pc4:
        pct = prog["pct"]
        kpi_card("Completion", f"{pct:.0f}%",
                 color=_GREEN if pct == 100 else _BLUE)

    st.markdown(progress_bar(prog["audited"], prog["total"]), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not calls:
        info_banner("No calls in this campaign",
                    "Import calls first before auditing.")
        if st.button("📥 Import Calls"):
            nav("call_import", selected_campaign_id=campaign_id)
        return

    if not fields:
        st.warning("⚠️ No audit template defined for this campaign. Define scoring criteria first.")
        if st.button("📝 Build Template"):
            nav("audit_template", selected_campaign_id=campaign_id)
        return

    # ── Call selector + call list ─────────────────────────────────
    tab_list, tab_audit = st.tabs(["📋 Call Explorer", "✍️ Audit Form"])

    with tab_list:
        _render_call_explorer(calls, campaign_id)

    with tab_audit:
        _render_audit_form(calls, campaign_id, campaign, fields)


def _render_call_explorer(calls: list, campaign_id: str):
    section_header("📋 Call List")

    # Filter controls
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filt_status = st.selectbox("Status Filter", ["All", "Pending", "Audited"], key="exp_status")
    with col_f2:
        filt_lead = st.selectbox("Lead Category", ["All"] + [e.value for e in LeadCategory], key="exp_lead")
    with col_f3:
        sort_by = st.selectbox("Sort by", ["Date", "Duration", "Score"], key="exp_sort")

    filtered = calls
    if filt_status == "Pending":
        filtered = [c for c in filtered if not c.get("audit_id")]
    elif filt_status == "Audited":
        filtered = [c for c in filtered if c.get("audit_id")]
    if filt_lead != "All":
        filtered = [c for c in filtered if c.get("lead_category") == filt_lead]

    st.markdown(f"Showing **{len(filtered)}** of {len(calls)} calls")
    st.divider()

    for c in filtered:
        is_audited = bool(c.get("audit_id"))
        score_pct  = c.get("percentage_score")

        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([1.8, 1.6, 1.5, 1.5, 1.5, 1.1])
            with col1:
                st.markdown(f"**`{c['call_id']}`**")
                link = c.get("call_link", "")
                if link:
                    st.markdown(f"[🔗 Recording]({link})", unsafe_allow_html=False)
            with col2:
                dur = c.get("duration") or 0
                st.metric("Duration", f"{dur // 60}m {dur % 60}s", label_visibility="visible")
            with col3:
                st.markdown(f"`{c.get('lead_category', 'UNKNOWN')}`")
                st.caption(str(c.get("timestamp", "—"))[:10])
            with col4:
                st.markdown(badge("audited" if is_audited else "pending"), unsafe_allow_html=True)
                if is_audited and c.get("auditor_name"):
                    st.caption(f"by {c['auditor_name']}")
            with col5:
                if score_pct is not None:
                    color = _GREEN if score_pct >= 70 else (_AMBER if score_pct >= 50 else _RED)
                    st.markdown(
                        f"<b style='font-size:1.2rem;color:{color};'>{score_pct:.1f}%</b>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("—")
            with col6:
                btn_label = "Re-Audit" if is_audited else "Audit →"
                if st.button(btn_label, key=f"sel_{c['call_id']}", use_container_width=True,
                             type="primary" if not is_audited else "secondary"):
                    st.session_state["audit_call_id"] = c["call_id"]
                    st.rerun()
        st.divider()


def _render_audit_form(calls: list, campaign_id: str, campaign: dict, fields: list):
    section_header("✍️ Audit a Call")

    # Call selection
    call_opts = {}
    for c in calls:
        status = "✅" if c.get("audit_id") else "⏳"
        score  = f" ({c['percentage_score']:.0f}%)" if c.get("percentage_score") else ""
        label  = f"{status} {c['call_id']} — {c.get('lead_category','?')}{score}"
        call_opts[label] = c["call_id"]

    presel_call = st.session_state.get("audit_call_id")
    call_keys   = list(call_opts.keys())
    call_vals   = list(call_opts.values())
    default_ci  = 0
    if presel_call and presel_call in call_vals:
        default_ci = call_vals.index(presel_call)
    # Prefer pending calls by default
    elif any("⏳" in k for k in call_keys):
        default_ci = next(i for i, k in enumerate(call_keys) if "⏳" in k)

    chosen_call_key = st.selectbox("Select Call", call_keys, index=default_ci, key="audit_call_sel")
    call_id = call_opts[chosen_call_key]
    call    = get_call(call_id)

    if not call:
        st.error("Call not found.")
        return

    # ── Call metadata ─────────────────────────────────────────────
    st.markdown("---")
    mc1, mc2, mc3, mc4 = st.columns(4)
    dur = call.get("duration") or 0
    mc1.metric("Call ID",   call["call_id"])
    mc2.metric("Duration",  f"{dur // 60}m {dur % 60}s")
    mc3.metric("Lead Cat.", call.get("lead_category", "UNKNOWN"))
    mc4.metric("Date",      str(call.get("timestamp", "—"))[:10])

    col_link, col_lcat = st.columns(2)
    with col_link:
        link = call.get("call_link", "")
        if link:
            st.markdown(f"🔗 **Recording:** [{link[:50]}]({link})")
        else:
            st.info("No call link available.")
    with col_lcat:
        new_cat = st.selectbox(
            "Update Lead Category",
            [e.value for e in LeadCategory],
            index=[e.value for e in LeadCategory].index(call.get("lead_category", "UNKNOWN")),
            key=f"lcat_{call_id}",
        )
        if new_cat != call.get("lead_category", "UNKNOWN"):
            update_call_lead_category(call_id, new_cat)

    # ── Transcript viewer ─────────────────────────────────────────
    transcript = call.get("transcript", "") or ""
    if transcript:
        section_header("📄 Call Transcript")
        # Pretty-print transcript with color-coded speaker turns
        rendered_lines = []
        for line in transcript.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("bot:"):
                rendered_lines.append(
                    f'<div style="background:#EBF5FB;border-left:3px solid #2980B9;'
                    f'padding:6px 12px;border-radius:0 6px 6px 0;margin:3px 0;">'
                    f'<b style="color:#1A5276;">🤖 Bot:</b> {line[4:].strip()}</div>'
                )
            elif line.lower().startswith("customer:"):
                rendered_lines.append(
                    f'<div style="background:#EAFAF1;border-left:3px solid #27AE60;'
                    f'padding:6px 12px;border-radius:0 6px 6px 0;margin:3px 0;">'
                    f'<b style="color:#1E8449;">👤 Customer:</b> {line[9:].strip()}</div>'
                )
            else:
                rendered_lines.append(
                    f'<div style="padding:4px 12px;color:#7F8C8D;">{line}</div>'
                )
        st.markdown(
            '<div style="max-height:280px;overflow-y:auto;padding:8px;background:white;'
            'border:1px solid #ECF0F1;border-radius:8px;">'
            + "\n".join(rendered_lines) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No transcript available for this call.")

    # ── Auto-detected failures ────────────────────────────────────
    auto_failures = get_failures_for_call(call_id)
    if auto_failures:
        section_header("🤖 Auto-Detected Bot Issues")
        for fail in auto_failures:
            color = FAILURE_TYPE_COLORS.get(fail["failure_type"], "#7F8C8D")
            conf  = fail["confidence_score"]
            st.markdown(
                f'<div style="background:white;border-left:4px solid {color};'
                f'padding:0.5rem 1rem;border-radius:0 8px 8px 0;margin:4px 0;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.05);">'
                f'<b style="color:{color};">⚠ {fail["failure_type"]}</b> '
                f'<span style="color:#7F8C8D;font-size:0.78rem;">(confidence: {conf:.0%})</span><br>'
                f'<span style="font-size:0.87rem;">{fail["failure_reason"]}</span></div>',
                unsafe_allow_html=True,
            )

    # ── Existing audit (if any) ───────────────────────────────────
    existing_audit = get_audit_for_call(call_id)
    if existing_audit:
        st.info(
            f"✅ This call was already audited by **{existing_audit['auditor_name']}** "
            f"— Score: **{existing_audit['percentage_score']:.1f}%**. "
            "Submitting again will overwrite the previous audit."
        )

    # ── Audit form ────────────────────────────────────────────────
    st.markdown("---")
    section_header("📊 Scoring Scorecard")

    auditor_name = st.text_input("Auditor Name", value=st.session_state.get("auditor_name", "QA Auditor"))
    st.session_state["auditor_name"] = auditor_name

    total_max = sum(f["max_score"] for f in fields)

    with st.form(f"audit_form_{call_id}"):
        scores: dict = {}
        live_total = 0.0

        for field in fields:
            fid   = field["field_id"]
            max_s = field["max_score"]
            weight = round(max_s / total_max * 100, 1) if total_max else 0
            prev   = (
                float(existing_audit["field_scores"].get(fid, max_s / 2))
                if existing_audit else max_s / 2
            )
            score = st.slider(
                f"{field['field_name']}  *(max {max_s:.0f} pts, {weight:.0f}% weight)*",
                0.0, max_s, prev, 0.5,
                key=f"sf_{fid}_{call_id}",
            )
            scores[fid] = score
            live_total += score

        live_pct = live_total / total_max * 100 if total_max else 0
        score_color = _GREEN if live_pct >= 70 else (_AMBER if live_pct >= 50 else _RED)
        st.markdown(
            f'<div style="background:{score_color}22;border:1px solid {score_color};'
            f'border-radius:8px;padding:0.6rem 1rem;margin:0.5rem 0;">'
            f'<b style="color:{score_color};font-size:1.1rem;">Projected Score: '
            f'{live_total:.1f} / {total_max:.0f} pts = {live_pct:.1f}%</b></div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("**🏷️ Issue Tags** *(select all that apply)*")
        issue_tags = []
        tag_cols = st.columns(len(list(IssueTag)))
        for i, tag in enumerate(IssueTag):
            prev_tags = existing_audit["issue_tags"] if existing_audit else []
            checked = tag_cols[i].checkbox(
                tag.value,
                value=(tag.value in prev_tags),
                key=f"tag_{tag.value}_{call_id}",
            )
            if checked:
                issue_tags.append(tag.value)

        notes = st.text_area(
            "📝 Auditor Notes",
            value=existing_audit["notes"] if existing_audit else "",
            placeholder="e.g. Bot failed to capture customer's email. Latency noticed in turns 3–5.",
            height=90,
        )

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("✅ Submit Audit", type="primary", use_container_width=True)
        with c2:
            st.form_submit_button("Clear Form", use_container_width=True)

        if submitted:
            if not auditor_name.strip():
                st.error("Auditor name is required.")
            elif not scores:
                st.error("No scores to save.")
            else:
                result = submit_audit(
                    call_id=call_id,
                    campaign_id=campaign_id,
                    auditor_name=auditor_name.strip(),
                    field_scores=scores,
                    issue_tags=issue_tags,
                    notes=notes,
                )
                pct = result  # audit_id is returned, need to re-fetch
                audit = get_audit_for_call(call_id)
                pct = audit["percentage_score"] if audit else 0
                if pct >= 70:
                    st.success(f"✅ Audit submitted! Score: **{pct:.1f}%** (PASS)")
                    st.balloons()
                else:
                    st.warning(f"⚠️ Audit submitted! Score: **{pct:.1f}%** (FAIL — below 70% threshold)")
                st.session_state["audit_call_id"] = None
                st.rerun()
