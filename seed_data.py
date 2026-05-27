"""
seed_data.py — Populates VoiceBot Audit AI with realistic demo data.
4 campaigns · 50+ calls · 30+ audits · 3 closed campaigns with full insights.
Ferry/Transport campaign added to demonstrate domain-specific entity capture fields.
"""
import os
import random
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from database.db_manager import (
    init_db, create_campaign, create_call, add_template_field,
    submit_audit, get_template_fields, get_calls_for_campaign,
    close_campaign, get_campaign_progress,
)
from analytics.insight_engine import generate_campaign_insights

random.seed(99)

# ─────────────────────────── Transcripts ─────────────────────────

TRANSCRIPTS = [
    # 0 — Good call, full entity capture
    """Bot: Hello! Thank you for calling TechSolutions. I'm your AI assistant. May I have your name please?
Customer: Hi, I'm Sarah Johnson.
Bot: Hi Sarah! Great to connect with you. How can I assist you today?
Customer: I'm looking for information about your enterprise software package.
Bot: Excellent choice, Sarah! Our enterprise package starts at $299 per month and includes unlimited users, advanced analytics, and 24/7 priority support. May I get your email to send a detailed proposal?
Customer: Sure, it's sarah.j@techcorp.com
Bot: Perfect! And a phone number where our team can reach you?
Customer: Yes, 555-123-4567.
Bot: Great. I've captured your contact details — sarah.j@techcorp.com and 555-123-4567. Our sales team will contact you within 24 hours. Is there anything else I can help you with?
Customer: No, that's all. Thanks!
Bot: Thank you for calling TechSolutions, Sarah. Have a wonderful day!""",

    # 1 — Good call 2
    """Bot: Good morning! TechSolutions AI here. May I know your name?
Customer: Hello, I'm Dr. Emily Chen.
Bot: Good morning, Dr. Chen! How can I help you today?
Customer: We're a healthcare clinic of 50 doctors looking for a management solution.
Bot: That's wonderful! We have a specialised healthcare module with full HIPAA compliance. Could I have your clinic name and contact number?
Customer: Riverside Medical Centre. My number is 555-987-6543.
Bot: Thank you, Dr. Chen. And your email for a customised proposal?
Customer: emily.chen@riversidemedical.com
Bot: Excellent! I've noted your details — Riverside Medical Centre, 555-987-6543. Our healthcare specialist will reach out within 24 hours.
Customer: Perfect. Thank you.
Bot: Thank you for calling, Dr. Chen! Have a great day!""",

    # 2 — Latency failure
    """Bot: Good afternoon, TechSolutions AI assistant. How may I help you?
Customer: Hi, I want to upgrade my subscription.
Bot: Please wait while I look up your account...
Customer: Hello? Anyone there?
Bot: I apologize for the delay. I'm still processing your request, please wait...
Customer: This is taking way too long.
Bot: I'm sorry about that. One moment please while the system loads...
Customer: Forget it. This bot is useless.
Bot: I apologize for the inconvenience. Your upgrade request has been noted.""",

    # 3 — Loop response (same bot turn repeated)
    """Bot: Hello! TechSolutions support. How can I help you today?
Customer: I need to cancel my subscription please.
Bot: I understand you'd like to make changes to your account. How can I assist you today?
Customer: I said CANCEL. Cancel my subscription.
Bot: I understand you'd like to make changes to your account. How can I assist you today?
Customer: Are you serious? CANCEL! C-A-N-C-E-L!
Bot: I understand you'd like to make changes to your account. How can I assist you today?
Customer: I give up. Goodbye.
Bot: Thank you for calling. Is there anything else I can help you with?""",

    # 4 — Hallucination
    """Bot: Hello! Thanks for calling TechSolutions. How can I help?
Customer: What are your support hours?
Bot: Our support team is available 24 hours a day, 7 days a week, 365 days a year.
Customer: That's wrong. Your website says support is only Monday to Friday, 9 AM to 6 PM.
Bot: I apologize for any confusion. Our standard support is Monday to Friday.
Customer: You just told me 24/7. That's completely wrong information.
Bot: You're correct. I apologize for the incorrect information earlier. Support hours are Monday to Friday, 9 AM to 6 PM.
Customer: I cannot trust what this bot tells me.
Bot: I understand your concern. I'm sorry for the confusion.""",

    # 5 — Entity capture failure
    """Bot: Hello! May I have your name please?
Customer: It's Mike Davidson.
Bot: I'm sorry, could you repeat that?
Customer: Mike Davidson.
Bot: Could you spell your last name for me?
Customer: D-A-V-I-D-S-O-N.
Bot: I didn't quite catch that. Could you say your name one more time?
Customer: I've said my name three times already. Mike Davidson!
Bot: I apologize. Mike, could you repeat your last name once more?
Customer: Forget this. I'll call back later. Goodbye.""",

    # 6 — Conversation drop (short)
    """Bot: Hello! TechSolutions AI. How can I help?
Customer: Hi yes I'm calling about a billing issue.
Bot: I'd be happy to help with your billing inquiry. Could you provide your account number?
Customer: Sure it's""",

    # 7 — Intent misclassification
    """Bot: Hi there! TechSolutions assistant. How can I help?
Customer: I'd like to get a refund for my last payment.
Bot: I'd be happy to help you upgrade your subscription! Which plan are you interested in?
Customer: No, I said REFUND. I want my money back.
Bot: Great! Our premium plan offers many additional features. Let me tell you about them.
Customer: That's not what I'm asking about. I need a REFUND.
Bot: I understand you're interested in our products. Let me connect you with our sales team.
Customer: This bot doesn't understand anything. I need a supervisor.""",

    # 8 — Language detection failure
    """Bot: Hello! TechSolutions virtual assistant. How can I help you?
Customer: Hola, ¿habla español? No hablo inglés bien.
Bot: Hello! How can I help you today?
Customer: Español por favor. ¿Puedes hablar español?
Bot: I can see you're interested in our services. What would you like to know?
Customer: No entiendo. ¿Habla español?
Bot: Our team will be happy to assist you. Is there anything else I can help you with?
Customer: No comprendo. Necesito ayuda en español. Adiós.""",

    # 9 — Closure failure
    """Bot: Hello! What's your name?
Customer: John Williams.
Bot: Hi John! How can I help?
Customer: I'm interested in your basic plan.
Bot: Our basic plan is $49 per month with 5 users.
Customer: That sounds good. Can you send me info?
Bot: Sure, what's your email?
Customer: john.w@email.com
Bot: Got it. We'll send you information.
Customer: Will I hear from you soon?
Bot: Yes within 2 days.""",

    # 10 — Good call 3 (startup)
    """Bot: Hello! TechSolutions here. How can I assist you?
Customer: Hi, I saw your ad about the startup package.
Bot: Great! You're interested in our startup package. May I have your name?
Customer: James Kowalski.
Bot: Hi James! Our startup package is ideal for teams up to 10, at $99 per month. Could I have your email?
Customer: james.k@startupxyz.com
Bot: Perfect, James! Would you like to start with a free 14-day trial?
Customer: Yes, definitely!
Bot: Wonderful! I'll set up a trial for james.k@startupxyz.com. You'll receive login details within the hour. Anything else?
Customer: No, that's great. Thanks!
Bot: Thank you for calling, James! Enjoy your trial and have a great day!""",

    # 11 — Good call 4 (analytics enquiry)
    """Bot: Thank you for calling TechSolutions. How can I help you today?
Customer: Hi, I'm calling about your analytics features.
Bot: Of course! May I have your name and company?
Customer: I'm Robert Park from DataDriven Inc.
Bot: Hi Robert! TechSolutions offers real-time dashboards, custom reports, and predictive insights. What specific analytics are you looking for?
Customer: We need advanced reporting and data export.
Bot: Those are standard in our Professional tier at $199 per month. Would you like a demo?
Customer: Yes, that would be great.
Bot: Excellent! Your email for the demo invitation?
Customer: robert.park@datadriven.com
Bot: Done! You'll receive a calendar invite within 24 hours for a personalised demo.
Customer: Thank you very much.
Bot: Thank you for calling, Robert! Looking forward to showing you our platform. Have a great day!""",

    # 12 — Partial failure (latency + OK resolution)
    """Bot: Hello! TechSolutions AI. How can I assist you?
Customer: Hi, I need help with my account password reset.
Bot: I'd be happy to help. May I verify your account email?
Customer: It's mark.jones@email.com
Bot: Please wait while I process this...
Customer: Okay.
Bot: I've sent a reset link to mark.jones@email.com. You should receive it within 5 minutes.
Customer: I'm not getting it.
Bot: Let me try resending it. Please wait...
Customer: Still nothing.
Bot: I apologize for the inconvenience. Please check your spam folder, or I can escalate this to our technical team.
Customer: Okay, please escalate.
Bot: Done! Our technical team will contact you at mark.jones@email.com within 2 hours. Thank you for your patience!""",

    # 13 — Healthcare good call
    """Bot: Good morning! HealthBot AI. How can I help you today?
Customer: Hi, I need to schedule an appointment.
Bot: I'd be happy to help. May I have your full name?
Customer: Patricia Williams.
Bot: Thank you, Patricia! Could you provide your date of birth for verification?
Customer: March 15, 1985.
Bot: Got it. And your preferred appointment date?
Customer: Next Tuesday afternoon if possible.
Bot: I have an opening on Tuesday at 2:30 PM. Would that work?
Customer: Yes, perfect.
Bot: Great! I've booked Tuesday at 2:30 PM for Patricia Williams. You'll receive a confirmation SMS. Is there anything else?
Customer: No, that's all. Thanks!
Bot: Thank you, Patricia! See you Tuesday. Have a healthy day!""",

    # 14 — Healthcare latency
    """Bot: Good morning! HealthBot AI. How can I help?
Customer: Hi I need to reschedule my appointment.
Bot: Please wait while I access your records...
Customer: Hello? Are you still there?
Bot: One moment please...
Customer: This is taking too long.
Bot: I apologize. I can see your appointment for Monday. Would you like to move it?
Customer: Yes, to Wednesday please.
Bot: Processing that change. Please wait...
Customer: Still waiting...
Bot: I apologize for the delay. Your appointment has been moved to Wednesday. Thank you for your patience.""",

    # 15 — Healthcare entity fail
    """Bot: Good afternoon! HealthBot AI. May I have your name?
Customer: Jennifer Martinez.
Bot: I'm sorry, could you repeat that?
Customer: Jennifer Martinez.
Bot: Could you spell that?
Customer: J-E-N-N-I-F-E-R M-A-R-T-I-N-E-Z.
Bot: I didn't catch your first name. Could you say it again?
Customer: Jennifer! I've said it three times now.
Bot: I apologize. Jennifer, your last name please?
Customer: This is ridiculous. Goodbye.""",

    # 16 — Finance good call
    """Bot: Hello! FinanceBot here. How can I assist you today?
Customer: Hi, I'm interested in a mortgage pre-approval.
Bot: Great! I can help with that. May I have your full name?
Customer: David Thompson.
Bot: Hi David! For a mortgage pre-approval, I'll need some basic financial information. What's your annual household income?
Customer: Around $85,000.
Bot: Thank you. And the property value you're looking at?
Customer: About $350,000.
Bot: Perfect. Based on those figures, you may qualify for a mortgage. Your email for the pre-approval application?
Customer: david.t@personalmail.com
Bot: Thank you, David! A pre-approval specialist will contact you at david.t@personalmail.com within 24 hours. Is there anything else?
Customer: No, that covers it.
Bot: Thank you for calling FinanceBot, David! Have a wonderful day!""",

    # 17 — Finance loop
    """Bot: Hello! FinanceBot. How can I help?
Customer: I want to check my loan status.
Bot: I'd be happy to help you with your financial needs today. What service are you looking for?
Customer: My LOAN STATUS. Loan number 789456.
Bot: I'd be happy to help you with your financial needs today. What service are you looking for?
Customer: Are you broken? LOAN STATUS. L-O-A-N STATUS!
Bot: I'd be happy to help you with your financial needs today. What service are you looking for?
Customer: Unbelievable. Transferring to a human. Goodbye.""",

    # 18 — Finance hallucination
    """Bot: Good afternoon! FinanceBot. How can I help?
Customer: What's the current fixed mortgage rate?
Bot: Our current fixed mortgage rate is 2.5% for a 30-year term.
Customer: That can't be right. Rates are at 6.5% right now. You're giving me wrong information.
Bot: I apologize. You're correct, our current rates are approximately 6.5% for 30-year fixed mortgages.
Customer: You told me 2.5% first. I can't rely on your rates.
Bot: I understand your concern. I apologize for the incorrect information. Current rates are 6.5%.
Customer: This bot gives wrong financial information. That's dangerous.""",
]

