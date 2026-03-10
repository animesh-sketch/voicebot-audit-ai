"""
pages/call_import.py — Call Import System: CSV upload, manual entry, and API simulation.
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from database.db_manager import (
    get_all_campaigns, create_call, bulk_import_calls,
    get_calls_for_campaign, get_campaign,
)
from database.models import LeadCategory
from utils import page_header, section_header, kpi_card, badge, info_banner, nav

_CSV_TEMPLATE = """call_link,duration,timestamp,transcript,lead_category
https://example.com/call/001,180,2025-03-01 10:00:00,"Bot: Hello! How can I help? Customer: Hi I need info about your service.",HOT_LEAD
https://example.com/call/002,240,2025-03-01 11:00:00,"Bot: Good morning! Customer: I want to cancel my subscription.",COLD_LEAD
"""


def render():
    page_header("📥 Call Import System", "Import voice-bot calls via CSV, manual entry, or simulated API")

    campaigns = get_all_campaigns()
    active = [c for c in campaigns if c["status"] not in ("CLOSED",)]
    if not active:
        info_banner("No active campaigns found", "Create a campaign first before importing calls.")
        if st.button("➕ Create Campaign", type="primary"):
            nav("campaigns")
        return

    camp_opts = {f"{c['campaign_name']} ({c['campaign_id']})": c["campaign_id"] for c in active}
    presel = st.session_state.get("selected_campaign_id")
    default_idx = 0
    if presel:
        vals = list(camp_opts.values())
        if presel in vals:
            default_idx = vals.index(presel)

    chosen_key = st.selectbox("Select Campaign", list(camp_opts.keys()), index=default_idx)
    campaign_id = camp_opts[chosen_key]
    st.session_state["selected_campaign_id"] = campaign_id
    campaign = get_campaign(campaign_id)

    calls = get_calls_for_campaign(campaign_id)
    existing = len(calls)

    # ── Current campaign stats ────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1: kpi_card("Calls in Campaign", str(existing), color="#2980B9")
    with c2: kpi_card("Audited",           str(sum(1 for c in calls if c.get("audit_id"))), color="#27AE60")
    with c3: kpi_card("Pending Audit",     str(sum(1 for c in calls if not c.get("audit_id"))), color="#F39C12")

    st.markdown("---")
    tab_csv, tab_manual, tab_api = st.tabs(["📂 CSV Upload", "✏️ Manual Entry", "🔌 API Simulation"])

    # ── Tab 1: CSV Upload ─────────────────────────────────────────
    with tab_csv:
        section_header("Import Calls from CSV")
        st.markdown(
            "**Required columns:** `call_link`, `duration`, `timestamp`, `transcript`, `lead_category`  \n"
            "**Optional columns:** any extra columns will be ignored."
        )
        col_dl, col_info = st.columns([1, 2])
        with col_dl:
            st.download_button(
                "⬇️ Download CSV Template",
                data=_CSV_TEMPLATE,
                file_name="call_import_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_info:
            st.info(f"Lead categories: {', '.join(e.value for e in LeadCategory)}")

        uploaded = st.file_uploader("Upload CSV file", type=["csv"], key="csv_upload")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.success(f"✅ Loaded {len(df)} rows. Preview:")
                st.dataframe(df.head(5), use_container_width=True)

                # Validate columns
                required = {"call_link", "duration", "timestamp"}
                missing  = required - set(df.columns)
                if missing:
                    st.error(f"Missing required columns: {missing}")
                else:
                    col_prev, col_imp = st.columns(2)
                    with col_imp:
                        if st.button("📥 Import All Rows", type="primary", use_container_width=True):
                            with st.spinner(f"Importing {len(df)} calls..."):
                                count = bulk_import_calls(campaign_id, df)
                            st.success(f"✅ Imported {count} calls into **{campaign['campaign_name']}**!")
                            st.rerun()
            except Exception as e:
                st.error(f"CSV parse error: {e}")

    # ── Tab 2: Manual Entry ───────────────────────────────────────
    with tab_manual:
        section_header("Add Single Call Manually")
        with st.form("manual_call_form"):
            call_link  = st.text_input("Call Recording Link", placeholder="https://storage.example.com/call-001.mp3")
            col_a, col_b = st.columns(2)
            with col_a:
                dur_min = st.number_input("Duration (minutes)", 0, 120, 3)
                dur_sec = st.number_input("Duration (seconds)", 0, 59, 30)
            with col_b:
                ts = st.date_input("Call Date")
                lead_cat = st.selectbox("Lead Category", [e.value for e in LeadCategory])

            transcript = st.text_area(
                "Transcript",
                placeholder="Bot: Hello! How can I help you today?\nCustomer: Hi, I'm interested in...",
                height=160,
            )
            submitted = st.form_submit_button("➕ Add Call", type="primary", use_container_width=True)
            if submitted:
                cid = create_call(
                    campaign_id=campaign_id,
                    call_link=call_link or "",
                    duration=dur_min * 60 + dur_sec,
                    timestamp=str(ts),
                    transcript=transcript or "",
                    lead_category=lead_cat,
                )
                st.success(f"✅ Call added! ID: `{cid}`")
                st.rerun()

    # ── Tab 3: API Simulation ─────────────────────────────────────
    with tab_api:
        section_header("Simulated API Import")
        st.markdown(
            "In production, connect your telephony platform (Twilio, AWS Connect, etc.) "
            "to push calls via webhook. Below is a simulated batch import."
        )
        st.code("""
