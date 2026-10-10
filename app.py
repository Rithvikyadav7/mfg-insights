import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from google.genai import types

from utils import (clean_production, clean_sales, ensure_products,
                   generate_sample_data, lost_revenue_by_product)

st.set_page_config(page_title="OpsView", page_icon="🏭", layout="wide")

# ---------- Design tokens ----------
INK, MUTED, LINE, GRID = "#1B2430", "#6B7787", "#EEE8E2", "#EFEAE5"
TEAL, CORAL, NAVY = "#0F9D8A", "#E5533D", "#2B3A55"
COLORWAY = [TEAL, NAVY, "#9FB3C8"]
PAGES = ["Overview", "Operations", "Sales", "Connected insights", "AI analyst"]
ICONS = {"Overview": "📊", "Operations": "⚙️", "Sales": "💰", "Connected insights": "🔗", "AI analyst": "🤖"}
DESCRIPTIONS = {
    "Overview": "Plant health at a glance, with what needs attention first.",
    "Operations": "Machine downtime, causes and quality, worst first.",
    "Sales": "Revenue by region and product, with the trend.",
    "Connected insights": "Where problems on the factory floor show up in the business.",
    "AI analyst": "Ask in plain language and get numbers and next actions.",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
:root{--ink:#1B2430;--muted:#6B7787;--line:#EEE8E2;--teal:#0F9D8A;--mint:#E3F6F2;--coral:#E5533D;--coralbg:#FDEBE7}
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp button, .stApp textarea, .stApp h1, .stApp h2, .stApp h3, .stApp h4{font-family:'Poppins','Segoe UI',system-ui,sans-serif}
.stApp{background:radial-gradient(900px 520px at 100% -5%, rgba(255,205,175,.50), transparent 62%), #F8F5F2}
header[data-testid="stHeader"]{background:transparent}
footer{visibility:hidden}
.block-container{padding-top:1.2rem;padding-bottom:3rem;max-width:1400px}
section[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid var(--line)}
section[data-testid="stSidebar"] .block-container{padding-top:1.4rem}

.brand{display:flex;align-items:center;gap:12px;margin-bottom:22px}
.btile{width:42px;height:42px;border-radius:12px;background:var(--teal);color:#fff;font-weight:700;font-size:1.3rem;display:flex;align-items:center;justify-content:center}
.bname{font-weight:700;font-size:1.2rem;color:var(--ink);line-height:1.1}
.bsub{font-size:.62rem;letter-spacing:.14em;color:var(--muted);font-weight:500;margin-top:3px}
.sidelabel{font-size:.68rem;letter-spacing:.14em;color:#8B96A5;font-weight:600;margin:20px 0 8px}

.st-key-nav button{width:100%;justify-content:flex-start;border:0;box-shadow:none;background:transparent;padding:.7rem .9rem;border-radius:12px;color:var(--ink)}
.st-key-nav button:hover{background:#F3EEE9;color:var(--ink);border:0}
.st-key-nav button > div{justify-content:flex-start;width:100%}
.st-key-nav button p{text-align:left;font-weight:500;font-size:.95rem}
.st-key-nav button[kind="primary"], .st-key-nav button[data-testid="stBaseButton-primary"]{background:var(--teal);color:#fff;border:0}
.st-key-nav button[kind="primary"] p, .st-key-nav button[data-testid="stBaseButton-primary"] p{color:#fff;font-weight:600}

.topbar{display:flex;justify-content:space-between;align-items:center;padding:6px 2px 16px;border-bottom:1px solid var(--line);margin-bottom:24px}
.tsmall{font-size:.82rem;color:var(--muted)}
.tbig{font-weight:600;font-size:1.1rem;color:var(--ink)}
.phead{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:18px}
.eyebrow{font-size:.72rem;letter-spacing:.16em;color:var(--coral);font-weight:600}
.ptitle{font-weight:700;font-size:2.1rem;color:var(--ink);line-height:1.2;letter-spacing:-0.01em}
.pdesc{color:var(--muted);font-size:.98rem;max-width:380px;text-align:right}

.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 11px;border-radius:999px;font-size:.76rem;font-weight:600;background:#F0EDEA;color:#59636F}
.pill.ok{background:var(--mint);color:#0B7F6F}
.pill.bad{background:var(--coralbg);color:#C93E2A}
.pdot{width:7px;height:7px;border-radius:50%;background:currentColor;display:inline-block}

.card{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:0 1px 2px rgba(27,36,48,.04),0 10px 28px rgba(27,36,48,.05);padding:18px 22px}
.summary{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:0 1px 2px rgba(27,36,48,.04),0 10px 28px rgba(27,36,48,.05);margin-bottom:20px}
.sleft{display:flex;align-items:center;gap:16px;padding:18px 22px}
.sname{font-weight:600;font-size:1.25rem;color:var(--ink);display:flex;align-items:center;gap:10px}
.ssub{font-size:.88rem;color:var(--muted)}
.sstats{display:flex}
.sstat{padding:18px 30px;border-left:1px solid var(--line)}
.slab{font-size:.68rem;letter-spacing:.12em;color:#8B96A5;font-weight:600}
.sval{font-size:1.02rem;font-weight:500;color:var(--ink);margin-top:4px}

.kgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-bottom:22px}
.khead{display:flex;justify-content:space-between;align-items:center}
.klab{font-size:.86rem;color:var(--muted);font-weight:500}
.chip{width:30px;height:30px;border-radius:9px;background:var(--mint);display:flex;align-items:center;justify-content:center;font-size:.95rem}
.kval{font-weight:600;font-size:1.75rem;color:var(--ink);margin:10px 0 10px;font-variant-numeric:tabular-nums;letter-spacing:-0.01em}
.fgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:22px}
.card-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.card-t{font-weight:600;font-size:.98rem;color:var(--ink)}
.fh{font-weight:600;font-size:1.25rem;color:var(--ink);line-height:1.3}
.fs{font-size:.88rem;color:var(--muted);margin-top:4px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:6px 0 18px}
.snum{width:38px;height:38px;border-radius:11px;background:var(--mint);color:#0B7F6F;font-weight:700;display:flex;align-items:center;justify-content:center;margin-bottom:12px}
.step-t{font-weight:600;font-size:1.1rem;color:var(--ink);margin-bottom:4px}
.step-p{color:var(--muted);font-size:.93rem;line-height:1.5}
.note{color:var(--muted);font-size:.9rem;margin-top:8px}

[data-testid="stPlotlyChart"]{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:0 1px 2px rgba(27,36,48,.04),0 10px 28px rgba(27,36,48,.05);padding:8px 10px}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:14px;overflow:hidden}
[data-testid="stFileUploaderDropzone"]{background:#FBF9F7;border:1px dashed #DCD3CA;border-radius:14px}
.stButton > button{border-radius:12px;border:1px solid #E4DCD3;background:#fff;color:var(--ink);font-weight:500}
.stButton > button:hover{border-color:var(--teal);color:var(--teal)}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"]{background:var(--teal);color:#fff;border:1px solid var(--teal)}
@media (max-width: 1000px){.kgrid{grid-template-columns:repeat(2,1fr)}.fgrid,.steps{grid-template-columns:1fr}.phead{flex-direction:column;align-items:flex-start}.pdesc{text-align:left}.sstats{display:none}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- Helpers ----------
def style(fig, height=360, money=False):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins, Segoe UI, sans-serif", color=INK, size=13),
        title=dict(x=0.0, xanchor="left", font=dict(size=17, color=INK)),
        margin=dict(l=12, r=12, t=58, b=12), height=height, colorway=COLORWAY,
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", title_text=""),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=INK, bordercolor=LINE),
    )
    fig.update_xaxes(title_text="", showgrid=False, linecolor=LINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(title_text="", gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED))
    if money:
        fig.update_yaxes(tickprefix="₹", tickformat="~s")
    fig.update_traces(line_width=3, marker_size=7, selector=dict(type="scatter"))
    fig.update_traces(marker_color=TEAL, selector=dict(type="bar"))
    return fig


def show(fig, height=360, money=False, flag=None):
    """flag=(labels, target) paints the matching bar coral."""
    style(fig, height, money)
    if flag is not None:
        labels, target = flag
        fig.update_traces(marker_color=[CORAL if x == target else TEAL for x in labels],
                          selector=dict(type="bar"))
    st.plotly_chart(fig, width="stretch")


def pill(text, kind="info", dot=True):
    d = '<span class="pdot"></span>' if dot else ""
    return f'<span class="pill {kind}">{d}{text}</span>'


def kpi_card(icon, label, value, sub, kind="info"):
    return (f'<div class="card"><div class="khead"><span class="klab">{label}</span><span class="chip">{icon}</span></div>'
            f'<div class="kval">{value}</div>{pill(sub, kind)}</div>')


def flag_card(title, headline, sub):
    return (f'<div class="card"><div class="card-h"><span class="card-t">{title}</span>{pill("Flagged", "bad")}</div>'
            f'<div class="fh">{headline}</div><div class="fs">{sub}</div></div>')


def step_card(n, title, text):
    return (f'<div class="card"><div class="snum">{n}</div><div class="step-t">{title}</div>'
            f'<div class="step-p">{text}</div></div>')


def topbar(kind, text):
    st.markdown(
        '<div class="topbar"><div><div class="tsmall">Analytics workspace</div>'
        '<div class="tbig">Factory operations and sales</div></div>'
        f'<div>{pill(text, kind)}</div></div>', unsafe_allow_html=True)


def page_header(title):
    st.markdown(
        f'<div class="phead"><div><div class="eyebrow">OPERATIONS DASHBOARD</div><div class="ptitle">{title}</div></div>'
        f'<div class="pdesc">{DESCRIPTIONS[title]}</div></div>', unsafe_allow_html=True)


def summary_card(badge_kind, badge_text, period, n_machines, n_products):
    st.markdown(
        '<div class="summary"><div class="sleft"><div class="btile">O</div><div>'
        f'<div class="sname">OpsView {pill(badge_text, badge_kind)}</div>'
        '<div class="ssub">Manufacturing and sales analytics</div></div></div>'
        '<div class="sstats">'
        f'<div class="sstat"><div class="slab">PERIOD</div><div class="sval">{period}</div></div>'
        f'<div class="sstat"><div class="slab">MACHINES</div><div class="sval">{n_machines}</div></div>'
        f'<div class="sstat"><div class="slab">PRODUCTS</div><div class="sval">{n_products}</div></div>'
        '</div></div>', unsafe_allow_html=True)


def read_any(f):
    if f.name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(f)
    return pd.read_csv(f)


def go(p):
    st.session_state["page"] = p


# ---------- Sidebar: brand, navigation, data ----------
page = st.session_state.get("page", "Overview")
with st.sidebar:
    st.markdown('<div class="brand"><div class="btile">O</div><div><div class="bname">OpsView</div>'
                '<div class="bsub">MANUFACTURING ANALYTICS</div></div></div>'
                '<div class="sidelabel">NAVIGATION</div>', unsafe_allow_html=True)
    with st.container(key="nav"):
        for p_name in PAGES:
            st.button(f"{ICONS[p_name]}  {p_name}", key=f"nav_{p_name}",
                      type="primary" if page == p_name else "secondary", on_click=go, args=(p_name,))
    st.markdown('<div class="sidelabel">DATA</div>', unsafe_allow_html=True)
    prod_file = st.file_uploader("Production file (CSV/Excel)", type=["csv", "xlsx", "xls"])
    sales_file = st.file_uploader("Sales file (CSV/Excel)", type=["csv", "xlsx", "xls"])
    cat_file = st.file_uploader("Products file (optional)", type=["csv", "xlsx", "xls"])
    if st.button("Use sample data"):
        st.session_state["use_sample"] = True

using_upload = bool(prod_file and sales_file)
using_sample = (not using_upload) and st.session_state.get("use_sample", False)
if using_upload:
    src_kind, src_text = "ok", "Your uploaded files"
elif using_sample:
    src_kind, src_text = "info", "Simulated sample data"
else:
    src_kind, src_text = "info", "No data loaded yet"
topbar(src_kind, src_text)

try:
    if using_upload:
        production = clean_production(read_any(prod_file))
        sales = clean_sales(read_any(sales_file))
        products = ensure_products(read_any(cat_file) if cat_file else None, production, sales)
    elif using_sample:
        p, s, pr = generate_sample_data()
        production, sales = clean_production(p), clean_sales(s)
        products = ensure_products(pr, production, sales)
    else:
        st.markdown(
            '<div class="phead"><div><div class="eyebrow">GET STARTED</div>'
            '<div class="ptitle">From scattered files to one view</div></div></div>'
            '<div class="steps">'
            + step_card("1", "Upload your files", "Production and sales, as CSV or Excel. Column names don't need to match.")
            + step_card("2", "See one view", "We clean and merge them, then work out defect rate, availability, on-time delivery and revenue lost to downtime.")
            + step_card("3", "Ask the analyst", "Get the top issues and what to fix first, in plain language.")
            + '</div><div class="note">No files handy? Choose Use sample data in the sidebar.</div>',
            unsafe_allow_html=True,
        )
        st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()

name_map = dict(zip(products["product_id"], products["product_name"]))
production["product"] = production["product_id"].map(name_map).fillna(production["product_id"])
sales["product"] = sales["product_id"].map(name_map).fillna(sales["product_id"])

# ---------- Sidebar: filters ----------
with st.sidebar:
    st.markdown('<div class="sidelabel">FILTERS</div>', unsafe_allow_html=True)
    min_d = min(production["date"].min(), sales["order_date"].min()).date()
    max_d = max(production["date"].max(), sales["order_date"].max()).date()
    date_range = st.date_input("Date range", (min_d, max_d))
    all_products = sorted(set(production["product"]) | set(sales["product"]))
    chosen = st.multiselect("Products", all_products, default=all_products)

if len(date_range) != 2:
    st.stop()
start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

prod_f = production[production["date"].between(start, end) & production["product"].isin(chosen)].copy()
sales_f = sales[sales["order_date"].between(start, end) & sales["product"].isin(chosen)].copy()
if prod_f.empty or sales_f.empty:
    st.warning("No data for these filters.")
    st.stop()

prod_f["month"] = prod_f["date"].dt.to_period("M").dt.to_timestamp()
sales_f["month"] = sales_f["order_date"].dt.to_period("M").dt.to_timestamp()
sales_f["late"] = sales_f["delivery_date"] > sales_f["promised_date"]

# ---------- Metrics ----------
units = prod_f["units_produced"].sum()
defect_rate = prod_f["defective_units"].sum() / max(units, 1)
availability = 1 - prod_f["downtime_hours"].sum() / max(prod_f["planned_hours"].sum(), 1)
revenue = sales_f["revenue"].sum()
on_time = 1 - sales_f["late"].mean()
lost = lost_revenue_by_product(prod_f, sales_f)

by_machine = prod_f.groupby("machine_id", as_index=False).agg(
    downtime_hours=("downtime_hours", "sum"),
    defective=("defective_units", "sum"),
    units=("units_produced", "sum"),
)
by_machine["defect_rate_%"] = (by_machine["defective"] / by_machine["units"].replace(0, 1) * 100).round(2)
worst_row = by_machine.sort_values("downtime_hours", ascending=False).iloc[0]
quality_row = by_machine.sort_values("defect_rate_%", ascending=False).iloc[0]

late = sales_f.groupby("product", as_index=False)["late"].mean()
late["late_%"] = late["late"] * 100
late_row = late.sort_values("late_%", ascending=False).iloc[0]

# ---------- Page frame ----------
page_header(page)
summary_card("ok" if using_upload else "info", "Your data" if using_upload else "Sample data",
             f"{start:%d %b %Y} to {end:%d %b %Y}", len(by_machine), len(chosen))

# ---------- Overview ----------
if page == "Overview":
    st.markdown(
        '<div class="kgrid">'
        + kpi_card("🏭", "Units produced", f"{units:,.0f}", f"{len(by_machine)} machines")
        + kpi_card("⚠️", "Defect rate", f"{defect_rate:.1%}",
                   "Within 2.5% target" if defect_rate <= 0.025 else "Above 2.5% target",
                   "ok" if defect_rate <= 0.025 else "bad")
        + kpi_card("⚙️", "Machine availability", f"{availability:.1%}",
                   "Above 90% target" if availability >= 0.9 else "Below 90% target",
                   "ok" if availability >= 0.9 else "bad")
        + kpi_card("💰", "Revenue", f"₹{revenue:,.0f}", "Selected period")
        + kpi_card("🚚", "On-time delivery", f"{on_time:.1%}",
                   "Above 90% target" if on_time >= 0.9 else "Below 90% target",
                   "ok" if on_time >= 0.9 else "bad")
        + '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="fgrid">'
        + flag_card("Downtime hotspot", f"{worst_row['machine_id']} lost {worst_row['downtime_hours']:,.0f} hours",
                    "Most downtime of any machine")
        + flag_card("Quality hotspot", f"{quality_row['machine_id']} at {quality_row['defect_rate_%']:.1f}% defects",
                    f"Plant average is {defect_rate:.1%}")
        + flag_card("Delivery risk", f"{late_row['product']}: {late_row['late_%']:.0f}% late",
                    "Highest late-delivery rate")
        + '</div>',
        unsafe_allow_html=True,
    )
    m_rev = sales_f.groupby("month", as_index=False)["revenue"].sum()
    peak_month = m_rev.loc[m_rev["revenue"].idxmax(), "month"]
    m_units = prod_f.groupby("month", as_index=False)["units_produced"].sum()
    left, right = st.columns(2)
    with left:
        show(px.line(m_rev, x="month", y="revenue", markers=True,
                     title=f"Monthly revenue peaked in {peak_month:%b %Y}"), money=True)
    with right:
        show(px.line(m_units, x="month", y="units_produced", markers=True, title="Monthly units produced"))

# ---------- Operations ----------
elif page == "Operations":
    left, right = st.columns(2)
    with left:
        show(px.bar(by_machine, x="machine_id", y="downtime_hours",
                    title=f"{worst_row['machine_id']} has the most downtime ({worst_row['downtime_hours']:,.0f} hours)"),
             flag=(by_machine["machine_id"], worst_row["machine_id"]))
    reasons = (
        prod_f[prod_f["downtime_reason"] != "None"]
        .groupby("downtime_reason", as_index=False)["downtime_hours"].sum()
        .sort_values("downtime_hours", ascending=False)
    )
    with right:
        top_reason = reasons.iloc[0]["downtime_reason"] if len(reasons) else None
        show(px.bar(reasons, x="downtime_reason", y="downtime_hours",
                    title=f"Downtime by reason: {top_reason} leads" if top_reason else "Downtime by reason"),
             flag=(reasons["downtime_reason"], top_reason))

    m_def = prod_f.groupby("month", as_index=False).agg(d=("defective_units", "sum"), u=("units_produced", "sum"))
    m_def["defect_rate_%"] = m_def["d"] / m_def["u"].replace(0, 1) * 100
    show(px.line(m_def, x="month", y="defect_rate_%", markers=True, title="Defect rate by month (%)"))

    st.markdown("#### Machines, worst first")
    table = by_machine.sort_values("downtime_hours", ascending=False).rename(columns={
        "machine_id": "Machine", "downtime_hours": "Downtime (h)", "defective": "Defective units",
        "units": "Units", "defect_rate_%": "Defect rate (%)",
    })
    st.dataframe(table, width="stretch", hide_index=True)

# ---------- Sales ----------
elif page == "Sales":
    reg = sales_f.groupby("region", as_index=False)["revenue"].sum()
    top = sales_f.groupby("product", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
    left, right = st.columns(2)
    with left:
        show(px.bar(reg, x="region", y="revenue", title="Revenue by region"), money=True)
    with right:
        show(px.bar(top, x="product", y="revenue", title=f"{top.iloc[0]['product']} brings in the most revenue"), money=True)

    m_rev2 = sales_f.groupby("month", as_index=False)["revenue"].sum()
    fig = px.scatter(m_rev2, x="month", y="revenue", trendline="ols", title="Revenue by month with trendline")
    fig.update_traces(marker_color=TEAL, selector=dict(mode="markers"))
    fig.update_traces(line_color=NAVY, line_dash="dash", selector=dict(mode="lines"))
    show(fig, money=True)

# ---------- Connected insights ----------
elif page == "Connected insights":
    pm = prod_f.groupby("month", as_index=False).agg(units_produced=("units_produced", "sum"))
    sm = sales_f.groupby("month", as_index=False).agg(units_ordered=("quantity", "sum"))
    both = pm.merge(sm, on="month", how="outer").melt("month", var_name="measure", value_name="units")
    show(px.line(both, x="month", y="units", color="measure", markers=True, title="Production against customer orders"))

    total_lost = lost["lost_revenue"].sum()
    top_loss = lost.sort_values("lost_revenue", ascending=False).iloc[0]["product"]
    left, right = st.columns(2)
    with left:
        show(px.bar(lost, x="product", y="lost_revenue",
                    title=f"₹{total_lost:,.0f} estimated revenue lost to downtime"),
             money=True, flag=(lost["product"], top_loss))
    with right:
        show(px.bar(late, x="product", y="late_%", title=f"{late_row['product']} has the highest late-delivery rate (%)"),
             flag=(late["product"], late_row["product"]))
    st.caption("Lost revenue = downtime hours × units per run-hour × average revenue per unit. It is an estimate.")

# ---------- AI analyst ----------
else:
    MODEL_NAME = "gemini-3.8-flash"
    FALLBACK_MODEL = "gemini-3-flash-preview"
    SYSTEM = (
        "You are an expert manufacturing operations and sales analyst. "
        "Answer ONLY from the data summary provided. Quote specific numbers, "
        "name the machines/products/months involved, and keep answers concise "
        "(under 200 words). End with 1-2 concrete recommended actions. "
        "If the data does not contain the answer, say so clearly."
    )

    def build_summary():
        m_prod = prod_f.groupby("month").agg(
            units=("units_produced", "sum"),
            downtime_hours=("downtime_hours", "sum"),
            defective=("defective_units", "sum"),
        ).round(1)
        m_sales = sales_f.groupby("month").agg(
            revenue=("revenue", "sum"),
            orders=("quantity", "count"),
            late_share=("late", "mean"),
        ).round(2)
        machines = prod_f.groupby("machine_id").agg(
            downtime_hours=("downtime_hours", "sum"),
            units=("units_produced", "sum"),
            defective=("defective_units", "sum"),
        )
        machines["defect_rate_pct"] = (machines["defective"] / machines["units"] * 100).round(2)
        reasons_s = (
            prod_f[prod_f["downtime_reason"] != "None"]
            .groupby("downtime_reason")["downtime_hours"].sum().round(1)
        )
        late_p = sales_f.groupby("product")["late"].mean().mul(100).round(1)
        rev_p = sales_f.groupby("product")["revenue"].sum().round(0)
        return (
            f"OVERALL: units={units:,.0f}; defect_rate={defect_rate:.1%}; "
            f"machine_availability={availability:.1%}; revenue=Rs{revenue:,.0f}; on_time_delivery={on_time:.1%}\n\n"
            f"MONTHLY PRODUCTION:\n{m_prod.to_csv()}\n"
            f"MONTHLY SALES:\n{m_sales.to_csv()}\n"
            f"BY MACHINE:\n{machines.to_csv()}\n"
            f"DOWNTIME HOURS BY REASON:\n{reasons_s.to_csv()}\n"
            f"LATE DELIVERY % BY PRODUCT:\n{late_p.to_csv()}\n"
            f"REVENUE BY PRODUCT:\n{rev_p.to_csv()}\n"
            f"ESTIMATED REVENUE LOST TO DOWNTIME BY PRODUCT:\n{lost.round(0).to_csv(index=False)}\n"
        )

    def ask_ai(question):
        try:
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        except Exception:
            return "⚠️ AI key not found. Add GEMINI_API_KEY in the app's Secrets settings."
        prompt = f"DATA SUMMARY:\n{build_summary()}\n\nQUESTION: {question}"
        last_error = ""
        for model in (MODEL_NAME, FALLBACK_MODEL):
            try:
                r = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM),
                )
                return r.text
            except Exception as e:
                last_error = str(e)
        return f"⚠️ The AI is busy or unavailable right now. Please try again in a minute. ({last_error[:100]})"

    def run(question):
        with st.spinner("Analysing your data..."):
            st.session_state["ai_result"] = {"q": question, "a": ask_ai(question)}

    st.caption("Answers use the data currently shown, so your filters apply.")
    examples = [
        "Which machine is costing us the most?",
        "Why did output drop in March 2026?",
        "Which products are at risk of late delivery?",
        "What should the plant manager fix first?",
    ]
    cols = st.columns(len(examples))
    for i, (col, ex) in enumerate(zip(cols, examples)):
        if col.button(ex, key=f"ex_{i}"):
            run(ex)

    typed = st.text_input("Or ask your own question", placeholder="For example: which region is growing fastest?")
    if st.button("Ask") and typed.strip():
        run(typed.strip())

    if st.button("Generate top 5 insights and actions", type="primary"):
        run(
            "Give the top 5 insights from this data as a numbered list. For each, state the "
            "evidence (numbers) and one recommended action. Cover operations, sales, and how "
            "factory problems affect customer delivery and revenue."
        )

    res = st.session_state.get("ai_result")
    if res:
        with st.container(border=True):
            st.markdown(f"**{res['q']}**")
            st.markdown(res["a"])
        st.download_button("Download this answer", f"Q: {res['q']}\n\n{res['a']}", file_name="insights.txt")