# ── Lead categories ────────────────────────────────────────────────
_LEADS = [
    "HOT_LEAD", "HOT_LEAD", "WARM_LEAD", "COLD_LEAD", "NOT_INTERESTED",
    "CALLBACK_REQUESTED", "WARM_LEAD", "COLD_LEAD", "WRONG_NUMBER",
    "HOT_LEAD", "HOT_LEAD", "WARM_LEAD", "WARM_LEAD",
    "HOT_LEAD", "COLD_LEAD", "NOT_INTERESTED",
    "HOT_LEAD", "COLD_LEAD", "NOT_INTERESTED",
]
_LINKS = [f"https://storage.voicebot.io/calls/{uuid.uuid4().hex[:8]}.mp3" for _ in range(len(TRANSCRIPTS))]

# ── Field definitions: (name, max_score, field_category) ──────────
_QA   = "Call Quality"
_AI   = "AI Issues"
_ENT  = "Entity Capture"
_LEAD = "Lead Classification"
_COMP = "Compliance"

TECH_FIELDS = [
    ("Greeting Quality",        10, _QA),
    ("Bot Response Latency",    10, _AI),
    ("Entity Capture",          15, _ENT),
    ("Bot Clarity",             15, _QA),
    ("Lead Qualification",      10, _LEAD),
    ("Closure Attempt",         10, _QA),
]
HEALTH_FIELDS = [
    ("Greeting & Empathy",      10, _QA),
    ("Appointment Intent",      15, _QA),
    ("Patient Name Capture",    15, _ENT),
    ("Date of Birth Capture",   10, _ENT),
    ("Scheduling Success",      10, _QA),
    ("Compliance & Disclosure", 10, _COMP),
    ("Closure",                 10, _QA),
]
FINANCE_FIELDS = [
    ("Greeting Quality",        10, _QA),
    ("Financial Needs Capture", 15, _ENT),
    ("Income Capture",          10, _ENT),
    ("Credit Qualification",    15, _LEAD),
    ("Product Matching",        10, _LEAD),
    ("Compliance Check",        15, _COMP),
    ("Closure Attempt",         10, _QA),
]
FERRY_FIELDS = [
    ("Greeting Quality",            10, _QA),
    ("Bot Latency",                 10, _AI),
    ("Hallucination Check",         10, _AI),
    ("STT Error Rate",              10, _AI),
    ("Language Switch Handling",    10, _AI),
    ("Customer Name Capture",       15, _ENT),
    ("Route Capture",               15, _ENT),
    ("Passenger Count Capture",     15, _ENT),
    ("Sailing Date Capture",        15, _ENT),
    ("Lead Classification Accuracy", 10, _LEAD),
    ("Closure & Next Steps",        10, _QA),
]


