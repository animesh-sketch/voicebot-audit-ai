"""
report_generator.py — PDF Campaign Report using ReportLab + Matplotlib.
Generates a professional multi-section PDF saved to /reports/.
"""
import io
import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

REPORTS_DIR = Path(__file__).parent.parent / "reports" / "output"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Colour palette ────────────────────────────────────────────────
C_DARK       = colors.HexColor("#1C2833")
C_BLUE       = colors.HexColor("#2980B9")
C_GREEN      = colors.HexColor("#27AE60")
C_RED        = colors.HexColor("#E74C3C")
C_AMBER      = colors.HexColor("#F39C12")
C_LIGHT_GREY = colors.HexColor("#F4F6F9")
C_LIGHT_BLUE = colors.HexColor("#EBF5FB")
C_GREY       = colors.HexColor("#95A5A6")
C_WHITE      = colors.white

PRIORITY_COLORS = {
    "CRITICAL": colors.HexColor("#C0392B"),
    "HIGH":     colors.HexColor("#E74C3C"),
    "MEDIUM":   colors.HexColor("#F39C12"),
    "LOW":      colors.HexColor("#27AE60"),
}

MPL = {
    "green": "#27AE60", "red": "#E74C3C", "amber": "#F39C12",
    "blue": "#2980B9", "grey": "#95A5A6", "dark": "#1C2833",
    "purple": "#8E44AD", "teal": "#16A085",
}
FAILURE_MPL_COLORS = [
    "#E74C3C", "#F39C12", "#C0392B", "#2980B9",
    "#E67E22", "#8E44AD", "#16A085", "#95A5A6",
]


def _styles():
    s = {}
    s["cover_h1"]   = ParagraphStyle("ch1", fontSize=30, textColor=C_WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s["cover_sub"]  = ParagraphStyle("csub", fontSize=13, textColor=colors.HexColor("#BDC3C7"), fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)
    s["h1"]         = ParagraphStyle("h1",  fontSize=17, textColor=C_DARK, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=5)
    s["h2"]         = ParagraphStyle("h2",  fontSize=13, textColor=C_BLUE, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    s["body"]       = ParagraphStyle("body",fontSize=10, textColor=C_DARK, fontName="Helvetica", leading=15, spaceAfter=4)
    s["small"]      = ParagraphStyle("sm",  fontSize=8,  textColor=C_GREY, fontName="Helvetica", leading=11)
    s["bullet"]     = ParagraphStyle("blt", fontSize=9,  textColor=C_DARK, fontName="Helvetica", leading=14, leftIndent=12, spaceAfter=2)
    s["footer"]     = ParagraphStyle("ftr", fontSize=7,  textColor=C_GREY, fontName="Helvetica", alignment=TA_CENTER)
    return s


def _cover_bg(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(C_DARK)
    canvas.rect(0, h - 260, w, 260, fill=1, stroke=0)
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, h - 265, w, 8, fill=1, stroke=0)
    canvas.restoreState()


def _body_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, h - 26, w, 26, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18, h - 17, "VoiceBot Audit AI — Campaign Report")
    canvas.drawRightString(w - 18, h - 17, getattr(doc, "campaign_name", ""))
    canvas.setFillColor(C_GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w / 2, 15, f"Page {doc.page}  ·  {getattr(doc, 'gen_date', '')}")
    canvas.setStrokeColor(C_LIGHT_GREY)
    canvas.line(18, 28, w - 18, 28)
    canvas.restoreState()


def _img(fig, w=16.5, h=7) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w * cm, height=h * cm)


def _kpi_table(data: list[tuple], styles):
    n = len(data)
    col_w = [A4[0] / n - 1.2 * cm] * n
    header_row = [Paragraph(f"<b>{d[0]}</b>", styles["small"]) for d in data]
    value_row  = [Paragraph(f"<b>{d[1]}</b>",
                            ParagraphStyle("kv", fontSize=20, textColor=C_DARK,
                                           fontName="Helvetica-Bold", alignment=TA_CENTER))
                  for d in data]
    t = Table([header_row, value_row], colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT_BLUE),
        ("BACKGROUND", (0, 1), (-1, 1), C_LIGHT_GREY),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_GREY),
    ]))
    return t


# ── Matplotlib chart builders ─────────────────────────────────────

def _chart_score_dist(dist: dict):
    labels = list(dist.keys())
    counts = [dist[l] for l in labels]
    colors_list = [MPL["red"], MPL["amber"], MPL["amber"], MPL["green"], MPL["green"]][:len(labels)]
    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(labels, counts, color=colors_list, edgecolor="white", linewidth=0.8)
    for b, c in zip(bars, counts):
        if c > 0:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.1,
                    str(c), ha="center", va="bottom", fontsize=9)
    ax.set_title("QA Score Distribution", fontweight="bold")
    ax.set_xlabel("Score Band"); ax.set_ylabel("Calls")
    ax.set_facecolor("#F4F6F9"); fig.patch.set_facecolor("white")
    ax.spines[["top", "right"]].set_visible(False)
    plt.xticks(rotation=20, fontsize=8)
    fig.tight_layout()
    return fig


