import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from google.genai import types

from utils import (clean_production, clean_sales, ensure_products,
                   generate_sample_data, lost_revenue_by_product)

st.set_page_config(page_title="MfgInsights", page_icon="🏭", layout="wide")
st.title("🏭 MfgInsights")
st.caption("Unify factory and sales data into one dashboard, with an AI analyst.")


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

try:
    if prod_file and sales_file:
        production = clean_production(read_any(prod_file))
        sales = clean_sales(read_any(sales_file))
        products = ensure_products(read_any(cat_file) if cat_file else None, production, sales)
    elif st.session_state.get("use_sample"):
        p, s, pr = generate_sample_data()
        production, sales = clean_production(p), clean_sales(s)
        products = ensure_products(pr, production, sales)
    else:
        st.markdown("### From scattered spreadsheets to one live view")
        a, b, c = st.columns(3)
        a.markdown("**1️⃣ Upload**  \nDrop in your production and sales files (CSV or Excel). Column names don't have to match.")
        b.markdown("**2️⃣ Unify**  \nWe clean and merge them, then calculate defect rate, availability, on-time delivery and revenue lost to downtime.")
        c.markdown("**3️⃣ Ask**  \nSee operations and sales together, then ask the AI analyst what to fix first.")
        st.info("👈 Upload your files, or click **Use sample data** in the sidebar to see it in action.")
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Overview", "⚙️ Operations", "💰 Sales", "🔗 Connected Insights", "🤖 AI Analyst"]
)

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Units produced", f"{units:,.0f}")
    c2.metric("Defect rate", f"{defect_rate:.1%}")
    c3.metric("Machine availability", f"{availability:.1%}")
    c4.metric("Revenue", f"₹{revenue:,.0f}")
    c5.metric("On-time delivery", f"{on_time:.1%}")
    m_rev = sales_f.groupby("month", as_index=False)["revenue"].sum()
    st.plotly_chart(px.line(m_rev, x="month", y="revenue", markers=True, title=f"Monthly revenue: peaked in {m_rev.loc[m_rev['revenue'].idxmax(), 'month']:%b %Y}"), width="stretch")
    m_units = prod_f.groupby("month", as_index=False)["units_produced"].sum()
    st.plotly_chart(px.line(m_units, x="month", y="units_produced", markers=True, title="Monthly units produced"), width="stretch")

with tab2:
    by_machine = prod_f.groupby("machine_id", as_index=False).agg(
        downtime_hours=("downtime_hours", "sum"),
        defective=("defective_units", "sum"),
        units=("units_produced", "sum"),
    )
    by_machine["defect_rate_%"] = (by_machine["defective"] / by_machine["units"] * 100).round(2)
    a, b = st.columns(2)
        worst = by_machine.sort_values("downtime_hours", ascending=False).iloc[0]
    a.plotly_chart(px.bar(by_machine, x="machine_id", y="downtime_hours", title=f"{worst['machine_id']} has the most downtime ({worst['downtime_hours']:,.0f} hours)"), width="stretch")
    reasons = prod_f[prod_f["downtime_reason"] != "None"].groupby("downtime_reason", as_index=False)["downtime_hours"].sum()
    b.plotly_chart(px.bar(reasons, x="downtime_reason", y="downtime_hours", title="Downtime by reason"), width="stretch")
    m_def = prod_f.groupby("month", as_index=False).agg(d=("defective_units", "sum"), u=("units_produced", "sum"))
    m_def["defect_rate_%"] = m_def["d"] / m_def["u"] * 100
    st.plotly_chart(px.line(m_def, x="month", y="defect_rate_%", markers=True, title="Defect rate trend (%)"), width="stretch")
    st.subheader("Machines needing attention")
    st.dataframe(by_machine.sort_values("downtime_hours", ascending=False), width="stretch")

with tab3:
    a, b = st.columns(2)
    reg = sales_f.groupby("region", as_index=False)["revenue"].sum()
    a.plotly_chart(px.bar(reg, x="region", y="revenue", title="Revenue by region"), width="stretch")
    top = sales_f.groupby("product", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
    b.plotly_chart(px.bar(top, x="product", y="revenue", title="Revenue by product"), width="stretch")
    m_rev2 = sales_f.groupby("month", as_index=False)["revenue"].sum()
    st.plotly_chart(
        px.scatter(m_rev2, x="month", y="revenue", trendline="ols", title="Revenue trend with trendline"),
        width="stretch",
    )

with tab4:
    st.markdown("**Where factory problems hit the business.**")
    pm = prod_f.groupby("month", as_index=False).agg(units_produced=("units_produced", "sum"))
    sm = sales_f.groupby("month", as_index=False).agg(units_ordered=("quantity", "sum"))
    both = pm.merge(sm, on="month", how="outer").melt("month", var_name="measure", value_name="units")
    st.plotly_chart(px.line(both, x="month", y="units", color="measure", markers=True, title="Production vs customer orders"), width="stretch")
    a, b = st.columns(2)
    a.plotly_chart(px.bar(lost, x="product", y="lost_revenue",title=f"₹{lost['lost_revenue'].sum():,.0f} estimated revenue lost to downtime"), width="stretch")
    late = sales_f.groupby("product", as_index=False)["late"].mean()
    late["late_%"] = late["late"] * 100
    b.plotly_chart(px.bar(late, x="product", y="late_%", title=f"{late.sort_values('late_%').iloc[-1]['product']} has the highest late-delivery rate (%)""), width="stretch")
    st.caption("Lost revenue = downtime hours × units per run-hour × average revenue per unit (an estimate).")

with tab5:
    st.subheader("🤖 AI Analyst")
    st.caption("Ask questions about the data currently shown (your filters apply).")

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
        reasons = prod_f[prod_f["downtime_reason"] != "None"].groupby("downtime_reason")["downtime_hours"].sum().round(1)
        late_p = sales_f.groupby("product")["late"].mean().mul(100).round(1)
        rev_p = sales_f.groupby("product")["revenue"].sum().round(0)
        return (
            f"OVERALL: units={units:,.0f}; defect_rate={defect_rate:.1%}; "
            f"machine_availability={availability:.1%}; revenue=Rs{revenue:,.0f}; on_time_delivery={on_time:.1%}\n\n"
            f"MONTHLY PRODUCTION:\n{m_prod.to_csv()}\n"
            f"MONTHLY SALES:\n{m_sales.to_csv()}\n"
            f"BY MACHINE:\n{machines.to_csv()}\n"
            f"DOWNTIME HOURS BY REASON:\n{reasons.to_csv()}\n"
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

    st.markdown("**Try a question:**")
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

    typed = st.text_input("Or ask your own question", placeholder="e.g. Which region is growing fastest?")
    if st.button("Ask") and typed.strip():
        run(typed.strip())

    st.divider()
    if st.button("✨ Generate Top 5 Insights & Recommended Actions", type="primary"):
        run(
            "Give the top 5 insights from this data as a numbered list. For each, state the "
            "evidence (numbers) and one recommended action. Cover operations, sales, and how "
            "factory problems affect customer delivery and revenue."
        )

    res = st.session_state.get("ai_result")
    if res:
        st.markdown(f"**Q:** {res['q']}")
                st.markdown(res["a"])
        st.download_button("⬇️ Download this insight", f"Q: {res['q']}\n\n{res['a']}", file_name="insights.txt")