FERRY_TRANSCRIPTS = [
    # F0 — Good ferry booking call
    """Bot: Hello! Welcome to SeaLink Ferries. I'm your booking assistant. May I have your name?
Customer: Hi, it's James Thornton.
Bot: Hello James! I'd be happy to help you book a ferry. Which route are you interested in?
Customer: I'd like to book the Auckland to Waiheke Island route.
Bot: Great choice! How many passengers will be travelling?
Customer: There will be 4 of us — 2 adults and 2 children.
Bot: Perfect. And what sailing date are you looking at?
Customer: We're hoping for Saturday the 15th of March.
Bot: I have a 9:30 AM sailing on Saturday 15 March available. That's 4 passengers on the Auckland to Waiheke Island route. Shall I confirm that booking?
Customer: Yes please!
Bot: Wonderful! Booking confirmed for James Thornton — 4 passengers, Auckland to Waiheke Island, 15 March at 9:30 AM. You'll receive a confirmation email shortly. Have a great trip!""",

    # F1 — Entity capture failure (name and route repeated)
    """Bot: Welcome to SeaLink Ferries! May I have your name please?
Customer: Maria Santos.
Bot: I'm sorry, could you repeat your name?
Customer: Maria Santos.
Bot: Could you spell that for me?
Customer: M-A-R-I-A S-A-N-T-O-S. I've said it twice now.
Bot: I apologize. Maria, which route would you like to book?
Customer: Wellington to Picton.
Bot: Sorry, which route was that again?
Customer: Wellington to Picton! I've already told you the route.
Bot: I apologize for the inconvenience. Let me try again.""",

    # F2 — Latency on ferry call
    """Bot: Hello! SeaLink Ferries booking service. How can I help?
Customer: I want to book a ferry for tomorrow.
Bot: Of course! Please wait while I check availability...
Customer: Hello? Are you still there?
Bot: One moment please, checking sailings...
Customer: This is taking too long.
Bot: I apologize for the delay. I can see sailings for tomorrow. What route would you like?
Customer: Auckland to Waiheke.
Bot: Please wait while I process that route...
Customer: Still waiting...
Bot: I have a 10 AM sailing available. How many passengers?""",

    # F3 — Good call with language switch
    """Bot: Welcome to SeaLink Ferries! How can I help you today?
Customer: Kia ora, ko Thomas toku ingoa. I need to book a ferry.
Bot: Kia ora Thomas! I'd be happy to help. Which route would you like?
Customer: Interislander, Wellington to Picton.
Bot: Excellent! For the Wellington to Picton route, how many passengers?
Customer: Just myself — one adult.
Bot: And your preferred sailing date?
Customer: Next Friday, the 21st.
Bot: I have a 2:30 PM sailing on Friday 21st for 1 passenger on the Wellington to Picton route. Shall I confirm?
Customer: Yes, that's perfect. Thank you!
Bot: Booking confirmed for Thomas! Wellington to Picton, 21st at 2:30 PM. Have a wonderful journey!""",

    # F4 — Wrong date / hallucination
    """Bot: SeaLink Ferries, how can I help?
Customer: Hi, I want to book for the 30th of February.
Bot: Of course! I can book you for the 30th of February.
Customer: Wait, that's wrong. February doesn't have 30 days. You just confirmed an invalid date.
Bot: I apologize for the confusion. You're right, February does not have 30 days.
Customer: This bot confirmed a date that doesn't exist. That's completely wrong.
Bot: I'm sorry about that error. What sailing date would you prefer?
Customer: I don't trust your system anymore. Goodbye.""",

    # F5 — Conversation drop (very short)
    """Bot: Hello, SeaLink Ferries! May I help you book a ferry today?
Customer: Yes, I need to book 6 passengers from""",

    # F6 — Good call with full entity capture
    """Bot: Good morning! SeaLink Ferries booking assistant. May I have your name?
Customer: Sophie Williams.
Bot: Good morning Sophie! Which route are you booking for?
Customer: We need the Devonport to Auckland CBD route.
Bot: How many passengers will be travelling?
Customer: It will be 2 adults.
Bot: And the date of travel?
Customer: Wednesday the 5th of April.
Bot: Perfect. To confirm — Sophie Williams, 2 passengers, Devonport to Auckland CBD, 5th April. Shall I proceed with the booking?
Customer: Yes please.
Bot: Booking confirmed! Your reference is SEA-2046. Have a great trip, Sophie!""",

    # F7 — STT error / repeated entity
    """Bot: Welcome to SeaLink Ferries! What's your name?
Customer: It's Raj Patel.
Bot: Could you repeat that? I didn't quite catch your name.
Customer: Raj Patel.
Bot: And the route you'd like to travel?
Customer: Auckland to Waiheke Island.
Bot: Sorry, could you say the destination again?
Customer: Waiheke Island. From Auckland.
Bot: I didn't catch that. Could you spell the destination?
Customer: W-A-I-H-E-K-E. This bot can't understand basic words.
Bot: Thank you. And the number of passengers?""",
]

