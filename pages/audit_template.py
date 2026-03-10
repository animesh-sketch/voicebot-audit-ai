"""
pages/audit_template.py — Custom Audit Template Builder.
Each campaign has its own scoring template with weighted fields.
Supports: CSV/Excel upload · manual field entry · default templates · export.
"""
import io

import pandas as pd
import streamlit as st

from database.db_manager import (
    get_all_campaigns, get_campaign, get_template_fields,
    add_template_field, delete_template_field,
)
from utils import page_header, section_header, kpi_card, info_banner, nav

# ── Built-in template presets ─────────────────────────────────────
PRESETS = {
    "Standard Voice Bot Audit": [
        ("Greeting Quality",    10.0),
        ("Entity Capture",      15.0),
        ("Bot Clarity",         15.0),
        ("Lead Qualification",  10.0),
        ("Closure Attempt",     10.0),
    ],
    "Healthcare Bot Audit": [
        ("Greeting & Empathy",      10.0),
        ("Appointment Intent",      15.0),
        ("Patient Verification",    15.0),
        ("Scheduling Success",      10.0),
        ("Compliance & Disclosure", 10.0),
        ("Closure",                 10.0),
    ],
    "Finance / Mortgage Bot": [
        ("Greeting Quality",        10.0),
        ("Financial Needs Capture", 15.0),
        ("Credit Qualification",    15.0),
        ("Product Matching",        10.0),
        ("Compliance Check",        15.0),
        ("Closure Attempt",         10.0),
    ],
    "E-Commerce Support Bot": [
        ("Greeting & Tone",         10.0),
        ("Issue Identification",    15.0),
        ("Resolution Quality",      20.0),
        ("Empathy",                 10.0),
        ("Closure & Follow-up",     10.0),
    ],
}

_CSV_TEMPLATE = "field_name,max_score\nGreeting Quality,10\nEntity Capture,15\nBot Clarity,15\nLead Qualification,10\nClosure Attempt,10\n"


# ─────────────────────────── Main render ─────────────────────────

def render():
    page_header("📝 Audit Template Builder",
                "Define custom scoring criteria — upload CSV/Excel, add manually, or apply a preset")

    campaigns = get_all_campaigns()
    if not campaigns:
        info_banner("No campaigns found", "Create a campaign first.")
        if st.button("➕ Create Campaign", type="primary"):
            nav("campaigns")
        return

    camp_opts = {f"{c['campaign_name']} ({c['campaign_id']})": c["campaign_id"]
                 for c in campaigns}
    presel      = st.session_state.get("selected_campaign_id")
    default_idx = 0
    if presel:
        vals = list(camp_opts.values())
        if presel in vals:
            default_idx = vals.index(presel)

    chosen_key  = st.selectbox("Select Campaign", list(camp_opts.keys()), index=default_idx)
    campaign_id = camp_opts[chosen_key]
    campaign    = get_campaign(campaign_id)
    is_closed   = campaign["status"] == "CLOSED"

    fields    = get_template_fields(campaign_id)
    total_max = sum(f["max_score"] for f in fields)

    # ── KPI row ───────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Fields Defined", str(len(fields)),          color="#2980B9")
    with k2: kpi_card("Total Max Score", f"{total_max:.0f} pts",   color="#27AE60")
    with k3: kpi_card("Campaign Status", campaign["status"],
                      color="#7F8C8D" if is_closed else "#27AE60")
    with k4:
        avg_w = total_max / len(fields) if fields else 0
        kpi_card("Avg Field Weight", f"{avg_w:.1f} pts",           color="#8E44AD")

    if is_closed:
        st.warning("⚠️ This campaign is closed — template is read-only.")
        _render_current_fields(fields, total_max, is_closed, campaign_id)
        _render_export(fields, campaign)
        return

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────
    t_upload, t_manual, t_preset, t_fields, t_preview, t_export = st.tabs([
        "📂 Upload Template",
        "✏️ Add Field",
        "💡 Presets",
        "📋 Current Fields",
        "👁️ Preview",
        "⬇️ Export",
    ])

    with t_upload:
        _render_upload_tab(campaign_id, fields)

    with t_manual:
        _render_manual_tab(campaign_id)

    with t_preset:
        _render_preset_tab(campaign_id, fields)

    with t_fields:
        _render_current_fields(fields, total_max, is_closed, campaign_id)

    with t_preview:
        _render_preview(get_template_fields(campaign_id))  # re-fetch after possible changes

    with t_export:
        _render_export(fields, campaign)


# ─────────────────────────── Upload tab ──────────────────────────

