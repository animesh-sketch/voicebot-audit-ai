"""
pages/audit_template.py — Custom Audit Template Builder.
Each campaign has its own scoring template with weighted fields.
"""
import streamlit as st

from database.db_manager import (
    get_all_campaigns, get_campaign, get_template_fields,
    add_template_field, delete_template_field,
)
from utils import page_header, section_header, kpi_card, info_banner, nav

_DEFAULT_FIELDS = [
    ("Greeting Quality",    10.0),
    ("Entity Capture",      15.0),
    ("Bot Clarity",         10.0),
    ("Lead Qualification",  15.0),
    ("Closure Attempt",     10.0),
]


def render():
    page_header("📝 Audit Template Builder", "Define custom scoring criteria for each campaign")

    campaigns = get_all_campaigns()
    active = [c for c in campaigns if c["status"] not in ("CLOSED",)]
    all_c  = campaigns  # allow viewing templates for closed campaigns too

    if not all_c:
        info_banner("No campaigns found", "Create a campaign first.")
        if st.button("➕ Create Campaign", type="primary"):
            nav("campaigns")
        return

    camp_opts = {f"{c['campaign_name']} ({c['campaign_id']})": c["campaign_id"] for c in all_c}
    presel = st.session_state.get("selected_campaign_id")
    default_idx = 0
    if presel:
        vals = list(camp_opts.values())
        if presel in vals:
            default_idx = vals.index(presel)

    chosen_key  = st.selectbox("Select Campaign", list(camp_opts.keys()), index=default_idx)
    campaign_id = camp_opts[chosen_key]
    campaign    = get_campaign(campaign_id)
    is_closed   = campaign["status"] == "CLOSED"

    fields = get_template_fields(campaign_id)

    # ── Template overview ─────────────────────────────────────────
    total_max = sum(f["max_score"] for f in fields)
    c1, c2, c3 = st.columns(3)
    with c1: kpi_card("Template Fields", str(len(fields)), color="#2980B9")
    with c2: kpi_card("Total Max Score",  f"{total_max:.0f} pts", color="#27AE60")
    with c3: kpi_card("Status", campaign["status"], color="#F39C12" if is_closed else "#27AE60")

    if is_closed:
        st.warning("⚠️ This campaign is closed. Template is read-only.")

    st.markdown("---")

    # ── Seed defaults (if empty) ──────────────────────────────────
    if not fields and not is_closed:
        st.info("This campaign has no audit template yet.")
        with st.expander("💡 Apply Default Template", expanded=True):
            st.markdown("Default fields: " + ", ".join(f[0] for f in _DEFAULT_FIELDS))
            if st.button("✅ Apply Default Template", type="primary"):
                for fname, max_s in _DEFAULT_FIELDS:
                    add_template_field(campaign_id, fname, max_s)
                st.success("Default template applied!")
                st.rerun()

    # ── Existing fields ───────────────────────────────────────────
    section_header("📋 Current Template Fields")
    if not fields:
        st.info("No fields defined. Add fields below or apply the default template.")
    else:
        col_hdrs = st.columns([3, 2, 2, 1])
        col_hdrs[0].markdown("**Field Name**")
        col_hdrs[1].markdown("**Max Score**")
        col_hdrs[2].markdown("**Weight (%)**")
        col_hdrs[3].markdown("**Action**")
        st.divider()

        for field in fields:
            weight = round(field["max_score"] / total_max * 100, 1) if total_max else 0
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            with c1:
                st.markdown(f"**{field['field_name']}**")
                st.caption(f"ID: `{field['field_id']}`")
            with c2:
                st.markdown(f"`{field['max_score']:.0f} pts`")
            with c3:
                st.markdown(f"`{weight:.1f}%`")
                # Mini progress bar
                st.markdown(
                    f'<div style="background:#ECF0F1;border-radius:4px;height:6px;">'
                    f'<div style="width:{weight:.0f}%;background:#2980B9;height:6px;border-radius:4px;"></div></div>',
                    unsafe_allow_html=True,
                )
            with c4:
                if not is_closed:
                    if st.button("🗑️", key=f"del_{field['field_id']}", help="Delete field"):
                        delete_template_field(field["field_id"])
                        st.rerun()

        st.divider()
        st.markdown(f"**Total: {total_max:.0f} pts across {len(fields)} fields**")

    # ── Add new field ─────────────────────────────────────────────
    if not is_closed:
        st.markdown("---")
        section_header("➕ Add New Field")
        with st.form("add_field_form"):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                fname = st.text_input("Field Name *", placeholder="e.g. Empathy & Tone")
            with col_b:
                max_s = st.number_input("Max Score", 1.0, 100.0, 10.0, 1.0)

            st.markdown("**Common field examples:**")
            st.markdown(
                "Greeting Quality · Entity Capture · Bot Clarity · Lead Qualification · "
                "Closure Attempt · Empathy & Tone · Problem Resolution · Compliance Check"
            )
            ok = st.form_submit_button("Add Field", type="primary", use_container_width=True)
            if ok:
                if not fname.strip():
                    st.error("Field name is required.")
                else:
                    add_template_field(campaign_id, fname.strip(), max_s)
                    st.success(f"Field '{fname}' added!")
                    st.rerun()

    # ── Template preview ──────────────────────────────────────────
    if fields:
        st.markdown("---")
        section_header("👁️ Template Preview (Audit Form)")
        st.markdown("This is how auditors will see the scoring form:")
        with st.container():
            for field in fields:
                st.slider(
                    field["field_name"],
                    0.0, field["max_score"],
                    field["max_score"] / 2,
                    0.5,
                    key=f"prev_{field['field_id']}",
                    help=f"Max: {field['max_score']:.0f} pts ({round(field['max_score'] / total_max * 100, 1) if total_max else 0}% weight)",
                    disabled=True,
                )