_FERRY_LEADS = [
    "HOT_LEAD", "COLD_LEAD", "WARM_LEAD", "HOT_LEAD",
    "NOT_INTERESTED", "UNKNOWN", "HOT_LEAD", "COLD_LEAD",
]
_FERRY_AUDIT_LEADS = [
    "HOT_LEAD", "NOT_INTERESTED", "HOT_LEAD", "HOT_LEAD",
    "NOT_INTERESTED", "UNKNOWN", "HOT_LEAD", "WARM_LEAD",
]


def _rand_scores(fields, quality: float) -> dict:
    """Generate field scores for a call with given quality (0–1)."""
    scores = {}
    for f in fields:
        noise = random.gauss(0, 0.12)
        eff   = min(1.0, max(0.05, quality + noise))
        scores[f["field_id"]] = round(eff * f["max_score"], 1)
    return scores


def _rand_tags(quality: float) -> list:
    tags = []
    if quality < 0.5 and random.random() > 0.5:
        tags.append(random.choice(["Latency", "Hallucination", "STT Error"]))
    if quality < 0.4 and random.random() > 0.6:
        tags.append("Intent Misclassification")
    if quality < 0.35 and random.random() > 0.7:
        tags.append("Conversation Drop")
    return list(set(tags))


def _rand_date(start: datetime, days: int) -> str:
    return (start + timedelta(days=random.randint(0, days - 1))).strftime("%Y-%m-%d")