# Webhook payload format (POST /api/calls/import)
{
  "campaign_id": "CAMP-XXXXXXXX",
  "calls": [
    {
      "call_link":     "https://cdn.voicebot.io/calls/abc123.mp3",
      "duration":       185,
      "timestamp":     "2025-03-10T14:30:00Z",
      "transcript":    "Bot: Hello!\\nCustomer: Hi...",
      "lead_category": "WARM_LEAD"
    }
  ]
}
""", language="json")

        n_calls = st.slider("Number of simulated calls to generate", 1, 50, 10)
        if st.button("🚀 Simulate API Import", type="primary"):
            import random, uuid as _uuid
            from datetime import timedelta
            DEMO_TRANSCRIPTS = [
                "Bot: Hello! Thanks for calling. May I know your name?\nCustomer: Hi, I'm Alex Turner.\nBot: Great, Alex! How can I help you today?\nCustomer: I'm interested in your enterprise plan.\nBot: Excellent! Could I get your email address?\nCustomer: alex.t@corp.com\nBot: Thank you! Our team will reach out within 24 hours.",
                "Bot: Good afternoon! How can I assist you?\nCustomer: I want to cancel my subscription.\nBot: I understand you'd like to make changes. How can I assist?\nCustomer: CANCEL. C-A-N-C-E-L.\nBot: I understand you'd like to make changes. How can I assist?\nCustomer: This bot keeps repeating itself!",
                "Bot: Hi! TechBot here. What can I do for you?\nCustomer: I'm calling about a billing issue.\nBot: Sure! Could I have your account number?\nCustomer: It's 78934.\nBot: Please wait while I check...\nCustomer: Hello? Are you there?\nBot: One moment please...\nCustomer: This is taking forever.",
                "Bot: Hello! May I have your name?\nCustomer: Maria Santos.\nBot: Hi Maria! How can I help?\nCustomer: I need info about your health plan.\nBot: Our health plan covers dental, vision, and medical. Could I get your email?\nCustomer: maria.s@health.com\nBot: Perfect! You'll receive a detailed proposal within 2 business days. Anything else?\nCustomer: No, that's all. Thank you!\nBot: Thank you, Maria! Have a great day!",
                "Bot: Good morning! How can I help?\nCustomer: Hola, ¿habla español?\nBot: Hello! How can I help you today?\nCustomer: Español por favor. ¿Puedes hablar español?\nBot: I can see you're interested in our services.\nCustomer: No comprendo. Adiós.",
            ]
            LEAD_CATS = [e.value for e in LeadCategory]
            base_date = datetime(2025, 1, 10)
            with st.spinner(f"Simulating {n_calls} API call(s)..."):
                for i in range(n_calls):
                    transcript = random.choice(DEMO_TRANSCRIPTS)
                    create_call(
                        campaign_id=campaign_id,
                        call_link=f"https://api.voicebot.io/calls/{_uuid.uuid4().hex[:8]}",
                        duration=random.randint(45, 420),
                        timestamp=str(base_date + timedelta(days=random.randint(0, 60))),
                        transcript=transcript,
                        lead_category=random.choice(LEAD_CATS),
                    )
            st.success(f"✅ {n_calls} simulated calls imported into **{campaign['campaign_name']}**!")
            st.rerun()

    # ── Call list ─────────────────────────────────────────────────
    st.markdown("---")
    section_header(f"📞 All Calls in Campaign ({len(get_calls_for_campaign(campaign_id))} total)")
    calls = get_calls_for_campaign(campaign_id)
    if calls:
        rows = []
        for c in calls:
            rows.append({
                "Call ID":   c["call_id"],
                "Link":      (c.get("call_link") or "—")[:45],
                "Duration":  f"{(c.get('duration') or 0) // 60}m {(c.get('duration') or 0) % 60}s",
                "Date":      (c.get("timestamp") or "—")[:10],
                "Lead":      c.get("lead_category", "UNKNOWN"),
                "Audited":   "✅" if c.get("audit_id") else "⏳",
                "Score":     f"{c['percentage_score']:.1f}%" if c.get("percentage_score") else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if st.button("✍️ Go to Audit Interface →", use_container_width=False):
            nav("call_audit", selected_campaign_id=campaign_id)
