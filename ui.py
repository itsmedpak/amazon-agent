import base64
from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

import analysis
from config import APP_NAME, APP_TAGLINE, find_logo
from pathlib import Path

CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 1400px;}

.app-header {display: flex; align-items: center; gap: 16px; padding: 14px 20px;
  border-radius: 14px; margin-bottom: 1.2rem;
  background: linear-gradient(135deg, #0f2a4a 0%, #1d4ed8 100%);}
.brand-logo {background: #fff; border-radius: 10px; padding: 6px 10px;
  display: flex; align-items: center;}
.brand-logo img {height: 34px; width: auto; display: block;}
.app-title {font-size: 1.35rem; font-weight: 700; line-height: 1.2; color: #fff;}
.app-tagline {font-size: .82rem; color: rgba(255,255,255,.78);}

.app-footer {position: fixed; left: 0; right: 0; bottom: 0; z-index: 100; height: 30px;
  display: flex; align-items: center; justify-content: center; gap: 18px;
  font-size: .74rem; color: rgba(255,255,255,.82); background: #0f2a4a;
  border-top: 2px solid #f59e0b;}

.kpi {border: 1px solid rgba(128,128,128,.28); border-top: 3px solid #1d4ed8;
  border-radius: 12px; padding: 14px 16px; background: rgba(128,128,128,.06);}
.kpi-label {font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; opacity: .7;}
.kpi-value {font-size: 1.75rem; font-weight: 700; line-height: 1.3;}
.kpi-note {font-size: .78rem; opacity: .65; min-height: 1.1em;}

table.pt {width: 100%; border-collapse: collapse; font-size: .86rem;}
table.pt th {text-align: left; padding: 8px 10px; background: #0f2a4a; color: #fff;
  font-weight: 600; white-space: nowrap; border: none;}
table.pt td {padding: 8px 10px; border: none;
  border-bottom: 1px solid rgba(128,128,128,.2); vertical-align: middle;}
table.pt tr:hover td {background: rgba(29,78,216,.07);}
table.pt .num {text-align: right; white-space: nowrap;}
table.pt a, .card-link a {color: #2563eb; text-decoration: none; font-weight: 600;}
.up {color: #16a34a; font-weight: 600;}
.down {color: #dc2626; font-weight: 600;}
.noimg {width: 56px; height: 56px; display: flex; align-items: center;
  justify-content: center; font-size: .65rem; opacity: .5;}

.thumb {position: relative; display: inline-block;}
.thumb img.s {object-fit: contain; border-radius: 6px; background: #fff; display: block;}
.thumb img.big {display: none; position: absolute; left: calc(100% + 10px); top: 50%;
  transform: translateY(-50%); width: 280px; max-width: none; height: auto;
  background: #fff; padding: 8px; border: 1px solid rgba(0,0,0,.15); border-radius: 10px;
  box-shadow: 0 12px 32px rgba(0,0,0,.28); z-index: 1000; pointer-events: none;}
.thumb:hover img.big {display: block;}
.thumb.center img.big {left: 50%; top: 50%; transform: translate(-50%, -50%); width: 260px;}
.card-title {font-size: .9rem; margin: 6px 0 2px 0;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".svg": "image/svg+xml"}


@st.cache_data
def _encode(path_str, mtime):
    path = Path(path_str)
    return f"data:{MIME[path.suffix.lower()]};base64," + base64.b64encode(path.read_bytes()).decode()


def logo_uri():
    path = find_logo()
    if path is None:
        return None
    return _encode(str(path), path.stat().st_mtime)


def render_header():
    uri = logo_uri()
    logo = f'<div class="brand-logo"><img src="{uri}" alt="logo"></div>' if uri else ""
    st.markdown(
        '<div class="app-header">' + logo +
        f'<div><div class="app-title">{escape(APP_NAME)}</div>'
        f'<div class="app-tagline">{escape(APP_TAGLINE)}</div></div></div>',
        unsafe_allow_html=True,
    )

def render_footer():
    st.markdown(
        '<div class="app-footer">'
        f"<span>{escape(APP_NAME)}</span><span>Internal use only</span>"
        "<span>Data: public Amazon.ae Best Sellers pages</span>"
        f"<span>© {datetime.now().year}</span></div>",
        unsafe_allow_html=True,
    )


def num(v, fmt):
    return "—" if v is None or pd.isna(v) else fmt.format(v)


def money(v):
    return "—" if v is None or pd.isna(v) else f"AED {v:,.2f}"


def kpi(label, value, note=""):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def header(category, data):
    st.title(category)
    if data is None:
        st.caption("Amazon.ae Best Sellers · no data collected yet")
        return
    run = data["run"]
    st.caption(
        f"Amazon.ae Best Sellers · collected {analysis.fmt_ts(run['started_at'])} · "
        f"{run['product_count']} products · {data['snapshots']} daily snapshot(s) · "
        f"page: {run.get('page_heading') or 'n/a'}"
    )


def require_data(category):
    data = analysis.load_view(category)
    header(category, data)
    if data is None:
        st.info(
            f"No completed collection for **{category}** yet. Run "
            f'`python collect.py --category "{category}"` in a terminal.'
        )
        st.stop()
    return data


def thumb_html(url, size=56, center=False):
    if not url:
        return '<div class="noimg">no image</div>'
    u = escape(url, quote=True)
    cls = "thumb center" if center else "thumb"
    return (
        f'<span class="{cls}">'
        f'<img class="s" style="width:{size}px;height:{size}px" src="{u}" loading="lazy" alt="">'
        f'<img class="big" src="{u}" alt=""></span>'
    )


def link_html(url, text="Open"):
    if not url:
        return "—"
    return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{text}</a>'


def _delta_cell(v):
    if v is None or pd.isna(v):
        return '<td class="num">—</td>'
    v = int(v)
    if v > 0:
        return f'<td class="num up">▲ {v}</td>'
    if v < 0:
        return f'<td class="num down">▼ {abs(v)}</td>'
    return '<td class="num">0</td>'


def product_table_html(df, has_prev):
    heads = ["Image", "Rank", "Product", "Price (AED)", "Rating", "Ratings"]
    if has_prev:
        heads += ["Rank change", "Movement"]
    heads.append("Amazon")

    out = ["<table class='pt'><thead><tr>",
           "".join(f"<th>{h}</th>" for h in heads), "</tr></thead><tbody>"]
    for r in df.itertuples():
        cells = [
            f"<td>{thumb_html(r.image_url)}</td>",
            f"<td class='num'>{num(r.rank, '{:,.0f}')}</td>",
            f"<td>{escape(str(r.title))}</td>",
            f"<td class='num'>{num(r.price_aed, '{:,.2f}')}</td>",
            f"<td class='num'>{num(r.rating, '{:.1f}')}</td>",
            f"<td class='num'>{num(r.reviews, '{:,.0f}')}</td>",
        ]
        if has_prev:
            cells.append(_delta_cell(r.rank_change))
            cells.append(f"<td>{escape(str(r.status))}</td>")
        cells.append(f"<td>{link_html(r.product_url)}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)