def _render_upload_tab(campaign_id: str, existing_fields: list):
    section_header("📂 Upload Audit Template (CSV or Excel)")

    # ── Download blank template ───────────────────────────────────
    col_dl, col_info = st.columns([1, 2])
    with col_dl:
        st.download_button(
            "⬇️ Download Blank CSV Template",
            data=_CSV_TEMPLATE,
            file_name="audit_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_info:
        st.info(
            "**Required columns:** `field_name`, `max_score`  \n"
            "Accepted file types: `.csv`, `.xlsx`, `.xls`  \n"
            "Max score must be a positive number (e.g. `10`, `15`)."
        )

    # ── File uploader ─────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Drop your template file here",
        type=["csv", "xlsx", "xls"],
        key="tmpl_upload",
        help="Columns required: field_name (text), max_score (number)",
    )

    if not uploaded:
        # Show format reference
        with st.expander("📄 Example file format", expanded=False):
            st.code(
                "field_name,max_score\n"
                "Greeting Quality,10\n"
                "Entity Capture,15\n"
                "Bot Clarity,15\n"
                "Lead Qualification,10\n"
                "Compliance Check,10\n"
                "Closure Attempt,10",
                language="text",
            )
        return

    # ── Parse file ────────────────────────────────────────────────
    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    # ── Normalise column names (strip whitespace, lowercase) ──────
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # ── Validate ──────────────────────────────────────────────────
    errors = []
    if "field_name" not in df.columns:
        errors.append("Missing column: `field_name`")
    if "max_score" not in df.columns:
        errors.append("Missing column: `max_score`")

    if errors:
        for e in errors:
            st.error(e)
        st.caption(f"Detected columns: {list(df.columns)}")
        return

    # Drop empty rows
    df = df.dropna(subset=["field_name", "max_score"])
    df["field_name"] = df["field_name"].astype(str).str.strip()
    df["max_score"]  = pd.to_numeric(df["max_score"], errors="coerce")

    invalid_rows = df[df["max_score"].isna() | (df["max_score"] <= 0)]
    df           = df[~(df["max_score"].isna() | (df["max_score"] <= 0))]

    if invalid_rows.shape[0]:
        st.warning(
            f"⚠️ Skipped {invalid_rows.shape[0]} row(s) with invalid or missing `max_score`."
        )

    if df.empty:
        st.error("No valid rows found after validation. Please check your file.")
        return

    # ── Preview ───────────────────────────────────────────────────
    st.success(f"✅ File parsed — **{len(df)} valid field(s)** found.")
    total_preview = df["max_score"].sum()
    df["weight_%"] = (df["max_score"] / total_preview * 100).round(1)
    st.dataframe(
        df[["field_name", "max_score", "weight_%"]].rename(columns={
            "field_name": "Field Name",
            "max_score":  "Max Score",
            "weight_%":   "Weight %",
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Total max score: **{total_preview:.0f} pts**")

    # ── Import mode ───────────────────────────────────────────────
    st.markdown("---")
    mode = st.radio(
        "Import mode",
        ["Append to existing fields", "Replace all existing fields"],
        horizontal=True,
        help="Append adds the uploaded fields on top of what's already there. "
             "Replace deletes all current fields first.",
    )

    if existing_fields and mode == "Replace all existing fields":
        st.warning(
            f"⚠️ **Replace** will permanently delete the "
            f"**{len(existing_fields)} existing field(s)** for this campaign."
        )

    # ── Import button ─────────────────────────────────────────────
    col_imp, col_cancel = st.columns([1, 1])
    with col_imp:
        if st.button("📥 Import Template", type="primary", use_container_width=True):
            with st.spinner("Importing..."):
                if mode == "Replace all existing fields":
                    for f in existing_fields:
                        delete_template_field(f["field_id"])

                for _, row in df.iterrows():
                    add_template_field(
                        campaign_id,
                        str(row["field_name"]),
                        float(row["max_score"]),
                    )

            action = "replaced with" if mode == "Replace all existing fields" else "added"
            st.success(
                f"✅ **{len(df)} field(s) {action}** successfully! "
                "Switch to **Current Fields** tab to review."
            )
            st.rerun()
    with col_cancel:
        if st.button("Clear", use_container_width=True):
            st.rerun()


# ─────────────────────────── Manual tab ──────────────────────────

def _render_manual_tab(campaign_id: str):
    section_header("✏️ Add Field Manually")
    with st.form("add_field_form"):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            fname = st.text_input("Field Name *", placeholder="e.g. Empathy & Tone")
        with col_b:
            max_s = st.number_input("Max Score", 1.0, 100.0, 10.0, 1.0)

        st.markdown(
            "**Common examples:** Greeting Quality · Entity Capture · Bot Clarity · "
            "Lead Qualification · Closure Attempt · Empathy & Tone · Problem Resolution · "
            "Compliance Check · Accuracy · Call Handling"
        )
        if st.form_submit_button("➕ Add Field", type="primary", use_container_width=True):
            if not fname.strip():
                st.error("Field name is required.")
            else:
                add_template_field(campaign_id, fname.strip(), max_s)
                st.success(f"Field **'{fname}'** added!")
                st.rerun()


# ─────────────────────────── Preset tab ──────────────────────────

def _render_preset_tab(campaign_id: str, existing_fields: list):
    section_header("💡 Apply a Preset Template")
    st.markdown(
        "Choose a built-in preset designed for common voice-bot use cases. "
        "You can further customise fields after applying."
    )

    for preset_name, preset_fields in PRESETS.items():
        total = sum(s for _, s in preset_fields)
        with st.expander(f"**{preset_name}** — {len(preset_fields)} fields, {total:.0f} pts total"):
            # Preview table
            preview_df = pd.DataFrame(preset_fields, columns=["Field Name", "Max Score"])
            preview_df["Weight %"] = (preview_df["Max Score"] / total * 100).round(1)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)

            mode = st.radio(
                "Import mode",
                ["Append", "Replace existing"],
                horizontal=True,
                key=f"preset_mode_{preset_name}",
            )

            if st.button(
                f"✅ Apply  \"{preset_name}\"",
                key=f"apply_{preset_name}",
                type="primary",
                use_container_width=True,
            ):
                if mode == "Replace existing":
                    for f in existing_fields:
                        delete_template_field(f["field_id"])
                for fname, max_s in preset_fields:
                    add_template_field(campaign_id, fname, max_s)
                st.success(f"Preset **{preset_name}** applied!")
                st.rerun()


# ─────────────────────────── Current fields tab ───────────────────

def _render_current_fields(fields: list, total_max: float, is_closed: bool, campaign_id: str):
    section_header("📋 Current Template Fields")

    if not fields:
        st.info("No fields defined yet. Use **Upload Template**, **Add Field**, or a **Preset**.")
        return

    col_h = st.columns([3, 1.8, 2, 0.8])
    col_h[0].markdown("**Field Name**")
    col_h[1].markdown("**Max Score**")
    col_h[2].markdown("**Weight**")
    col_h[3].markdown("**Del**")
    st.divider()

    for field in fields:
        weight = round(field["max_score"] / total_max * 100, 1) if total_max else 0
        c1, c2, c3, c4 = st.columns([3, 1.8, 2, 0.8])
        with c1:
            st.markdown(f"**{field['field_name']}**")
            st.caption(f"`{field['field_id']}`")
        with c2:
            st.markdown(f"`{field['max_score']:.0f} pts`")
        with c3:
            st.markdown(f"`{weight:.1f}%`")
            st.markdown(
                f'<div style="background:#ECF0F1;border-radius:4px;height:7px;">'
                f'<div style="width:{min(weight,100):.0f}%;background:#2980B9;'
                f'height:7px;border-radius:4px;"></div></div>',
                unsafe_allow_html=True,
            )
        with c4:
            if not is_closed:
                if st.button("🗑️", key=f"del_{field['field_id']}", help="Delete this field"):
                    delete_template_field(field["field_id"])
                    st.rerun()

    st.divider()
    st.markdown(f"**Total: {total_max:.0f} pts across {len(fields)} field(s)**")

    # Clear all button
    if not is_closed and fields:
        if st.button("🗑️ Clear All Fields", use_container_width=False):
            st.session_state["confirm_clear"] = True

        if st.session_state.get("confirm_clear"):
            st.warning("This will delete **all** template fields. Are you sure?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Yes, clear all", type="primary", use_container_width=True):
                    for f in fields:
                        delete_template_field(f["field_id"])
                    st.session_state["confirm_clear"] = False
                    st.success("All fields cleared.")
                    st.rerun()
            with cc2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["confirm_clear"] = False
                    st.rerun()


# ─────────────────────────── Preview tab ─────────────────────────

def _render_preview(fields: list):
    section_header("👁️ Audit Form Preview")
    if not fields:
        st.info("No fields to preview. Add fields first.")
        return

    total_max = sum(f["max_score"] for f in fields)
    st.markdown("This is exactly how auditors will see the scoring form:")
    st.markdown("---")
    for field in fields:
        weight = round(field["max_score"] / total_max * 100, 1) if total_max else 0
        st.slider(
            f"{field['field_name']}  *(max {field['max_score']:.0f} pts · {weight:.0f}% weight)*",
            0.0, field["max_score"],
            field["max_score"] / 2,
            0.5,
            key=f"prev_{field['field_id']}",
            disabled=True,
        )
    st.markdown("---")
    st.caption(f"Total: {total_max:.0f} pts · {len(fields)} fields")


# ─────────────────────────── Export tab ──────────────────────────

def _render_export(fields: list, campaign: dict):
    section_header("⬇️ Export Current Template")

    if not fields:
        st.info("No fields to export yet.")
        return

    total_max = sum(f["max_score"] for f in fields)
    df = pd.DataFrame([
        {
            "field_name": f["field_name"],
            "max_score":  f["max_score"],
            "weight_pct": round(f["max_score"] / total_max * 100, 1) if total_max else 0,
        }
        for f in fields
    ])

    safe_name = campaign["campaign_name"].replace(" ", "_")
    col_csv, col_xlsx = st.columns(2)

    with col_csv:
        csv_bytes = df.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download as CSV",
            data=csv_bytes,
            file_name=f"{safe_name}_template.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

    with col_xlsx:
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit Template")
        xlsx_bytes = xlsx_buf.getvalue()
        st.download_button(
            "⬇️ Download as Excel",
            data=xlsx_bytes,
            file_name=f"{safe_name}_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("---")
    st.dataframe(
        df.rename(columns={"field_name": "Field Name", "max_score": "Max Score", "weight_pct": "Weight %"}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        f"Total: **{total_max:.0f} pts** · {len(fields)} fields · "
        f"Campaign: {campaign['campaign_name']}"
    )