def seed():
    init_db()
    print("\n🌱  Seeding VoiceBot Audit AI demo data...\n")

    # ─── Campaign 1: TechSolutions Q1 Lead Gen (CLOSED) ──────────
    c1 = create_campaign("TechSolutions Q1 Lead Gen", "TechSolutions Inc.")
    for entry in TECH_FIELDS:
        add_template_field(c1, entry[0], float(entry[1]), entry[2])
    f1 = get_template_fields(c1)

    tech_txts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    start1    = datetime(2025, 1, 6)
    call_ids1 = []
    for i, ti in enumerate(tech_txts):
        tx    = TRANSCRIPTS[ti] if ti < len(TRANSCRIPTS) else TRANSCRIPTS[0]
        lead  = _LEADS[i % len(_LEADS)]
        dur   = random.randint(45, 420)
        cid   = create_call(c1, _LINKS[ti], dur, _rand_date(start1, 45), tx, lead)
        call_ids1.append(cid)
    print(f"  ✓ Campaign 1 — {len(call_ids1)} calls created")

    agent_qualities = [0.90, 0.88, 0.40, 0.30, 0.35, 0.25, 0.20, 0.30, 0.45, 0.85, 0.87, 0.86, 0.55]
    for cid, quality in zip(call_ids1, agent_qualities):
        scores = _rand_scores(f1, quality)
        tags   = _rand_tags(quality)
        notes  = "Good call — all entities captured." if quality > 0.7 else "Multiple issues flagged."
        submit_audit(cid, c1, random.choice(["Alice QA", "Mike Audit"]), scores, tags, notes)
    print(f"  ✓ Campaign 1 — {len(call_ids1)} audits submitted")

    close_campaign(c1)
    ins1 = generate_campaign_insights(c1)
    avg1 = ins1["campaign_summary"]["avg_qa_score"]
    fails1 = ins1["campaign_summary"]["total_failures"]
    print(f"  ✓ Campaign 1 CLOSED — avg score: {avg1:.1f}%, failures: {fails1}")

    # ─── Campaign 2: HealthCare Pro (IN_PROGRESS, partially audited) ─
    c2 = create_campaign("HealthCare Pro Patient Outreach", "HealthCare Pro Ltd.")
    for entry in HEALTH_FIELDS:
        add_template_field(c2, entry[0], float(entry[1]), entry[2])
    f2 = get_template_fields(c2)

    health_txts = [13, 14, 15, 0, 1, 10, 11, 12, 2, 4, 7, 8]
    start2 = datetime(2025, 3, 3)
    call_ids2 = []
    for i, ti in enumerate(health_txts):
        tx   = TRANSCRIPTS[ti] if ti < len(TRANSCRIPTS) else TRANSCRIPTS[13]
        lead = _LEADS[(i + 5) % len(_LEADS)]
        dur  = random.randint(60, 360)
        cid  = create_call(c2, _LINKS[ti % len(_LINKS)], dur, _rand_date(start2, 30), tx, lead)
        call_ids2.append(cid)
    print(f"  ✓ Campaign 2 — {len(call_ids2)} calls created")

    # Audit only 8 of 12 (IN_PROGRESS)
    health_qualities = [0.88, 0.35, 0.28, 0.85, 0.87, 0.82, 0.79, 0.50]
    for cid, quality in zip(call_ids2[:8], health_qualities):
        scores = _rand_scores(f2, quality)
        tags   = _rand_tags(quality)
        submit_audit(cid, c2, "Sarah QA", scores, tags, "")
    print(f"  ✓ Campaign 2 — 8/12 audits (IN_PROGRESS)")

    # ─── Campaign 3: FinanceBot Mortgage Leads (CLOSED) ──────────
    c3 = create_campaign("FinanceBot Mortgage Lead Gen", "FinanceBot Corp.")
    for entry in FINANCE_FIELDS:
        add_template_field(c3, entry[0], float(entry[1]), entry[2])
    f3 = get_template_fields(c3)

    fin_txts = [16, 17, 18, 0, 1, 3, 5, 10]
    start3 = datetime(2025, 5, 1)
    call_ids3 = []
    for i, ti in enumerate(fin_txts):
        tx   = TRANSCRIPTS[ti] if ti < len(TRANSCRIPTS) else TRANSCRIPTS[16]
        lead = _LEADS[(i + 3) % len(_LEADS)]
        dur  = random.randint(60, 480)
        cid  = create_call(c3, _LINKS[ti % len(_LINKS)], dur, _rand_date(start3, 40), tx, lead)
        call_ids3.append(cid)
    print(f"  ✓ Campaign 3 — {len(call_ids3)} calls created")

    fin_qualities = [0.87, 0.30, 0.28, 0.88, 0.89, 0.35, 0.32, 0.84]
    for cid, quality in zip(call_ids3, fin_qualities):
        scores = _rand_scores(f3, quality)
        tags   = _rand_tags(quality)
        notes  = "Finance bot compliance issue." if quality < 0.5 else ""
        submit_audit(cid, c3, random.choice(["Tom QA", "Linda Audit"]), scores, tags, notes)
    print(f"  ✓ Campaign 3 — {len(call_ids3)} audits submitted")

    close_campaign(c3)
    ins3 = generate_campaign_insights(c3)
    avg3 = ins3["campaign_summary"]["avg_qa_score"]
    fails3 = ins3["campaign_summary"]["total_failures"]
    print(f"  ✓ Campaign 3 CLOSED — avg score: {avg3:.1f}%, failures: {fails3}")

    # ─── Campaign 4: SeaLink Ferry Booking Bot (CLOSED) ──────────
    c4 = create_campaign("SeaLink Ferry Booking Audit", "SeaLink Ferries Ltd.")
    for entry in FERRY_FIELDS:
        add_template_field(c4, entry[0], float(entry[1]), entry[2])
    f4 = get_template_fields(c4)

    start4 = datetime(2025, 6, 1)
    call_ids4 = []
    for i, tx in enumerate(FERRY_TRANSCRIPTS):
        lead = _FERRY_LEADS[i % len(_FERRY_LEADS)]
        dur  = random.randint(30, 360)
        link = f"https://storage.sealink.io/calls/{uuid.uuid4().hex[:8]}.mp3"
        cid  = create_call(c4, link, dur, _rand_date(start4, 30), tx, lead)
        call_ids4.append(cid)
    print(f"  ✓ Campaign 4 — {len(call_ids4)} calls created")

    ferry_qualities = [0.92, 0.30, 0.40, 0.88, 0.28, 0.15, 0.89, 0.35]
    ferry_tags_map = [
        [],
        ["STT Error", "Intent Misclassification"],
        ["Latency"],
        [],
        ["Hallucination"],
        ["Conversation Drop"],
        [],
        ["STT Error", "Latency"],
    ]
    for idx, (cid, quality) in enumerate(zip(call_ids4, ferry_qualities)):
        scores  = _rand_scores(f4, quality)
        tags    = ferry_tags_map[idx] if idx < len(ferry_tags_map) else _rand_tags(quality)
        lac     = _FERRY_AUDIT_LEADS[idx] if idx < len(_FERRY_AUDIT_LEADS) else None
        notes   = "Full entity capture — excellent." if quality > 0.8 else "Entity capture failure noted."
        submit_audit(cid, c4, random.choice(["Anna QA", "Ben Audit"]), scores, tags, notes,
                     lead_audit_category=lac)
    print(f"  ✓ Campaign 4 — {len(call_ids4)} audits submitted")

    close_campaign(c4)
    ins4 = generate_campaign_insights(c4)
    avg4 = ins4["campaign_summary"]["avg_qa_score"]
    fails4 = ins4["campaign_summary"]["total_failures"]
    print(f"  ✓ Campaign 4 CLOSED — avg score: {avg4:.1f}%, failures: {fails4}")

    print("\n✅  Seed complete!")
    print(f"   Campaign 1: {c1} (CLOSED, avg {avg1:.1f}%)")
    print(f"   Campaign 2: {c2} (IN_PROGRESS, 8/12 audited)")
    print(f"   Campaign 3: {c3} (CLOSED, avg {avg3:.1f}%)")
    print(f"   Campaign 4: {c4} (CLOSED, avg {avg4:.1f}%)")
    print("\n   Run: streamlit run app.py\n")


if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voicebot_audit.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database.")
    seed()
