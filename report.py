from datetime import datetime, timezone
from html import escape
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import analysis
from config import APP_NAME, find_logo
from reportlab.lib.utils import ImageReader

NAVY = colors.HexColor("#0f2a4a")
AMBER = colors.HexColor("#f59e0b")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6b7280")
ACCENT = colors.HexColor("#1d4ed8")
BAND = colors.HexColor("#f3f4f6")

_b = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_b["Title"], fontSize=22, leading=26, alignment=0, textColor=INK)
SUB = ParagraphStyle("Sub", parent=_b["Normal"], fontSize=11, textColor=MUTED, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=_b["Heading2"], fontSize=13, textColor=ACCENT, spaceBefore=14, spaceAfter=6)
BODY = ParagraphStyle("Body", parent=_b["BodyText"], fontSize=9.5, leading=13)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=12, bulletIndent=0)
NOTE = ParagraphStyle("Note", parent=BODY, fontSize=8, textColor=MUTED)
CELL = ParagraphStyle("Cell", parent=_b["BodyText"], fontSize=8, leading=10)
KPI_V = ParagraphStyle("KpiV", parent=_b["Normal"], fontSize=18, leading=22, textColor=INK, fontName="Helvetica-Bold")
KPI_L = ParagraphStyle("KpiL", parent=_b["Normal"], fontSize=8, textColor=MUTED)


def safe(text):
    """Built-in PDF fonts are Latin-1 only; other characters become '?'."""
    text = "" if text is None else str(text)
    return escape(text.encode("latin-1", "replace").decode("latin-1"))


def p(text, style=BODY):
    return Paragraph(safe(text), style)


def money(v):
    return "N/A" if pd.isna(v) else f"AED {v:,.2f}"


def rating(v):
    return "N/A" if pd.isna(v) else f"{v:.1f}"


def count(v):
    return "N/A" if pd.isna(v) else f"{int(v):,}"


def delta(v):
    if pd.isna(v):
        return "-"
    v = int(v)
    return "0" if v == 0 else f"{v:+d}"


def link(url):
    if not url:
        return "N/A"
    return Paragraph(f'<a href="{escape(str(url), quote=True)}" color="#1d4ed8"><u>Open</u></a>', CELL)


def _style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
    ])


def product_table(frame, has_prev):
    head = ["Rank", "Product", "Price", "Rating", "Ratings"]
    if has_prev:
        head += ["Rank change", "Status"]
        widths = [38, 358, 78, 48, 56, 56, 108, 50]
    else:
        widths = [40, 502, 80, 55, 65, 50]
    head.append("Amazon")
    rows = [head]
    for r in frame.itertuples():
        row = [count(r.rank), p(str(r.title)[:140], CELL), money(r.price_aed),
               rating(r.rating), count(r.reviews)]
        if has_prev:
            row += [delta(r.rank_change), r.status]
        row.append(link(r.product_url))
        rows.append(row)
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(_style())
    return t


def movers_table(frame):
    rows = [["Product", "Previous rank", "Current rank", "Change", "Amazon"]]
    for r in frame.itertuples():
        rows.append([p(str(r.title)[:110], CELL), count(r.prev_rank), count(r.rank),
                     delta(r.rank_change), link(r.product_url)])
    t = Table(rows, colWidths=[300, 80, 80, 60, 60], repeatRows=1)
    t.setStyle(_style())
    return t


def _chrome(generated):
    logo = find_logo()
    box_h = 24
    logo_w = None
    if logo is not None and logo.suffix.lower() in (".png", ".jpg", ".jpeg"):
        try:
            iw, ih = ImageReader(str(logo)).getSize()
            logo_w = min(iw / ih * box_h, 150)
        except Exception:
            logo_w = None

    def draw(canvas, doc):
        w, h = landscape(A4)
        canvas.saveState()
        # header band
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 42, w, 42, fill=1, stroke=0)
        canvas.setFillColor(AMBER)
        canvas.rect(0, h - 44, w, 2, fill=1, stroke=0)
        x = 25
        if logo_w:
            canvas.setFillColor(colors.white)
            canvas.roundRect(x, h - 37, logo_w + 12, box_h + 8, 6, fill=1, stroke=0)
            canvas.drawImage(str(logo), x + 6, h - 33, width=logo_w, height=box_h, mask="auto")
            x += logo_w + 24
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(x, h - 25, APP_NAME)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#cbd5e1"))
        canvas.drawRightString(w - 25, h - 25, "Amazon.ae Best Sellers Research")
        # footer
        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(25, 28, w - 25, 28)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(25, 16, f"{APP_NAME} - internal research, not a purchasing recommendation")
        canvas.drawCentredString(w / 2, 16, f"Generated {generated}")
        canvas.drawRightString(w - 25, 16, f"Page {doc.page}")
        canvas.restoreState()
    return draw

