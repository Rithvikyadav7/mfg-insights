import numpy as np
import pandas as pd

ALIASES = {
    "machine": "machine_id", "machineid": "machine_id",
    "product": "product_id", "productid": "product_id", "sku": "product_id", "item": "product_id",
    "production_date": "date", "units": "units_produced", "output": "units_produced",
    "defects": "defective_units", "defect_units": "defective_units",
    "downtime": "downtime_hours", "downtime_hrs": "downtime_hours",
    "planned_hrs": "planned_hours", "qty": "quantity", "amount": "revenue",
    "sales": "revenue", "orderdate": "order_date", "delivery": "delivery_date",
    "promised": "promised_date", "due_date": "promised_date", "name": "product_name",
}


def _std(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df.rename(columns=ALIASES)


def _need(df, cols, name):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"{name} file is missing: {', '.join(missing)}. Columns found: {', '.join(df.columns)}"
        )


def clean_production(df):
    df = _std(df)
    _need(df, ["date", "machine_id", "product_id", "planned_hours",
               "downtime_hours", "units_produced", "defective_units"], "Production")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["planned_hours", "downtime_hours", "units_produced", "defective_units"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["machine_id"] = df["machine_id"].astype(str).str.strip()
    if "downtime_reason" not in df.columns:
        df["downtime_reason"] = "Unknown"
    df["downtime_reason"] = df["downtime_reason"].fillna("None")
    return df.dropna(subset=["date"]).drop_duplicates()


def clean_sales(df):
    df = _std(df)
    _need(df, ["order_date", "promised_date", "delivery_date",
               "product_id", "quantity", "revenue"], "Sales")
    for c in ["order_date", "promised_date", "delivery_date"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["quantity", "revenue"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["product_id"] = df["product_id"].astype(str).str.strip()
    if "region" not in df.columns:
        df["region"] = "All"
    return df.dropna(subset=["order_date"]).drop_duplicates()


def ensure_products(products, production, sales):
    if products is not None:
        products = _std(products)
        if "product_id" in products.columns:
            products["product_id"] = products["product_id"].astype(str).str.strip()
            if "product_name" not in products.columns:
                products["product_name"] = products["product_id"]
            return products[["product_id", "product_name"]].drop_duplicates()
    ids = sorted(set(production["product_id"]) | set(sales["product_id"]))
    return pd.DataFrame({"product_id": ids, "product_name": ids})


def lost_revenue_by_product(prod, sales):
    p = prod.groupby("product").agg(
        units=("units_produced", "sum"),
        planned=("planned_hours", "sum"),
        downtime_hours=("downtime_hours", "sum"),
    )
    p["run_hours"] = (p["planned"] - p["downtime_hours"]).replace(0, np.nan)
    p["units_per_hour"] = p["units"] / p["run_hours"]
    s = sales.groupby("product").agg(revenue=("revenue", "sum"), qty=("quantity", "sum"))
    s["rev_per_unit"] = s["revenue"] / s["qty"].replace(0, np.nan)
    out = p.join(s, how="inner")
    out["lost_revenue"] = out["downtime_hours"] * out["units_per_hour"] * out["rev_per_unit"]
    return out.reset_index()[["product", "downtime_hours", "lost_revenue"]].fillna(0)


def generate_sample_data(seed=42):
    rng = np.random.default_rng(seed)
    products = pd.DataFrame({
        "product_id": ["P101", "P102", "P103", "P104", "P105"],
        "product_name": ["Brake Pad", "Piston Ring", "Gear Shaft", "Fuel Pump", "Clutch Plate"],
        "unit_price": [45, 30, 120, 85, 60],
    })
    machines = ["M1", "M2", "M3", "M4", "M5"]
    machine_product = dict(zip(machines, products["product_id"]))
    reasons = ["Maintenance", "Breakdown", "Material shortage", "Changeover", "Power outage"]
    dates = pd.date_range("2025-10-01", "2026-09-30", freq="D")

    rows = []
    for d in dates:
        for m in machines:
            planned = 16
            downtime = abs(rng.normal(1.0, 0.6))
            if m == "M4":
                downtime += rng.exponential(1.5)
            if d.year == 2026 and d.month == 3:
                downtime += rng.exponential(1.5)
            downtime = min(downtime, 12)
            units = int((planned - downtime) * rng.integers(40, 61))
            defect_rate = 0.07 if m == "M3" else 0.02
            defective = int(rng.binomial(units, defect_rate))
            reason = "None"
            if downtime > 1.5:
                reason = "Breakdown" if (m == "M4" and rng.random() < 0.6) else rng.choice(reasons)
            rows.append({
                "date": d, "machine_id": m, "product_id": machine_product[m],
                "planned_hours": planned, "downtime_hours": round(downtime, 2),
                "downtime_reason": reason, "units_produced": units, "defective_units": defective,
            })
    production = pd.DataFrame(rows)

    n = 3000
    order_dates = pd.to_datetime(rng.choice(dates, n))
    pids = rng.choice(products["product_id"], n, p=[0.25, 0.2, 0.2, 0.2, 0.15])
    price = products.set_index("product_id")["unit_price"]
    qty = rng.integers(20, 300, n)
    revenue = qty * price.loc[pids].values * rng.uniform(0.95, 1.05, n)
    delay = rng.integers(-2, 3, n)
    late_boost = (pids == "P104") | ((order_dates.year == 2026) & (order_dates.month == 3))
    delay = delay + np.where(late_boost, rng.integers(2, 7, n), 0)
    promised = order_dates + pd.to_timedelta(7, unit="D")
    delivered = promised + pd.to_timedelta(delay, unit="D")
    sales = pd.DataFrame({
        "order_id": [f"O{i:05d}" for i in range(n)],
        "order_date": order_dates, "promised_date": promised, "delivery_date": delivered,
        "product_id": pids, "region": rng.choice(["North", "South", "East", "West"], n),
        "quantity": qty, "revenue": revenue.round(2),
    })
    return production, sales, products[["product_id", "product_name"]]
