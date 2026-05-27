"""
pages/audit_template.py — Custom Audit Template Builder.
Each campaign has its own scoring template with weighted fields.
Supports: CSV · Excel · JSON · TSV upload · paste/URL import · manual entry · presets · export.
"""
import io
import json
import re
import urllib.request

import pandas as pd
import streamlit as st

from database.db_manager import (
    get_all_campaigns, get_campaign, get_template_fields,
    add_template_field, update_template_field, delete_template_field,
)
from database.models import FieldCategory, CONVIN_SENSE_FRAMEWORK
from utils import page_header, section_header, kpi_card, info_banner, nav

# ── Built-in template presets ─────────────────────────────────────
_GEN  = FieldCategory.GENERAL.value
_AI   = FieldCategory.AI_ISSUES.value
_ENT  = FieldCategory.ENTITY_CAPTURE.value
_LEAD = FieldCategory.LEAD_CLASSIFICATION.value
_QA   = FieldCategory.CALL_QUALITY.value
_COMP = FieldCategory.COMPLIANCE.value

# ── Convin Sense v0.3 preset (applied via special handler) ────────
# Uses CONVIN_SENSE_FRAMEWORK from models.py — not a plain tuple preset.

# Presets: each field is (name, max_score, field_category)
PRESETS = {
    "Standard Voice Bot Audit": [
        ("Greeting Quality",   10.0, _QA),
        ("Bot Response Latency", 10.0, _AI),
        ("Entity Capture",     15.0, _ENT),
        ("Bot Clarity",        15.0, _QA),
        ("Lead Qualification", 10.0, _LEAD),
        ("Closure Attempt",    10.0, _QA),
    ],
    "Ferry / Transport Bot": [
        ("Greeting Quality",   10.0, _QA),
        ("Bot Latency",        10.0, _AI),
        ("Hallucination Check", 10.0, _AI),
        ("STT Error Rate",     10.0, _AI),
        ("Language Switch Handling", 10.0, _AI),
        ("Customer Name Capture",   15.0, _ENT),
        ("Route Capture",           15.0, _ENT),
        ("Passenger Count Capture", 15.0, _ENT),
        ("Sailing Date Capture",    15.0, _ENT),
        ("Lead Classification Accuracy", 10.0, _LEAD),
        ("Closure & Next Steps",   10.0, _QA),
    ],
    "Healthcare Bot Audit": [
        ("Greeting & Empathy",      10.0, _QA),
        ("Appointment Intent",      15.0, _QA),
        ("Patient Name Capture",    15.0, _ENT),
        ("Date of Birth Capture",   10.0, _ENT),
        ("Scheduling Success",      10.0, _QA),
        ("Compliance & Disclosure", 10.0, _COMP),
        ("Closure",                 10.0, _QA),
    ],
    "Finance / Mortgage Bot": [
        ("Greeting Quality",        10.0, _QA),
        ("Financial Needs Capture", 15.0, _ENT),
        ("Income Capture",          10.0, _ENT),
        ("Credit Qualification",    15.0, _LEAD),
        ("Product Matching",        10.0, _LEAD),
        ("Compliance Check",        15.0, _COMP),
        ("Closure Attempt",         10.0, _QA),
    ],
    "E-Commerce Support Bot": [
        ("Greeting & Tone",         10.0, _QA),
        ("Issue Identification",    15.0, _ENT),
        ("Resolution Quality",      20.0, _QA),
        ("Empathy",                 10.0, _QA),
        ("Closure & Follow-up",     10.0, _QA),
    ],
}