def _chart_failure_dist(dist: dict):
    if not dist:
        return None
    labels = list(dist.keys())
    values = [dist[l] for l in labels]
    short  = [l.replace(" Failure", "").replace(" Detection", "") for l in labels]
    fig, ax = plt.subplots(figsize=(9, max(3.5, len(labels) * 0.65)))
    bar_colors = FAILURE_MPL_COLORS[:len(labels)]
    bars = ax.barh(short, values, color=bar_colors, edgecolor="white")
    for b, v in zip(bars, values):
        ax.text(v + 0.1, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=9)
    ax.set_title("Bot Failure Distribution", fontweight="bold")
    ax.set_xlabel("Count"); ax.set_facecolor("#F4F6F9")
    fig.patch.set_facecolor("white")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def _chart_field_scores(fields: list[dict]):
    if not fields:
        return None
    names = [f["field_name"][:22] for f in fields]
    pcts  = [f["percentage"] for f in fields]
    bar_colors = [MPL["green"] if p >= 70 else MPL["amber"] if p >= 50 else MPL["red"] for p in pcts]
    fig, ax = plt.subplots(figsize=(9, max(3, len(names) * 0.6)))
    bars = ax.barh(names, pcts, color=bar_colors, edgecolor="white")
    ax.axvline(70, color=MPL["amber"], linestyle="--", linewidth=1.5, label="70% threshold")
    for b, p in zip(bars, pcts):
        ax.text(min(p + 1, 102), b.get_y() + b.get_height() / 2, f"{p:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 108)
    ax.set_title("QA Field Scores", fontweight="bold")
    ax.set_xlabel("Average Score (%)"); ax.set_facecolor("#F4F6F9")
    fig.patch.set_facecolor("white")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def _chart_lead_pie(dist: dict):
    if not dist:
        return None
    labels = list(dist.keys())
    values = [dist[l] for l in labels]
    colors_list = [
        "#E74C3C", "#F39C12", "#3498DB", "#7F8C8D",
        "#27AE60", "#9B59B6", "#BDC3C7", "#ECF0F1",
    ][:len(labels)]
    fig, ax = plt.subplots(figsize=(7, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors_list,
        autopct=lambda p: f"{p:.0f}%" if p > 3 else "",
        startangle=90, pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8)
    ax.set_title("Lead Classification", fontweight="bold")
    fig.tight_layout()
    return fig


def _chart_duration_dist(dur_dist: dict):
    if not dur_dist:
        return None
    labels = list(dur_dist.keys())
    values = [int(dur_dist[l]) for l in labels]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.bar(labels, values, color=MPL["blue"], edgecolor="white")
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + 0.1, str(v), ha="center", fontsize=9)
    ax.set_title("Call Duration Distribution", fontweight="bold")
    ax.set_xlabel("Duration Band"); ax.set_ylabel("Calls")
    ax.set_facecolor("#F4F6F9"); fig.patch.set_facecolor("white")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


# ── Action plan table ─────────────────────────────────────────────

def _action_table(plan: list[dict], styles):
    header = [
        Paragraph("<b>Priority</b>", styles["small"]),
        Paragraph("<b>Category</b>", styles["small"]),
        Paragraph("<b>Finding</b>",  styles["small"]),
        Paragraph("<b>Recommendation</b>", styles["small"]),
        Paragraph("<b>Owner</b>",    styles["small"]),
        Paragraph("<b>Timeline</b>", styles["small"]),
    ]
    rows = [header]
    for item in plan:
        pri = item["priority"]
        c   = PRIORITY_COLORS.get(pri, C_GREY)
        rows.append([
            Paragraph(f"<b>{pri}</b>",
                      ParagraphStyle("p", fontSize=8, textColor=c, fontName="Helvetica-Bold")),
            Paragraph(item.get("category", ""), styles["small"]),
            Paragraph(item.get("finding", "")[:90], styles["small"]),
            Paragraph(item.get("recommendation", "")[:110], styles["small"]),
            Paragraph(item.get("owner", ""), styles["small"]),
            Paragraph(item.get("timeline", ""), styles["small"]),
        ])
    col_w = [2 * cm, 2.5 * cm, 4.5 * cm, 5 * cm, 2.8 * cm, 1.7 * cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_LIGHT_GREY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_GREY]),
    ]))
    return t


