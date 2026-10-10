import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from google.genai import types

from utils import (clean_production, clean_sales, ensure_products,
                   generate_sample_data, lost_revenue_by_product)

st.set_page_config(page_title="MfgInsights", page_icon="🏭", layout="wide")

# ---------- Design tokens ----------
INK, STEEL, LINE, GRID = "#16202E", "#51657D", "#D5DCE4", "#E3E8ED"
BLUE, ORANGE = "#2F6690", "#F26B1D"
COLORWAY = [BLUE, INK, "#8FA3B8"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Semi+Condensed:wght@500;600;700&display=swap');
:root{--paper:#F2F4F6;--ink:#16202E;--steel:#51657D;--line:#D5DCE4;--blue:#2F6690;--orange:#F26B1D;--ok:#2E8B57}
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp button, .stApp textarea{font-family:'Barlow','Segoe UI',system-ui,sans-serif}
.stApp h1, .stApp h2, .stApp h3, .stApp h4{font-family:'Barlow Semi Condensed','Barlow',sans-serif;color:var(--ink);letter-spacing:-0.01em}
.stApp{background:var(--paper)}
header[data-testid="stHeader"]{background:transparent}
footer{visibility:hidden}
.block-container{padding-top:1.6rem;padding-bottom:3rem;max-width:1380px}
section[data-testid="stSidebar"]{background:#E9EDF1;border-right:1px solid var(--line)}
.hazard{height:10px;border-radius:2px;background:repeating-linear-gradient(-45deg,#F26B1D 0 12px,#16202E 12px 24px);margin-bottom:18px}
.title{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-size:3.1rem;line-height:1;color:var(--ink);letter-spacing:-0.02em}
.tagline{color:var(--steel);font-size:1.15rem;margin:8px 0 6px}
.source{font-size:.95rem;color:var(--steel);margin-bottom:18px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;background:#9AA9BB}
.dot.ok{background:var(--ok)}
.dot.bad{background:var(--orange)}
.strip{display:grid;grid-template-columns:repeat(5,1fr);background:#fff;border:1px solid var(--line);border-radius:6px;margin:6px 0 22px}
.cell{padding:16px 20px;border-left:1px solid var(--line)}
.cell:first-child{border-left:0}
.lab{font-size:.95rem;color:var(--steel);font-weight:500}
.val{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-size:2.3rem;line-height:1.15;color:var(--ink);font-variant-numeric:tabular-nums}
.sub{font-size:.88rem;color:var(--steel);margin-top:2px}
.flags{display:grid;grid-template-columns:repeat(3,1fr);background:#fff;border:1px solid var(--line);border-radius:6px;margin:6px 0 22px}
.flag{padding:14px 20px;border-left:4px solid var(--orange)}
.flag + .flag{border-left:1px solid var(--line);box-shadow:inset 4px 0 0 var(--orange)}
.flag-t{font-size:.92rem;color:var(--steel);font-weight:500}
.flag-h{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-size:1.5rem;color:var(--ink);line-height:1.2}
.flag-s{font-size:.9rem;color:var(--steel)}
.steps{display:grid;grid-template-columns:repeat(3,1fr);background:#fff;border:1px solid var(--line);border-radius:6px;margin:10px 0 18px}
.step{padding:20px 24px;border-left:1px solid var(--line)}
.step:first-child{border-left:0}
.step-n{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;font-size:2rem;color:var(--blue);line-height:1}
.step-t{font-family:'Barlow Semi Condensed',sans-serif;font-weight:600;font-size:1.3rem;color:var(--ink);margin:6px 0 4px}
.step-p{color:var(--steel);font-size:1rem}
.note{color:var(--steel);font-size:.9rem;margin-top:24px}
.stTabs [data-baseweb="tab-list"]{gap:26px;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{padding:10px 2px;height:auto;font-family:'Barlow Semi Condensed',sans-serif;font-weight:600;font-size:1.15rem;color:var(--steel)}
.stTabs [aria-selected="true"]{color:var(--ink)}
.stTabs [data-baseweb="tab-highlight"]{background:var(--ink);height:3px}
[data-testid="stPlotlyChart"]{background:#fff;border:1px solid var(--line);border-radius:6px;padding:6px 8px}
.stButton > button{border-radius:6px;border:1px solid #AEB9C6;background:#fff;color:var(--ink);font-weight:600}
.stButton > button:hover{border-color:var(--ink);color:var(--ink)}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"]{background:var(--ink);color:#fff;border:1px solid var(--ink)}
@media (max-width: 900px){.strip{grid-template-columns:repeat(2,1fr)}.flags,.steps{grid-template-columns:1fr}.cell{border-top:1px solid var(--line)}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- Helpers ----------
def style(fig, height=360, money=False):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Barlow, Segoe UI, sans-serif", color=INK, size=14),
        title=dict(x=0.0, xanchor="left",
                   font=dict(family="Barlow Semi Condensed, Barlow, sans-serif", size=20, color=INK)),
        margin=dict(l=12, r=12, t=58, b=12), height=height, colorway=COLORWAY,
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", title_text=""),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=INK, bordercolor=LINE),
    )
    fig.update_xaxes(title_text="", showgrid=False, linecolor=LINE, tickfont=dict(color=STEEL))
    fig.update_yaxes(title_text="", gridcolor=GRID, zeroline=False, tickfont=dict(color=STEEL))
    if money:
        fig.update_yaxes(tickprefix="₹", tickformat="~s")
    fig.update_traces(line_width=3, marker_size=7, selector=dict(type="scatter"))
    fig.update_traces(marker_color=BLUE, selector=dict(type="bar"))
    return fig


def show(fig, height=360, money=False, flag=None):
    """flag=(labels, target) paints the matching bar safety-orange."""
    style(fig, height, money)
    if flag is not None:
        labels, target = flag
        fig.update_traces(marker_color=[ORANGE if x == target else BLUE for x in labels],
                          selector=dict(type="bar"))
    st.plotly_chart(fig, width="stretch")


def kpi_cell(label, value, sub, status="info"):
    return (f'<div class="cell"><div class="lab">{label}</div><div class="val">{value}</div>'
            f'<div class="sub"><span class="dot {status}"></span>{sub}</div></div>')


def flag_cell(title, headline, sub):
    return (f'<div class="flag"><div class="flag-t">{title}</div>'
            f'<div class="flag-h">{headline}</div><div class="flag-s">{sub}</div></div>')


def step_cell(n, title, text):
    return (f'<div class="step"><div class="step-n">{n}</div>'
            f'<div class="step-t">{title}</div><div class="step-p">{text}</div></div>')


def read_any(f):
    if f.name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(f)
    return pd.read_csv(f)


# ---------- Sidebar: data ----------
with st.sidebar:
    st.header("1. Data")
    prod_file = st.file_uploader("Production file (CSV/Excel)", type=["csv", "xlsx", "xls"])
    sales_file = st.file_uploader("Sales file (CSV/Excel)", type=["csv", "xlsx", "xls"])
    cat_file = st.file_uploader("Products file (optional)", type=["csv", "xlsx", "xls"])
    if st.button("Use sample data"):
        st.session_state["use_sample"] = True

using_upload = bool(prod_file and sales_file)
using_sample = (not using_upload) and st.session_state.get("use_sample", False)
if using_upload:
    source_line = '<span class="dot ok"></span>Showing your uploaded files'
elif using_sample:
    source_line = '<span class="dot"></span>Showing simulated sample data'
else:
    source_line = ""

st.markdown('<div class="hazard"></div>'
            '<div class="title">MfgInsights</div>'
            '<div class="tagline">Factory and sales data in one view, with an AI analyst that tells you what to fix first.</div>'
            f'<div class="source">{source_line}</div>', unsafe_allow_html=True)

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
            '<div class="steps">'
            + step_cell("1", "Upload your files", "Production and sales, as CSV or Excel. Column names don't need to match.")
            + step_cell("2", "See one view", "We clean and merge them, then work out defect rate, availability, on-time delivery and revenue lost to downtime.")
            + step_cell("3", "Ask the analyst", "Get the top issues and what to fix first, in plain language.")
            + '</div>'
            '<div class="note">No files handy? Choose Use sample data in the sidebar.</div>',
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
    st.header("2. Filters")
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Operations", "Sales", "Connected insights", "AI analyst"]
)

# ---------- Overview ----------
with tab1:
    st.markdown(
        '<div class="strip">'
        + kpi_cell("Units produced", f"{units:,.0f}", f"{len(by_machine)} machines")
        + kpi_cell("Defect rate", f"{defect_rate:.1%}",
                   "Within the 2.5% target" if defect_rate <= 0.025 else "Above the 2.5% target",
                   "ok" if defect_rate <= 0.025 else "bad")
        + kpi_cell("Machine availability", f"{availability:.1%}",
                   "Above the 90% target" if availability >= 0.9 else "Below the 90% target",
                   "ok" if availability >= 0.9 else "bad")
        + kpi_cell("Revenue", f"₹{revenue:,.0f}", "Selected period")
        + kpi_cell("On-time delivery", f"{on_time:.1%}",
                   "Above the 90% target" if on_time >= 0.9 else "Below the 90% target",
                   "ok" if on_time >= 0.9 else "bad")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Needs attention")
    st.markdown(
        '<div class="flags">'
        + flag_cell("Downtime hotspot", f"{worst_row['machine_id']} lost {worst_row['downtime_hours']:,.0f} hours",
                    "Most downtime of any machine")
        + flag_cell("Quality hotspot", f"{quality_row['machine_id']} at {quality_row['defect_rate_%']:.1f}% defects",
                    f"Plant average is {defect_rate:.1%}")
        + flag_cell("Delivery risk", f"{late_row['product']}: {late_row['late_%']:.0f}% late",
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
with tab2:
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

    st.subheader("Machines, worst first")
    table = by_machine.sort_values("downtime_hours", ascending=False).rename(columns={
        "machine_id": "Machine", "downtime_hours": "Downtime (h)", "defective": "Defective units",
        "units": "Units", "defect_rate_%": "Defect rate (%)",
    })
    st.dataframe(table, width="stretch", hide_index=True)

# ---------- Sales ----------
with tab3:
    reg = sales_f.groupby("region", as_index=False)["revenue"].sum()
    top = sales_f.groupby("product", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
    left, right = st.columns(2)
    with left:
        show(px.bar(reg, x="region", y="revenue", title="Revenue by region"), money=True)
    with right:
        show(px.bar(top, x="product", y="revenue", title=f"{top.iloc[0]['product']} brings in the most revenue"), money=True)

    m_rev2 = sales_f.groupby("month", as_index=False)["revenue"].sum()
    fig = px.scatter(m_rev2, x="month", y="revenue", trendline="ols", title="Revenue by month with trendline")
    fig.update_traces(marker_color=BLUE, selector=dict(mode="markers"))
    fig.update_traces(line_color=INK, line_dash="dash", selector=dict(mode="lines"))
    show(fig, money=True)

# ---------- Connected insights ----------
with tab4:
    st.markdown("Where problems on the factory floor show up in the business.")
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
with tab5:
    st.subheader("Ask the analyst")
    st.caption("Answers use the data currently shown, so your filters apply.")

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
