# 🎙️ VoiceBot Audit AI

> **MVP SaaS platform for auditing AI voice-bot calls and generating campaign-level intelligence reports.**

Built with Python · Streamlit · SQLite · Plotly · ReportLab

---

## Features

| Module | Description |
|--------|-------------|
| **Campaign Management** | Create campaigns, track status (ACTIVE → IN_PROGRESS → READY_TO_CLOSE → CLOSED) |
| **Call Import System** | CSV upload, manual entry, or simulated API batch import |
| **Audit Template Builder** | Per-campaign custom scoring fields with weights and live preview |
| **Call Audit Interface** | Colour-coded transcript viewer, slider scorecard, issue tagging |
| **Progress Tracker** | Live completion %, auto status updates |
| **Campaign Close Engine** | Gated close (100% audited required), locks entries, triggers full pipeline |
| **Bot Failure Intelligence** | 8-type NLP failure detector (Latency, Hallucination, Entity Capture, Intent Misclassification, Conversation Drop, Loop Response, Language Detection, Closure Failure) |
| **Analytics Engine** | QA scores, failure distribution, entity accuracy, lead classification, duration analysis |
| **Dashboard** | 6 KPIs, failure chart, status donut, lead pie, campaign score comparison |
| **Action Plan Generator** | CRITICAL/HIGH/MEDIUM/LOW priority recommendations with owner + timeline |
| **PDF Report Generator** | 6-page professional PDF: cover → summary → QA → failures → entity/leads → conversation → action plan |

---

## Project Structure

```
voicebot_audit_ai/
├── app.py                          # Navigation router + sidebar
├── utils.py                        # Shared CSS + UI components
├── seed_data.py                    # Demo data (3 campaigns, 33 calls)
├── requirements.txt
├── database/
│   ├── models.py                   # Enums, constants, thresholds
│   └── db_manager.py               # SQLite CRUD (7 tables)
├── analytics/
│   ├── failure_engine.py           # Rule-based NLP failure detector
│   ├── insight_engine.py           # Campaign analytics aggregator
│   └── action_plan_generator.py    # Priority recommendation engine
├── reports/
│   └── report_generator.py         # ReportLab + Matplotlib PDF builder
└── pages/
    ├── dashboard.py                # Platform overview
    ├── campaigns.py                # Campaign CRUD + close workflow
    ├── call_import.py              # Call import interface
    ├── audit_template.py           # Custom field builder
    ├── call_audit.py               # Audit scorecard interface
    └── insights.py                 # 6-tab insights dashboard
```

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/animesh-sketch/voicebot-audit-ai.git
cd voicebot-audit-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Load demo data (3 campaigns, 2 pre-closed with full insights)
python seed_data.py

# 4. Run the app
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io)
- **Database:** SQLite via `sqlite3`
- **Data Processing:** [Pandas](https://pandas.pydata.org)
- **Charts:** [Plotly](https://plotly.com/python/) + [Matplotlib](https://matplotlib.org)
- **PDF Reports:** [ReportLab](https://www.reportlab.com)

---

## Bot Failure Categories Detected

| Failure Type | Detection Method |
|---|---|
| Latency Failure | Bot wait-message keywords + customer frustration signals |
| Hallucination | Customer correction phrases ("that's wrong", "incorrect info") |
| Entity Capture Failure | Repeated clarification requests + customer frustration |
| Intent Misclassification | Customer correction phrases ("no I meant", "that's not what I asked") |
| Conversation Drop | Short duration, few turns, abrupt transcript end |
| Loop Response | Sequence-matcher similarity > 78% across bot turns |
| Language Detection Failure | Non-English phrases without bot acknowledgement |
| Closure Failure | Missing farewell/closing phrases in final bot turns |

---

## Screenshots

> Dashboard · Campaign Management · Call Audit Interface · Insights Dashboard · PDF Report

---

## License

MIT