_CSV_TEMPLATE  = "field_name,max_score,field_category\nGreeting Quality,10,Call Quality\nEntity Capture,15,Entity Capture\nBot Clarity,15,Call Quality\nLead Qualification,10,Lead Classification\nClosure Attempt,10,Call Quality\n"
_TSV_TEMPLATE  = "field_name\tmax_score\tfield_category\nGreeting Quality\t10\tCall Quality\nEntity Capture\t15\tEntity Capture\nBot Clarity\t15\tCall Quality\nLead Qualification\t10\tLead Classification\nClosure Attempt\t10\tCall Quality\n"
_JSON_TEMPLATE = json.dumps([
    {"field_name": "Greeting Quality",   "max_score": 10, "field_category": "Call Quality"},
    {"field_name": "Entity Capture",     "max_score": 15, "field_category": "Entity Capture"},
    {"field_name": "Bot Clarity",        "max_score": 15, "field_category": "Call Quality"},
    {"field_name": "Lead Qualification", "max_score": 10, "field_category": "Lead Classification"},
    {"field_name": "Closure Attempt",    "max_score": 10, "field_category": "Call Quality"},
], indent=2)


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
    t_upload, t_paste, t_manual, t_preset, t_fields, t_preview, t_export = st.tabs([
        "📂 Upload File",
        "📋 Paste / URL",
        "✏️ Add Field",
        "💡 Presets",
        "🗂️ Current Fields",
        "👁️ Preview",
        "⬇️ Export",
    ])

    with t_upload:
        _render_upload_tab(campaign_id, fields)

    with t_paste:
        _render_paste_tab(campaign_id, fields)

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

def _parse_to_df(raw: bytes | str, filename: str = "") -> pd.DataFrame:
    """Parse CSV, TSV, Excel, or JSON bytes/string into a DataFrame."""
    name = filename.lower()
    if isinstance(raw, bytes):
        # JSON detection: starts with [ or {
        text = raw.decode("utf-8", errors="replace").strip()
    else:
        text = raw.strip()

    if name.endswith(".json") or text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        if isinstance(data, dict):          # {fields: [...]} wrapper
            data = data.get("fields", list(data.values())[0] if data else [])
        return pd.DataFrame(data)

    if name.endswith(".tsv") or (not name.endswith((".csv", ".xlsx", ".xls")) and "\t" in text):
        return pd.read_csv(io.StringIO(text) if isinstance(text, str) else io.BytesIO(raw), sep="\t")

    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw) if isinstance(raw, bytes) else io.BytesIO(raw.encode()))

    # Default: CSV
    return pd.read_csv(io.StringIO(text) if isinstance(text, str) else io.BytesIO(raw))


