# HomeBuilder Sales Dashboard - Rhodes Enterprises

I built this as part of the Rhodes Enterprises Data Engineer assessment. The goal was to take raw Homebuilder sales data and Regional Manager data and turn it into a live dashboard with AI features.

Live Dashboard: https://homebuildersales-znpajl9hjvqkafx6zlzp2t.streamlit.app

---
## What This Project Does

We have two raw files here. Homebuilder_Sales,Regional_Manager_Lookup :  a CSV of 600 home sales transactions and an Excel lookup of regional managers loads them into Snowflake, transforms them 
using dbt, and serves everything through a Streamlit dashboard with Snowflake Cortex AI built in.

---

## How to Access It

The dashboard is live and public just click the link above. No login needed. The Streamlit app connects to a private Snowflake instance with the 
assessment data. Local setup is not possible without access to the underlying Snowflake environment.
---

## How the Data Flows

**Step 1 - Raw data lands in Snowflake** 

**Step 2 - dbt cleans it (STAGING)** : The staging models fix data types, handle nulls, add boolean flags like is_closed and is_cancelled,
and calculate simple derived fields like price per square foot and days to close. Nothing analytical here just cleaning.

**Step 3 - dbt joins it (INTERMEDIATE)** : One model whose only job is to join the sales data to the regional manager lookup table. I kept this separate from the mart so that join 
logic and metric calculations never live in the same file.

**Step 4 - dbt builds the metrics (MART)** : The final fact_sales table has all business metrics calculated and ready for the dashboard to query. 

**Step 5 - Streamlit serves it** : The dashboard reads from MART in real time, applies whatever filters the user selects, and passes the filtered data to the AI features.

---

## What Each File Does

**app.py** : The entire Streamlit dashboard. Connects to Snowflake, loads data, applies sidebar filters, renders all 5 visualisations, runs the 
Cortex AI features, and handles the natural language chat interface.

**models/staging/stg_homebuilder_sales.sql** : Cleans the raw sales CSV. Fixes column types, adds boolean flags, calculates price_per_sqft and days_to_close, adds a contract_outcome 
label (Closed / Cancelled / In Progress).

**models/staging/stg_regional_manager_lookup.sql** :  Cleans the 3 row regional manager lookup table. Small model but important staging everything means it gets the same data quality 
tests as everything else.

**models/intermediate/int_sales.sql** : Joins the two staging models on the region column.  Keeping joins here means the mart model only has to think about metrics.

**models/mart/fct_sales.sql** : The final table. Selects from int_sales and adds 7 business metrics incentive intensity, commission efficiency, net value added, binary 
closed/cancelled flags, days to close, and price per sqft. 

**macros/generate_schema_name.sql** : Controls which Snowflake schema each dbt model deploys to. Without this, dbt adds environment prefixes to schema names. With it, the 
schemas are clean - STAGING, INTERMEDIATE, MART.

**dbt_project.yml** : The dbt project config. Defines the project name, model paths, and which schemas each folder deploys to.

**requirements.txt** : Python dependencies for the Streamlit app - snowflake-connector-python, streamlit, pandas, plotly.

---

## Dashboard Features

- 5 KPI cards at the top - closed units, revenue, cancellation rate, avg days to close, target attainment
- Regional sales vs annual target chart
- Cancellation rate by community (colour coded red/orange/green)
- Buyer source breakdown - which channels produce real buyers
- Sales consultant performance bubble chart
- Community scorecard table with health filters
- 6 sidebar filters - region, year, consultant, community, loan type, date range
- AI sales forecast - Cortex FORECAST predicts next 3 months by region
- AI executive summary - one button generates 4 strategic bullet points from your current filtered view
- Natural language chat - ask plain English questions about the data

---

## Data

- 600 total contracts (528 closed, 41 cancelled, 31 in progress)
- $162M total revenue
- 3 regions - South Texas, Rio Grande Valley, Coastal Bend
- Date range - January 2023 to October 2024
- Data ingestion - Both source files were loaded into the RAW schema using the Snowflake web UI file upload. 

---

## Known Limitations

- 2024 data ends October 2 - the year is not complete
- Forecast was trained on data ending Oct 2024 - in production it would retrain every month
- The AI summary reads pre-aggregated data, not raw rows, complex cross dimensional questions may be outside its scope
- Target attainment uses full annual targets even when a date filter is applied

---

## What I Would Do Next

- Use Cortex ANALYST instead of COMPLETE for the NL query it generates live SQL rather than reading pre summarised data
- Add a cancellation risk model using Cortex CLASSIFICATION to flag deals likely to cancel at contract creation time
- Automate monthly forecast retraining as new closing data arrives