def _kpi_row(cells):
    flow = [[Paragraph(safe(v), KPI_V), Paragraph(safe(l), KPI_L)] for v, l in cells]
    t = Table([flow], colWidths=[198] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BAND),
        ("GRID", (0, 0), (-1, -1), 6, colors.white),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_pdf(category, data, full_list=True):
    run, prev_run, df = data["run"], data["prev_run"], data["df"]
    has_prev = prev_run is not None
    s = analysis.summarize(df, has_prev)
    collected = analysis.fmt_ts(run["started_at"])
    generated = analysis.fmt_ts(datetime.now(timezone.utc).isoformat())

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), leftMargin=25, rightMargin=25,
        topMargin=60, bottomMargin=38,
        title=f"{APP_NAME} - {category}", author=APP_NAME,
    )

    story = [p("Amazon.ae Best Sellers Report", H1), p(category, SUB)]

    meta = Table([
        [p("Collected", NOTE), p(collected, CELL), p("Amazon page", NOTE), p(run.get("page_heading") or "n/a", CELL)],
        [p("Products collected", NOTE), p(str(s["products"]), CELL), p("Compared with", NOTE),
         p(analysis.fmt_ts(prev_run["started_at"]) if has_prev else "None (baseline snapshot)", CELL)],
    ], colWidths=[100, 296, 100, 296])
    meta.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                              ("PADDING", (0, 0), (-1, -1), 4)]))
    story += [meta, Spacer(1, 12)]

    story.append(_kpi_row([
        (str(s["products"]), "Products collected"),
        (money(s["median_price"]), f"Median price ({s['priced']} of {s['products']} priced)"),
        ("N/A" if s["avg_rating"] is None else f"{s['avg_rating']:.2f} / 5", f"Average rating ({s['rated']} rated)"),
        ((f"{s['improved']} up / {s['declined']} down" if has_prev else "Baseline"),
         "Rank movement vs previous snapshot" if has_prev else "No previous snapshot yet"),
    ]))

    story.append(p("Executive summary", H2))
    lines = [
        f"{s['products']} products were collected for {category} on {collected}, covering ranks "
        f"{s['min_rank']} to {s['max_rank']}."
        + (f" Ranks {', '.join(s['gaps'])} were not present in the collected pages." if s["gaps"] else ""),
        (f"Listed prices range from {money(s['min_price'])} to {money(s['max_price'])}, with a median of "
         f"{money(s['median_price'])}. {s['products'] - s['priced']} products showed no price."
         if s["priced"] else "No prices were available in this snapshot."),
        (f"The average rating is {s['avg_rating']:.2f} out of 5 across {s['rated']} rated products."
         if s["rated"] else "No ratings were available in this snapshot."),
    ]
    if has_prev:
        lines.append(
            f"Versus {analysis.fmt_ts(prev_run['started_at'])}: {s['improved']} improved, {s['declined']} declined, "
            f"{s['unchanged']} unchanged, {s['new']} new to the observed range."
        )
    else:
        lines.append("This is a baseline snapshot. Ranking movement and new-product detection "
                     "require at least one earlier collection.")
    for line in lines:
        story.append(Paragraph(safe(line), BULLET, bulletText="•"))

    story.append(p("Top 10 products", H2))
    top = df.dropna(subset=["rank"]).nsmallest(10, "rank")
    story.append(product_table(top, has_prev))

    if has_prev:
        story.append(p("Biggest ranking movements", H2))
        story.append(p("Rank change = previous rank minus current rank; positive means the product moved up. "
                       "Only products ranked in both snapshots are compared.", NOTE))
        story.append(Spacer(1, 4))
        gain = df[df["status"] == "Improved"].nlargest(5, "rank_change")
        loss = df[df["status"] == "Declined"].nsmallest(5, "rank_change")
        story.append(p("Gainers", BODY))
        story.append(movers_table(gain) if len(gain) else p("None.", NOTE))
        story.append(Spacer(1, 6))
        story.append(p("Decliners", BODY))
        story.append(movers_table(loss) if len(loss) else p("None.", NOTE))

        new = df[df["status"] == "New to observed range"].sort_values("rank").head(10)
        story.append(p("New to the observed range", H2))
        story.append(p("These products were not in the previous snapshot's collected ranks. That does not mean "
                       "they are new launches; they may have been in a rank range that is not collected.", NOTE))
        story.append(Spacer(1, 4))
        story.append(product_table(new, False) if len(new) else p("None.", NOTE))

    if full_list:
        story.append(p("Full ranked list", H2))
        story.append(product_table(df.sort_values("rank"), has_prev))

    story.append(p("Limitations", H2))
    for text in [
        "Best Sellers rank is a relative marketplace signal. It is not sales volume, revenue or profit.",
        "'Ratings' is the cumulative number of customer ratings, not units sold.",
        "Only ranks present on the collected pages are observed"
        + (f" (missing: {', '.join(s['gaps'])}). " if s["gaps"] else ". ")
        + "Ranks beyond the highest collected rank are not observed. A product that is absent may have moved "
          "outside the observed ranges, not disappeared.",
        "Prices and ratings are as displayed at collection time. Some listings show none.",
        "No supplier cost, shipping, customs, MOQ, VAT or margin data is included. A high-ranking product "
        "is a candidate to investigate, not a sourcing recommendation.",
    ]:
        story.append(Paragraph(safe(text), BULLET, bulletText="•"))

    chrome = _chrome(generated)
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return buf.getvalue()