def _validate_and_preview(df: pd.DataFrame, existing_fields: list, campaign_id: str, key_suffix: str = ""):
    """Shared validation, preview, import-mode selector, and import button."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Flexible column name aliasing
    aliases = {"name": "field_name", "score": "max_score", "category": "field_category",
                "weight": "max_score", "field": "field_name", "max": "max_score"}
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns and v not in df.columns})

    errors = []
    if "field_name" not in df.columns:
        errors.append("Missing column: `field_name` (also accepted: `name`, `field`)")
    if "max_score" not in df.columns:
        errors.append("Missing column: `max_score` (also accepted: `score`, `weight`, `max`)")
    if errors:
        for e in errors:
            st.error(e)
        st.caption(f"Detected columns: {list(df.columns)}")
        return

    df = df.dropna(subset=["field_name", "max_score"])
    df["field_name"] = df["field_name"].astype(str).str.strip()
    df["max_score"]  = pd.to_numeric(df["max_score"], errors="coerce")

    invalid = df[df["max_score"].isna() | (df["max_score"] <= 0)]
    df      = df[~(df["max_score"].isna() | (df["max_score"] <= 0))].reset_index(drop=True)

    if not invalid.empty:
        st.warning(f"⚠️ Skipped {len(invalid)} row(s) with invalid `max_score`.")
    if df.empty:
        st.error("No valid rows found. Check your file.")
        return

    total_preview = df["max_score"].sum()
    df["weight_%"] = (df["max_score"] / total_preview * 100).round(1)

    preview_cols = ["field_name", "max_score", "weight_%"]
    if "field_category" in df.columns:
        preview_cols.insert(2, "field_category")

    st.success(f"✅ Parsed — **{len(df)} field(s)** · total {total_preview:.0f} pts")
    st.dataframe(
        df[preview_cols].rename(columns={
            "field_name": "Field Name", "max_score": "Max Score",
            "field_category": "Category", "weight_%": "Weight %",
        }),
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    mode = st.radio(
        "Import mode",
        ["Append to existing fields", "Replace all existing fields"],
        horizontal=True,
        key=f"imp_mode_{key_suffix}",
    )
    if existing_fields and mode == "Replace all existing fields":
        st.warning(f"⚠️ Replace will delete **{len(existing_fields)} existing field(s)**.")

    if st.button("📥 Import Template", type="primary", use_container_width=True,
                 key=f"imp_btn_{key_suffix}"):
        with st.spinner("Importing..."):
            if mode == "Replace all existing fields":
                for f in existing_fields:
                    delete_template_field(f["field_id"])
            for _, row in df.iterrows():
                fcat = str(row["field_category"]) if "field_category" in df.columns and pd.notna(row.get("field_category")) else "General"
                add_template_field(campaign_id, str(row["field_name"]), float(row["max_score"]), fcat)
        action = "replaced with" if mode == "Replace all existing fields" else "added"
        st.success(f"✅ **{len(df)} field(s) {action}** successfully!")
        st.rerun()


def _render_upload_tab(campaign_id: str, existing_fields: list):
    section_header("📂 Upload Audit Template")

    # ── Blank template downloads ───────────────────────────────────
    st.markdown("**Download a blank template in your preferred format:**")
    dc1, dc2, dc3, dc4 = st.columns(4)
    with dc1:
        st.download_button("⬇️ CSV", data=_CSV_TEMPLATE,
                           file_name="audit_template.csv", mime="text/csv",
                           use_container_width=True)
    with dc2:
        xlsx_buf = io.BytesIO()
        pd.DataFrame([
            {"field_name": "Greeting Quality", "max_score": 10, "field_category": "Call Quality"},
            {"field_name": "Entity Capture",   "max_score": 15, "field_category": "Entity Capture"},
        ]).to_excel(xlsx_buf, index=False, sheet_name="Audit Template")
        st.download_button("⬇️ Excel", data=xlsx_buf.getvalue(),
                           file_name="audit_template.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with dc3:
        st.download_button("⬇️ TSV", data=_TSV_TEMPLATE,
                           file_name="audit_template.tsv", mime="text/tab-separated-values",
                           use_container_width=True)
    with dc4:
        st.download_button("⬇️ JSON", data=_JSON_TEMPLATE,
                           file_name="audit_template.json", mime="application/json",
                           use_container_width=True)

    st.markdown("---")

    st.info(
        "**Required columns:** `field_name` · `max_score`  \n"
        "**Optional:** `field_category` (AI Issues · Entity Capture · Lead Classification · Call Quality · Compliance · General)  \n"
        "**Accepted:** `.csv` · `.xlsx` · `.xls` · `.tsv` · `.json`"
    )

    # ── File uploader ─────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Drop your template file here",
        type=["csv", "xlsx", "xls", "tsv", "json"],
        key="tmpl_upload",
    )

    if not uploaded:
        with st.expander("📄 Format examples", expanded=False):
            tab_csv, tab_tsv, tab_json = st.tabs(["CSV", "TSV", "JSON"])
            with tab_csv:
                st.code("field_name,max_score,field_category\nGreeting Quality,10,Call Quality\nEntity Capture,15,Entity Capture\nBot Clarity,15,Call Quality", language="text")
            with tab_tsv:
                st.code("field_name\tmax_score\tfield_category\nGreeting Quality\t10\tCall Quality\nEntity Capture\t15\tEntity Capture", language="text")
            with tab_json:
                st.code('[{"field_name":"Greeting Quality","max_score":10,"field_category":"Call Quality"},\n {"field_name":"Entity Capture","max_score":15,"field_category":"Entity Capture"}]', language="json")
        return

    # ── Parse file ────────────────────────────────────────────────
    try:
        raw = uploaded.read()
        df  = _parse_to_df(raw, uploaded.name)
    except Exception as e:
        st.error(f"Could not parse file: {e}")
        return

    _validate_and_preview(df, existing_fields, campaign_id, key_suffix="upload")


# ─────────────────────────── Paste / URL tab ─────────────────────

def _render_paste_tab(campaign_id: str, existing_fields: list):
    section_header("📋 Paste Data or Import from URL")

    input_type = st.radio(
        "Import source",
        ["📋 Paste raw data (CSV / TSV / JSON)", "🔗 Google Sheets URL", "🌐 Any CSV/JSON URL"],
        horizontal=True,
        key="paste_src",
    )
    st.markdown("")

    raw_text: str | None = None

    if input_type == "📋 Paste raw data (CSV / TSV / JSON)":
        st.markdown(
            "Paste your data below. Auto-detected formats: **CSV**, **TSV** (tab-separated), **JSON array**."
        )
        pasted = st.text_area(
            "Paste here",
            height=220,
            placeholder=(
                "CSV example:\nfield_name,max_score,field_category\n"
                "Greeting Quality,10,Call Quality\n\n"
                "JSON example:\n"
                '[{"field_name":"Greeting Quality","max_score":10,"field_category":"Call Quality"}]'
            ),
            key="paste_raw",
        )
        if pasted.strip():
            raw_text = pasted.strip()

    elif input_type == "🔗 Google Sheets URL":
        st.info(
            "Paste a **public** Google Sheets URL. The sheet must be shared as "
            "'Anyone with the link can view'.  \n"
            "Supported formats: `spreadsheets/d/{ID}/edit` or `spreadsheets/d/{ID}/pub`"
        )
        gsheet_url = st.text_input("Google Sheets URL", placeholder="https://docs.google.com/spreadsheets/d/...")
        if gsheet_url.strip():
            match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", gsheet_url)
            if not match:
                st.error("Could not extract Sheet ID from URL.")
            else:
                sheet_id = match.group(1)
                gid_match = re.search(r"gid=(\d+)", gsheet_url)
                gid = gid_match.group(1) if gid_match else "0"
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                if st.button("📥 Fetch Sheet", use_container_width=False):
                    try:
                        with st.spinner("Fetching Google Sheet..."):
                            req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req, timeout=10) as r:
                                raw_text = r.read().decode("utf-8")
                        st.session_state["paste_fetched"] = raw_text
                    except Exception as e:
                        st.error(f"Failed to fetch sheet: {e}")
                raw_text = st.session_state.get("paste_fetched")

    else:  # Any CSV/JSON URL
        st.info("Paste any public URL that returns CSV or JSON data.")
        any_url = st.text_input("URL", placeholder="https://example.com/template.csv")
        if any_url.strip():
            if st.button("📥 Fetch URL", use_container_width=False):
                try:
                    with st.spinner("Fetching..."):
                        req = urllib.request.Request(any_url.strip(), headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=10) as r:
                            raw_text = r.read().decode("utf-8")
                    st.session_state["url_fetched"] = raw_text
                    st.session_state["url_fetched_name"] = any_url.strip().split("?")[0]
                except Exception as e:
                    st.error(f"Failed to fetch URL: {e}")
            raw_text = st.session_state.get("url_fetched")
            if raw_text:
                st.caption(f"Fetched from: {st.session_state.get('url_fetched_name','')}")

    if raw_text:
        try:
            fname = st.session_state.get("url_fetched_name", "")
            df = _parse_to_df(raw_text, fname)
        except Exception as e:
            st.error(f"Could not parse data: {e}")
            return
        st.markdown("---")
        _validate_and_preview(df, existing_fields, campaign_id, key_suffix="paste")


# ─────────────────────────── Manual tab ──────────────────────────

def _render_manual_tab(campaign_id: str):
    section_header("✏️ Add Field Manually")
    with st.form("add_field_form"):
        col_a, col_b, col_c = st.columns([3, 1, 1.5])
        with col_a:
            fname = st.text_input("Field Name *", placeholder="e.g. Customer Name Capture")
        with col_b:
            max_s = st.number_input("Max Score", 1.0, 100.0, 10.0, 1.0)
        with col_c:
            fcat = st.selectbox(
                "Category",
                [e.value for e in FieldCategory],
                index=[e.value for e in FieldCategory].index(FieldCategory.GENERAL.value),
            )

        st.markdown(
            "**Common examples:** Greeting Quality · Customer Name Capture · Route Capture · "
            "Passenger Count · Sailing Date · Bot Latency · Hallucination Check · "
            "Lead Classification Accuracy · Closure Attempt"
        )
        if st.form_submit_button("➕ Add Field", type="primary", use_container_width=True):
            if not fname.strip():
                st.error("Field name is required.")
            else:
                add_template_field(campaign_id, fname.strip(), max_s, fcat)
                st.success(f"Field **'{fname}'** added under **{fcat}**!")
                st.rerun()


# ─────────────────────────── Preset tab ──────────────────────────

def _render_preset_tab(campaign_id: str, existing_fields: list):
    section_header("💡 Apply a Preset Template")
    st.markdown(
        "Choose a built-in preset designed for common voice-bot use cases. "
        "You can further customise fields after applying."
    )

    # ── Convin Sense v0.3 — primary preset ────────────────────────
    cs_total_w = sum(p["weight_percent"] for p in CONVIN_SENSE_FRAMEWORK if not p["is_fatal"])
    with st.expander(
        f"⭐ **Convin Sense Audit Framework v0.3** — 25 parameters · "
        f"{cs_total_w:.0f}% weighted + 3 FATAL checks",
        expanded=True,
    ):
        cs_rows = []
        for p in CONVIN_SENSE_FRAMEWORK:
            cs_rows.append({
                "#":            p["no"],
                "Parameter":    p["name"],
                "Tier":         p["tier"],
                "Weight":       f"{p['weight_percent']:.0f}%" if not p["is_fatal"] else "FATAL",
                "Response":     p["response_type"].replace("_", "/"),
                "Pass When":    p["pass_value"],
            })
        st.dataframe(pd.DataFrame(cs_rows), use_container_width=True, hide_index=True)

        mode_cs = st.radio(
            "Import mode",
            ["Append", "Replace existing"],
            horizontal=True,
            key="preset_mode_convin_sense",
        )

        if st.button(
            "✅ Apply  \"Convin Sense Audit Framework v0.3\"",
            key="apply_convin_sense",
            type="primary",
            use_container_width=True,
        ):
            if mode_cs == "Replace existing":
                for f in existing_fields:
                    delete_template_field(f["field_id"])
            for p in CONVIN_SENSE_FRAMEWORK:
                add_template_field(
                    campaign_id,
                    field_name=p["name"],
                    max_score=p["weight_percent"],   # use weight as max_score for legacy compat
                    field_category="General",
                    tier=p["tier"],
                    weight_percent=p["weight_percent"],
                    response_type=p["response_type"],
                    is_fatal=int(p["is_fatal"]),
                    pass_value=p["pass_value"],
                )
            st.success("✅ **Convin Sense Audit Framework v0.3** applied — 25 parameters loaded!")
            st.rerun()

    st.markdown("---")
    st.markdown("#### Other domain presets")

    for preset_name, preset_fields in PRESETS.items():
        total = sum(entry[1] for entry in preset_fields)
        with st.expander(f"**{preset_name}** — {len(preset_fields)} fields, {total:.0f} pts total"):
            preview_rows = [
                {
                    "Field Name": entry[0],
                    "Category":   entry[2] if len(entry) > 2 else "General",
                    "Max Score":  entry[1],
                    "Weight %":   round(entry[1] / total * 100, 1),
                }
                for entry in preset_fields
            ]
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

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
                for entry in preset_fields:
                    fname = entry[0]
                    max_s = entry[1]
                    fcat  = entry[2] if len(entry) > 2 else "General"
                    add_template_field(campaign_id, fname, max_s, fcat)
                st.success(f"Preset **{preset_name}** applied!")
                st.rerun()


# ─────────────────────────── Current fields tab ───────────────────

_CAT_COLORS = {
    "AI Issues":            "#E74C3C",
    "Entity Capture":       "#2980B9",
    "Lead Classification":  "#27AE60",
    "Call Quality":         "#F39C12",
    "Compliance":           "#8E44AD",
    "General":              "#7F8C8D",
}

_TIER_COLORS_T = {
    "CRITICAL":  "#E74C3C",
    "IMPORTANT": "#E67E22",
    "QUALITY":   "#8E44AD",
}


def _render_current_fields(fields: list, total_max: float, is_closed: bool, campaign_id: str):
    section_header("📋 Current Template Fields")

    if not fields:
        st.info("No fields defined yet. Use **Upload Template**, **Add Field**, or a **Preset**.")
        return

    # Detect if this is a Convin Sense template
    uses_convin_sense = any(f.get("tier") == "CRITICAL" for f in fields)

    if uses_convin_sense:
        _render_convin_sense_fields(fields, is_closed, campaign_id)
    else:
        _render_legacy_fields(fields, total_max, is_closed, campaign_id)


def _render_convin_sense_fields(fields: list, is_closed: bool, campaign_id: str):
    """Display fields grouped by TIER for Convin Sense templates."""
    from collections import defaultdict

    TIER_ORDER = ["CRITICAL", "IMPORTANT", "QUALITY"]
    by_tier: dict = defaultdict(list)
    for f in fields:
        t = f.get("tier") or "IMPORTANT"
        by_tier[t].append(f)

    total_weight = sum(f.get("weight_percent") or 0 for f in fields if not f.get("is_fatal"))

    for tier in TIER_ORDER:
        tier_fields = by_tier.get(tier, [])
        if not tier_fields:
            continue
        color = _TIER_COLORS_T.get(tier, "#7F8C8D")
        non_fatal = [f for f in tier_fields if not f.get("is_fatal")]
        fatal     = [f for f in tier_fields if f.get("is_fatal")]
        tier_w    = sum(f.get("weight_percent") or 0 for f in non_fatal)
        st.markdown(
            f'<div style="background:{color}20;border-left:4px solid {color};'
            f'padding:0.3rem 0.8rem;border-radius:0 6px 6px 0;margin:0.8rem 0 0.3rem;'
            f'font-weight:700;font-size:0.88rem;color:{color};">'
            f'{tier}  <span style="font-weight:400;color:#7F8C8D;">'
            f'({len(tier_fields)} params · {tier_w:.0f}% weight'
            f'{" + " + str(len(fatal)) + " FATAL" if fatal else ""})</span></div>',
            unsafe_allow_html=True,
        )

        col_h = st.columns([0.4, 3.0, 1.0, 1.2, 1.0, 0.6, 0.6])
        col_h[0].markdown("**#**")
        col_h[1].markdown("**Parameter**")
        col_h[2].markdown("**Weight**")
        col_h[3].markdown("**Response**")
        col_h[4].markdown("**Pass When**")
        col_h[5].markdown("**Edit**")
        col_h[6].markdown("**Del**")

        for field in tier_fields:
            fid      = field["field_id"]
            weight   = field.get("weight_percent") or 0
            is_fatal = bool(int(field.get("is_fatal") or 0))
            resp     = (field.get("response_type") or "YES_NO").replace("_", "/")
            pass_val = field.get("pass_value") or "Yes"
            param_no = field.get("no", "")

            c0, c1, c2, c3, c4, c5, c6 = st.columns([0.4, 3.0, 1.0, 1.2, 1.0, 0.6, 0.6])
            with c0:
                st.markdown(f"`{param_no}`")
            with c1:
                st.markdown(f"**{field['field_name']}**")
                st.caption(f"`{fid}`")
            with c2:
                if is_fatal:
                    st.markdown(
                        '<span style="background:#E74C3C;color:white;padding:1px 6px;'
                        'border-radius:4px;font-size:0.72rem;">FATAL</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"`{weight:.0f}%`")
                    bar_w = min(weight / max(total_weight, 1) * 100 * 4, 100)
                    st.markdown(
                        f'<div style="background:#ECF0F1;border-radius:4px;height:5px;">'
                        f'<div style="width:{bar_w:.0f}%;background:{color};'
                        f'height:5px;border-radius:4px;"></div></div>',
                        unsafe_allow_html=True,
                    )
            with c3:
                st.markdown(f"`{resp}`")
            with c4:
                st.markdown(f"`{pass_val}`")
            with c5:
                if not is_closed:
                    if st.button("✏️", key=f"edit_btn_{fid}", help="Edit"):
                        st.session_state[f"editing_{fid}"] = True
            with c6:
                if not is_closed:
                    if st.button("🗑️", key=f"del_{fid}", help="Delete"):
                        delete_template_field(fid)
                        st.rerun()

            if not is_closed and st.session_state.get(f"editing_{fid}"):
                with st.form(f"edit_form_{fid}"):
                    ea, eb, ec, ed = st.columns([2.5, 1.0, 1.2, 1.0])
                    with ea:
                        new_name = st.text_input("Parameter Name", value=field["field_name"])
                    with eb:
                        new_w = st.number_input("Weight %", 0.0, 100.0,
                                                float(weight), 0.5)
                    with ec:
                        rt_opts = ["YES_NO", "YES_NO_NA", "NO_FATAL"]
                        cur_rt  = field.get("response_type") or "YES_NO"
                        new_rt  = st.selectbox("Response Type", rt_opts,
                                               index=rt_opts.index(cur_rt) if cur_rt in rt_opts else 0)
                    with ed:
                        pv_opts = ["Yes", "No"]
                        cur_pv  = field.get("pass_value") or "Yes"
                        new_pv  = st.selectbox("Pass When", pv_opts,
                                               index=pv_opts.index(cur_pv) if cur_pv in pv_opts else 0)
                    edc1, edc2 = st.columns(2)
                    with edc1:
                        if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                            update_template_field(
                                fid, new_name.strip(), new_w,
                                field.get("field_category", "General"),
                                field.get("tier", "IMPORTANT"),
                                new_w, new_rt,
                                int(field.get("is_fatal") or 0), new_pv,
                            )
                            st.session_state.pop(f"editing_{fid}", None)
                            st.rerun()
                    with edc2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop(f"editing_{fid}", None)
                            st.rerun()

    st.divider()
    fatal_count = sum(1 for f in fields if f.get("is_fatal"))
    weighted    = [f for f in fields if not f.get("is_fatal")]
    tw          = sum(f.get("weight_percent") or 0 for f in weighted)
    st.markdown(
        f"**{len(fields)} parameters** · {len(weighted)} weighted ({tw:.0f}% total) · "
        f"{fatal_count} FATAL auto-fail · Pass threshold: **80%**"
    )


def _render_legacy_fields(fields: list, total_max: float, is_closed: bool, campaign_id: str):
    """Legacy display for numeric-scored templates (grouped by category)."""
    from collections import defaultdict

    by_cat: dict = defaultdict(list)
    for f in fields:
        cat = f.get("field_category") or "General"
        by_cat[cat].append(f)

    for cat, cat_fields in by_cat.items():
        color = _CAT_COLORS.get(cat, "#7F8C8D")
        st.markdown(
            f'<div style="background:{color}20;border-left:4px solid {color};'
            f'padding:0.3rem 0.8rem;border-radius:0 6px 6px 0;margin:0.6rem 0 0.3rem;'
            f'font-weight:600;font-size:0.88rem;color:{color};">'
            f'🏷️ {cat}  <span style="font-weight:400;color:#7F8C8D;">'
            f'({len(cat_fields)} field{"s" if len(cat_fields) != 1 else ""})</span></div>',
            unsafe_allow_html=True,
        )

        col_h = st.columns([2.8, 1.5, 1.8, 0.7, 0.7])
        col_h[0].markdown("**Field Name**")
        col_h[1].markdown("**Max Score**")
        col_h[2].markdown("**Weight**")
        col_h[3].markdown("**Edit**")
        col_h[4].markdown("**Del**")

        for field in cat_fields:
            fid    = field["field_id"]
            weight = round(field["max_score"] / total_max * 100, 1) if total_max else 0
            c1, c2, c3, c4, c5 = st.columns([2.8, 1.5, 1.8, 0.7, 0.7])
            with c1:
                st.markdown(f"**{field['field_name']}**")
                st.caption(f"`{fid}`")
            with c2:
                st.markdown(f"`{field['max_score']:.0f} pts`")
            with c3:
                st.markdown(f"`{weight:.1f}%`")
                st.markdown(
                    f'<div style="background:#ECF0F1;border-radius:4px;height:7px;">'
                    f'<div style="width:{min(weight,100):.0f}%;background:{color};'
                    f'height:7px;border-radius:4px;"></div></div>',
                    unsafe_allow_html=True,
                )
            with c4:
                if not is_closed:
                    if st.button("✏️", key=f"edit_btn_{fid}", help="Edit this field"):
                        st.session_state[f"editing_{fid}"] = True
            with c5:
                if not is_closed:
                    if st.button("🗑️", key=f"del_{fid}", help="Delete this field"):
                        delete_template_field(fid)
                        st.rerun()

            if not is_closed and st.session_state.get(f"editing_{fid}"):
                with st.form(f"edit_form_{fid}"):
                    ea, eb, ec = st.columns([2.8, 1.2, 1.8])
                    with ea:
                        new_name = st.text_input("Field Name", value=field["field_name"])
                    with eb:
                        new_score = st.number_input("Max Score", 1.0, 100.0,
                                                    float(field["max_score"]), 0.5)
                    with ec:
                        cats = [e.value for e in FieldCategory]
                        cur_cat = field.get("field_category") or "General"
                        new_cat = st.selectbox("Category", cats,
                                               index=cats.index(cur_cat) if cur_cat in cats else 0)
                    ed1, ed2 = st.columns(2)
                    with ed1:
                        if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                            update_template_field(fid, new_name.strip(), new_score, new_cat)
                            st.session_state.pop(f"editing_{fid}", None)
                            st.rerun()
                    with ed2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop(f"editing_{fid}", None)
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
    col_csv, col_xlsx, col_tsv, col_json = st.columns(4)

    with col_csv:
        csv_bytes = df.to_csv(index=False).encode()
        st.download_button(
            "⬇️ CSV",
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
            "⬇️ Excel",
            data=xlsx_bytes,
            file_name=f"{safe_name}_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_tsv:
        tsv_bytes = df.to_csv(sep="\t", index=False).encode()
        st.download_button(
            "⬇️ TSV",
            data=tsv_bytes,
            file_name=f"{safe_name}_template.tsv",
            mime="text/tab-separated-values",
            use_container_width=True,
        )

    with col_json:
        fields_list = [
            {"field_name": f["field_name"], "max_score": f["max_score"],
             "field_category": f.get("field_category", "General")}
            for f in fields
        ]
        json_bytes = json.dumps(fields_list, indent=2).encode()
        st.download_button(
            "⬇️ JSON",
            data=json_bytes,
            file_name=f"{safe_name}_template.json",
            mime="application/json",
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