# ── Main generator ────────────────────────────────────────────────

def generate_pdf_report(campaign: dict, insights: dict) -> bytes:
    """
    Build and return PDF bytes. Also saves to REPORTS_DIR.
    """
    sty = _styles()
    summary  = insights.get("campaign_summary", {})
    qa       = insights.get("qa_analysis", {})
    failures = insights.get("failure_analysis", {})
    leads    = insights.get("lead_classification", {})
    conv     = insights.get("conversation_analysis", {})
    entity   = insights.get("entity_accuracy", {})
    plan     = insights.get("action_plan", [])
    gen_at   = insights.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.5 * cm, bottomMargin=1.8 * cm,
    )
    doc.campaign_name = summary.get("campaign_name", campaign.get("campaign_name", ""))
    doc.gen_date      = gen_at

    cover_frame = Frame(0, 0, A4[0], A4[1], id="cover")
    body_frame  = Frame(1.6 * cm, 1.8 * cm, A4[0] - 3.2 * cm, A4[1] - 3.2 * cm, id="body")

    doc.addPageTemplates([
        PageTemplate(id="Cover",    frames=[cover_frame], onPage=_cover_bg),
        PageTemplate(id="Standard", frames=[body_frame],  onPage=_body_page),
    ])

    story = []

    # ── Cover ─────────────────────────────────────────────────────
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("VoiceBot Audit AI", sty["cover_sub"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Campaign Insight Report", sty["cover_h1"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(summary.get("campaign_name", ""), sty["cover_sub"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"Client: {summary.get('client_name', '—')}", sty["cover_sub"]))
    story.append(Spacer(1, 2 * cm))

    cover_meta = [
        ["Generated", gen_at],
        ["Total Calls",  str(summary.get("total_calls", "—"))],
        ["Audited",      str(summary.get("audited_calls", "—"))],
        ["Avg QA Score", f"{summary.get('avg_qa_score', 0):.1f}%"],
        ["Pass Rate",    f"{summary.get('pass_rate', 0):.1f}%"],
        ["Bot Failures", str(summary.get("total_failures", "—"))],
    ]
    ct = Table(cover_meta, colWidths=[5 * cm, 9 * cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#2C3E50")),
        ("BACKGROUND",  (1, 0), (1, -1), colors.HexColor("#34495E")),
        ("TEXTCOLOR",   (0, 0), (-1, -1), C_WHITE),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TOPPADDING",  (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#1A252F")),
    ]))
    story.append(ct)

    # ── Page 2: Campaign Summary ───────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Campaign Summary", sty["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=10))
    story.append(_kpi_table([
        ("Total Calls",    str(summary.get("total_calls", 0))),
        ("Audited",        str(summary.get("audited_calls", 0))),
        ("Avg QA Score",   f"{summary.get('avg_qa_score', 0):.1f}%"),
        ("Pass Rate",      f"{summary.get('pass_rate', 0):.1f}%"),
        ("Bot Failures",   str(summary.get("total_failures", 0))),
        ("Failure Rate",   f"{summary.get('failure_rate', 0) * 100:.0f}%"),
    ], sty))
    story.append(Spacer(1, 0.6 * cm))

    # QA Distribution chart
    dist = qa.get("score_distribution", {})
    if dist:
        fig = _chart_score_dist(dist)
        story.append(_img(fig, h=6.5))
    story.append(Spacer(1, 0.4 * cm))

    # QA Field scores chart
    fields = qa.get("field_breakdown", [])
    if fields:
        story.append(Paragraph("QA Field Breakdown", sty["h2"]))
        fig2 = _chart_field_scores(fields)
        if fig2:
            story.append(_img(fig2, h=max(4, len(fields) * 0.7)))
        # Field table
        fh = [Paragraph("<b>Field</b>", sty["small"]),
              Paragraph("<b>Avg Score</b>", sty["small"]),
              Paragraph("<b>Max Score</b>", sty["small"]),
              Paragraph("<b>%</b>", sty["small"])]
        frows = [fh]
        for f in sorted(fields, key=lambda x: x["percentage"]):
            color = C_GREEN if f["percentage"] >= 70 else (C_AMBER if f["percentage"] >= 50 else C_RED)
            frows.append([
                Paragraph(f["field_name"], sty["small"]),
                Paragraph(f"{f['avg_score']:.1f}", sty["small"]),
                Paragraph(f"{f['max_score']:.0f}", sty["small"]),
                Paragraph(f"{f['percentage']:.1f}%",
                          ParagraphStyle("fp", fontSize=8, textColor=color, fontName="Helvetica-Bold")),
            ])
        ft = Table(frows, colWidths=[8 * cm, 3 * cm, 3 * cm, 2.5 * cm])
        ft.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
            ("GRID",       (0, 0), (-1, -1), 0.4, C_LIGHT_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_GREY]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(ft)

    # ── Page 3: Failure Analysis ───────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Bot Failure Intelligence Analysis", sty["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=10))

    fail_dist = failures.get("failure_distribution", {})
    if fail_dist:
        fig3 = _chart_failure_dist(fail_dist)
        if fig3:
            story.append(_img(fig3, h=max(4, len(fail_dist) * 0.8)))
        # Failure table
        fh2 = [Paragraph("<b>Failure Type</b>", sty["small"]),
               Paragraph("<b>Count</b>", sty["small"]),
               Paragraph("<b>Call Rate</b>", sty["small"]),
               Paragraph("<b>Severity</b>", sty["small"])]
        rates = failures.get("failure_rates", {})
        frows2 = [fh2]
        for ft_name, cnt in sorted(fail_dist.items(), key=lambda x: -x[1]):
            rate = rates.get(ft_name, 0)
            sev  = "Critical" if rate >= 0.3 else "High" if rate >= 0.15 else "Medium"
            sc   = C_RED if sev == "Critical" else C_AMBER if sev == "High" else C_BLUE
            frows2.append([
                Paragraph(ft_name, sty["small"]),
                Paragraph(str(cnt), sty["small"]),
                Paragraph(f"{rate * 100:.1f}%", sty["small"]),
                Paragraph(sev, ParagraphStyle("sv", fontSize=8, textColor=sc, fontName="Helvetica-Bold")),
            ])
        ft2 = Table(frows2, colWidths=[7 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        ft2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
            ("GRID",       (0, 0), (-1, -1), 0.4, C_LIGHT_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_GREY]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(ft2)
    else:
        story.append(Paragraph("No bot failures detected.", sty["body"]))

    # ── Page 4: Entity + Lead Analysis ────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Entity Accuracy & Lead Classification", sty["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=10))

    story.append(_kpi_table([
        ("Entity Capture Rate", f"{entity.get('capture_rate', 0) * 100:.0f}%"),
        ("Avg Entity Score",    f"{entity.get('avg_entity_score', 0):.1f}%"),
        ("Hot Lead Rate",       f"{leads.get('hot_lead_rate', 0) * 100:.0f}%"),
        ("Total Leads",         str(leads.get("total", 0))),
    ], sty))
    story.append(Spacer(1, 0.5 * cm))

    lead_dist = leads.get("distribution", {})
    if lead_dist:
        fig4 = _chart_lead_pie(lead_dist)
        if fig4:
            story.append(_img(fig4, w=10, h=7))

    # ── Page 5: Conversation Analysis ─────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Conversation Flow Analysis", sty["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=10))

    story.append(_kpi_table([
        ("Avg Duration",  f"{conv.get('avg_duration', 0):.0f}s"),
        ("Short Calls",   str(conv.get("short_calls", 0))),
        ("Conv Drops",    str(conv.get("conversation_drops", 0))),
        ("Drop Rate",     f"{conv.get('drop_rate', 0) * 100:.1f}%"),
    ], sty))
    story.append(Spacer(1, 0.5 * cm))

    dur_dist = conv.get("duration_distribution", {})
    if dur_dist:
        fig5 = _chart_duration_dist(dur_dist)
        if fig5:
            story.append(_img(fig5, h=5))

    # ── Page 6: Action Plan ────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Prioritised Action Plan", sty["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=8))
    story.append(Paragraph(
        "Recommendations are ordered by priority based on detected failure rates, "
        "QA scores, and conversation health metrics.",
        sty["body"],
    ))
    story.append(Spacer(1, 0.4 * cm))
    if plan:
        story.append(_action_table(plan, sty))
        story.append(Spacer(1, 0.5 * cm))
        # Detail bullets per item
        for item in plan:
            pri = item["priority"]
            c   = {"CRITICAL": "#C0392B", "HIGH": "#E74C3C", "MEDIUM": "#F39C12", "LOW": "#27AE60"}.get(pri, "#95A5A6")
            story.append(Paragraph(
                f'<font color="{c}"><b>[{pri}]</b></font> {item["recommendation"]}',
                sty["h2"],
            ))
            for act in item.get("actions", []):
                story.append(Paragraph(f"• {act}", sty["bullet"]))
            story.append(Spacer(1, 0.2 * cm))
    else:
        story.append(Paragraph("No recommendations generated.", sty["body"]))

    doc.build(story)
    pdf_bytes = buf.getvalue()

    # Save to disk
    safe_name = "".join(c for c in summary.get("campaign_name", "report") if c.isalnum() or c in " _-")
    fname = REPORTS_DIR / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    fname.write_bytes(pdf_bytes)

    return pdf_bytes
