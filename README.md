<img width="1917" height="906" alt="overview png" src="https://github.com/user-attachments/assets/78031e9c-3715-4838-9783-22b20f6503f7" />
<img width="1917" height="960" alt="landing png" src="https://github.com/user-attachments/assets/bbc8ee37-0c3d-4866-a3be-140967ffb633" />
# OpsView

**Factory and sales data in one view, with an AI analyst that tells you what to fix first.**

OpsView unifies a manufacturer's scattered production and sales files into one live dashboard. It flags problem machines, quality issues and late deliveries, estimates the revenue lost to downtime, and includes an AI analyst that answers questions in plain language.

Live app: https://mfg-insights.streamlit.app

Built in 24 hours for the hackathon's Analytics track. Problem statement: *Unify manufacturing data to show operational metrics, sales performance and trends.*

## The problem

Small and mid-sized manufacturers keep production logs and sales orders in separate spreadsheets. Files use different column names, date formats and product codes, so nobody sees how a machine breakdown turns into a late order. Managers find out when the customer calls.

## What OpsView does

1. **Upload** a production file and a sales file (CSV or Excel). Column names do not have to match.
2. **Unify.** OpsView cleans the files, standardises columns, dates and numbers, removes duplicates and merges everything by product.
3. **See one view.** Dashboards cover operations, sales and trends, and a "Needs attention" row flags the worst machine, the biggest quality problem and the product most at risk of late delivery.
4. **Connect the two sides.** Production and sales are shown together, with an estimate of revenue lost to downtime.
5. **Ask the AI analyst.** Ask questions such as "What should the plant manager fix first?" and get an answer with numbers and recommended actions.

## Pages

| Page | What it shows |
|---|---|
| Overview | KPI cards (units, defect rate, availability, revenue, on-time delivery), the "Needs attention" row, monthly revenue and output |
| Operations | Downtime by machine and by reason, defect rate by month, a table of machines ranked worst first |
| Sales | Revenue by region and product, with a monthly trendline |
| Connected insights | Production against customer orders, estimated revenue lost to downtime, late-delivery rate by product |
| AI analyst | Example questions, free-text questions, and a "top 5 insights and actions" report that can be downloaded |
## What the live app looks like

On the simulated sample plant (1 Oct 2025 to 30 Sep 2026), the Overview page shows:

| Measure | Value |
|---|---|
| Units produced | 1,323,114 across 5 machines |
| Defect rate | 3.0% (target at or below 2.5%) |
| Machine availability | 91.1% (target at or above 90%) |
| Revenue | ₹32,758,085 |
| On-time delivery | 60.8% (target at or above 90%) |

The "Needs attention" row flags three planted problems:

- **Downtime hotspot:** M4 lost 957 hours, the most of any machine.
- **Quality hotspot:** M3 has a 7.0% defect rate against a plant average of 3.0%.
- **Delivery risk:** Fuel Pump orders are 87% late, the highest rate.

A badge at the top of the app states that the data is simulated.

![Landing screen](landing.png)

![Overview page](overview.png)

## How the metrics are calculated

- **Defect rate** = defective units / units produced
- **Machine availability** = 1 - downtime hours / planned hours
- **On-time delivery** = share of orders delivered on or before the promised date
- **Estimated revenue lost to downtime** = downtime hours x units per run-hour x average revenue per unit. This is an estimate that shows where to look. It is not an accounting figure.

The target thresholds shown on the KPI cards (defect rate at or below 2.5%, availability and on-time delivery at or above 90%) are illustrative defaults.

## How the AI works

The app does not send raw rows to the model. It computes summary tables (monthly production and sales, per-machine figures, downtime reasons, late-delivery rates, revenue by product, estimated losses) and sends those with the question. The model is instructed to answer only from that summary, quote numbers, and say so when the data does not contain the answer. If the first model is unavailable, the app tries a backup model and then shows a clear message. The dashboard works without the AI.

## Tech stack

- **App and backend:** Python, Streamlit
- **Data processing:** Pandas, NumPy, openpyxl
- **Charts and trend fitting:** Plotly, statsmodels
- **AI:** Google Gemini API (`google-genai`)
- **Hosting:** Streamlit Community Cloud, deployed from this repository
- **Storage:** none. Uploaded files are processed in memory and are not saved.

## Input files

| File | Required columns | Optional |
|---|---|---|
| Production | `date`, `machine_id`, `product_id`, `planned_hours`, `downtime_hours`, `units_produced`, `defective_units` | `downtime_reason` |
| Sales | `order_date`, `promised_date`, `delivery_date`, `product_id`, `quantity`, `revenue` | `region` |
| Products | `product_id`, `product_name` | |

Common variants such as `SKU`, `Qty`, `Amount`, `Downtime`, `Units` or `Defects` are recognised. If a required column is missing, the app lists the columns it found. The sidebar also has a **Use sample data** button that loads a simulated plant with deliberately planted problems (one machine with heavy downtime, one with a quality issue, one product with late deliveries).

## Run locally

```bash
git clone https://github.com/Rithvikyadav7/mfg-insights.git
cd mfg-insights
pip install streamlit pandas numpy plotly openpyxl statsmodels google-genai
```

Create `.streamlit/secrets.toml` and add your Gemini API key:

```toml
GEMINI_API_KEY = "your-key-here"
```

Then start the app:

```bash
streamlit run app.py
```

Never commit your API key. On Streamlit Community Cloud, add it under the app's Secrets settings instead.

## Project structure

```
app.py                  Streamlit app: layout, navigation, charts, AI analyst
utils.py                Cleaning, merging, metrics and sample-data generator
requirements.txt        Python dependencies
.streamlit/config.toml  Theme
```

## Limitations

- The demo runs on simulated data. It has not yet been validated on a real plant's data.
- Files are uploaded manually. There is no live connection to ERP or MES systems.
- No login, user accounts or saved history yet.
- Column matching covers common names. Unusual headers need a manual mapping step, which is not built yet.
- The AI uses a free-tier API, so it can be rate-limited.

## Roadmap

- Direct connectors for ERP and MES systems
- Manual column mapping for unusual files
- Login, company workspaces and saved dashboards
- Alerts by email or WhatsApp when a machine or product crosses a threshold
- Predictive maintenance from downtime patterns

## License

MIT. See [LICENSE](LICENSE).
