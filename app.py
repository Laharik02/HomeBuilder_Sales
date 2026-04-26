import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# Page configuration
st.set_page_config(
    page_title="Rhodes Enterprises Home Builder Sales Dashboard",
    layout="wide"
)

# Snowflake connection and load data
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"]
    )


# Load all data from the mart table
# Cache for 5 minutes so filters don't keep querying Snowflake on every click
@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM FACT_SALES", conn)
    df.columns = df.columns.str.lower()
    df['contract_date'] = pd.to_datetime(df['contract_date'])
    df['close_date'] = pd.to_datetime(df['close_date'])
    return df

df = load_data()

# Sidebar for any chart updates automatically when these change
st.sidebar.header("Filters")

# Region filter for distinct region
regions = ["All"] + sorted(df['region'].unique().tolist())
selected_region = st.sidebar.selectbox("Region", regions)

# Year filter for distinct year
years = ["All"] + sorted(df['contract_year'].unique().tolist())
selected_year = st.sidebar.selectbox("Year", years)

# Consultant filter
consultants = ["All"] + sorted(df['sales_consultant'].unique().tolist())
selected_consultant = st.sidebar.selectbox("Consultant", consultants)

# Community filter
communities = ["All"] + sorted(df['community'].unique().tolist())
selected_community = st.sidebar.selectbox("Community", communities)

# Loan type filter
loan_types = ["All"] + sorted(df['loan_type'].unique().tolist())
selected_loan = st.sidebar.selectbox("Loan Type", loan_types)

# Date range filter - specific for date range and custom range
st.sidebar.subheader("Date Range")
date_option = st.sidebar.radio(
    "Select period:",
    options=[
        "All Time",
        "2023 Only",
        "2024 Only",
        "H1 2023 (Jan-Jun)",
        "H2 2023 (Jul-Dec)",
        "H1 2024 (Jan-Jun)",
        "H2 2024 (Jul-Oct, partial)",
        "Custom Range"
    ]
)


min_date = df['contract_date'].min().date()
max_date = df['contract_date'].max().date()

if date_option == "2023 Only":
    start_date = date(2023, 1, 1)
    end_date = date(2023, 12, 31)
elif date_option == "2024 Only":
    start_date = date(2024, 1, 1)
    end_date = date(2024, 12, 31)
elif date_option == "H1 2023 (Jan-Jun)":
    start_date = date(2023, 1, 1)
    end_date = date(2023, 6, 30)
elif date_option == "H2 2023 (Jul-Dec)":
    start_date = date(2023, 7, 1)
    end_date = date(2023, 12, 31)
elif date_option == "H1 2024 (Jan-Jun)":
    start_date = date(2024, 1, 1)
    end_date = date(2024, 6, 30)
elif date_option == "H2 2024 (Jul-Oct, partial)":
    start_date = date(2024, 7, 1)
    end_date = date(2024, 10, 2)
elif date_option == "Custom Range":
    start_date = st.sidebar.date_input(
        "From date",
        value=min_date
    )
    end_date = st.sidebar.date_input(
        "To date",
        value=max_date
    )
else:
    start_date = min_date
    end_date = max_date


# combine all these to create a filtered df
filtered = df.copy()
if selected_region != "All":
    filtered = filtered[filtered['region'] == selected_region]
if selected_year != "All":
    filtered = filtered[filtered['contract_year'] == selected_year]
if selected_consultant != "All":
    filtered = filtered[filtered['sales_consultant'] == selected_consultant]
if selected_community != "All":
    filtered = filtered[filtered['community'] == selected_community]
if selected_loan != "All":
    filtered = filtered[filtered['loan_type'] == selected_loan]

filtered = filtered[
    (filtered['contract_date'].dt.date >= start_date) &
    (filtered['contract_date'].dt.date <= end_date)
]

active_filters = []
if selected_consultant != "All":
    active_filters.append(f"Consultant: {selected_consultant}")
if selected_community != "All":
    active_filters.append(f"Community: {selected_community}")
if selected_region != "All":
    active_filters.append(f"Region: {selected_region}")
if active_filters:
    st.sidebar.info(f"Filtered by: {', '.join(active_filters)}")

# KPI'S Dashboard header
st.title("Rhodes Enterprises:  Home Builder Sales Performance Dashboard")
st.caption("Live data from Snowflake : Home Builder Sales | Contract dates: Jan 2023 — Oct 2024")
st.divider()

# Calculate KPI values from above filtered data
total_contracts = len(filtered)
closed = int(filtered['net_closed_unit'].sum())
cancelled = int(filtered['cancelled_unit'].sum())

# Cancellation rate  cancelled deals divided by total contracts
cancellation_rate = round(cancelled / total_contracts * 100, 1) if total_contracts > 0 else 0

# Total revenue from all closed deals only
total_revenue = filtered[filtered['is_closed'] == True]['contract_price'].sum()

# Average days to close for for closed deals, not cancelled or in progress
avg_days = filtered[filtered['is_closed'] == True]['days_to_close'].mean()

# Target areas  closed units vs sum of regional targets
closed_target = filtered.groupby('region')['regional_unit_target'].first().sum()
target_attainment = round(closed / closed_target * 100, 1) if closed_target > 0 else 0

#  5 KPI cards dashboard
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Closed Units", f"{closed:,}")
col2.metric("Total Revenue", f"${total_revenue/1_000_000:.1f}M")
col3.metric("Cancellation Rate", f"{cancellation_rate}%")
col4.metric("Avg Days to Close", f"{avg_days:.0f}" if not pd.isna(avg_days) else "N/A")
col5.metric("Target Attainment", f"{target_attainment}%")

if selected_region != "All" and len(filtered) > 0:
    manager = filtered['regional_manager'].iloc[0]
    st.caption(f"Regional Manager for {selected_region}: {manager}")

# Show context note whenever data is filtered by time
if selected_year != "All" or date_option != "All Time":
    st.caption(f"Note: Target Attainment is calculated against full annual regional targets (380 units total). Current view is filtered - numbers reflect the selected period only.")

# Specific warning for partial 2024 data
if date_option in ["2024 Only", "H2 2024 (Jul-Oct, partial)", "H1 2024 (Jan-Jun)"] or str(selected_year) == "2024":
    st.caption("Note: 2024 data ends October 2, 2024 - full year target attainment not yet achievable.")


st.divider()


# Visualizations 

# Visualization 1: "Regional Sales Pace vs Annual Target"
# To keep track of cumulative closed units over time as a line for all te regions 

st.subheader("Regional Sales vs Annual Target")
st.caption("Actual cumulative closed units vs target path by region")

closed_df = filtered[filtered['is_closed'] == True].copy()

if len(closed_df) == 0:
    st.info("No closed deals found for the selected filters.")
else:
    closed_df = closed_df.sort_values('close_date')
    closed_df['cumulative_closed'] = closed_df.groupby('region').cumcount() + 1
    #  one line per region showing cumulative closed units over time
    fig1 = px.line(
        closed_df,
        x='close_date',
        y='cumulative_closed',
        color='region',
        markers=False,
        color_discrete_sequence=['#1D9E75', '#534AB7', '#E8593C'],
        labels={'close_date': 'Date', 'cumulative_closed': 'Cumulative Closed Units'}
    )

    # Add a dashed straight line target for each region

    for region in closed_df['region'].unique():
     
        target = closed_df[closed_df['region'] == region]['regional_unit_target'].iloc[0]
        min_date = closed_df['close_date'].min()
        max_date = closed_df['close_date'].max()
        fig1.add_trace(go.Scatter(
            x=[min_date, max_date],
            y=[0, target],
            mode='lines',
            line=dict(dash='dash', width=1),
            name=f'{region} Target',
            showlegend=True
        ))

    fig1.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title="Cumulative Closed Units",
        legend=dict(orientation='h', y=-0.2)
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.divider()


# Visualization 2: "Cancellation Rate by Community"


st.subheader("Cancellation Rate by Community")
st.caption("Which communities are losing the most deals? higher % rate means more revenue at risk")

# Calculate the actual cancellation rate per community
community_cancel = filtered.groupby('community').agg(
    total=('contract_id', 'count'),
    cancelled=('cancelled_unit', 'sum'),
    closed=('net_closed_unit', 'sum')
).reset_index()

# Get the cancellation rate as percentage
community_cancel['cancellation_rate'] = (
    community_cancel['cancelled'] / community_cancel['total'] * 100
).round(1)

# Sorting so highest cancellation appears at the top
community_cancel = community_cancel.sort_values('cancellation_rate', ascending=True)

# Bar chart 
fig2 = px.bar(
    community_cancel,
    x='cancellation_rate',
    y='community',
    orientation='h',
    color='cancellation_rate',
    color_continuous_scale=['#1D9E75', '#EF9F27', '#E8593C'],
    text='cancellation_rate'
)
fig2.update_traces(texttemplate='%{text}%', textposition='outside')
fig2.update_layout(
    height=400,
    xaxis_title="Cancellation Rate %",
    yaxis_title="",
    coloraxis_showscale=False,
    margin=dict(r=60)
)
st.plotly_chart(fig2, use_container_width=True)
if len(community_cancel) == 1:
    st.caption("Showing single community. Select 'All' in Community filter to compare across communities.")
st.markdown("**Above 10%** — High risk, needs immediate attention &nbsp;&nbsp; **5–10%** — Monitor closely &nbsp;&nbsp; **Below 5%** — Healthy")
st.divider()


#Visualization 3: Buyer Source and Success Rate Effectiveness
# analysis for marketing budget efficiency

st.subheader("Buyer Source - Closed, In Progress and Cancelled by Source")
st.caption(" Every lead channel and how contracts from that source ended up - green is closed, blue is still in progress, red is cancelled. Bigger bar means more total volume from that source.")

source_summary = filtered.groupby('buyer_source').agg(
    total=('contract_id', 'count'),
    cancelled=('cancelled_unit', 'sum'),
    closed=('net_closed_unit', 'sum')
).reset_index()

source_summary['cancellation_rate'] = (
    source_summary['cancelled'] / source_summary['total'] * 100
).round(1)

source_summary['close_rate'] = (
    source_summary['closed'] / source_summary['total'] * 100
).round(1)

# Stacked bar - each bar is a buyer source
# Shows full breakdown of closed, in progress and cancelled per channel - hover over 
source_stacked = filtered.groupby(
    ['buyer_source', 'contract_outcome']
).size().reset_index(name='count')

fig3 = px.bar(
    source_stacked,
    x='buyer_source',
    y='count',
    color='contract_outcome',
    barmode='stack',
    color_discrete_map={
        'Closed': '#1D9E75',
        'In Progress': '#4A90D9',
        'Cancelled': '#E8593C'
    },
    text='count',
    labels={
        'buyer_source': 'Buyer Source',
        'count': 'Number of Contracts',
        'contract_outcome': 'Status'
    }
)
fig3.update_traces(
    textposition='inside',
    textfont=dict(size=13, color='white', family='Arial Black'),
    insidetextanchor='middle'
)
fig3.update_layout(
    height=550,
    xaxis_tickangle=30,
    legend=dict(orientation='h', y=1.08, x=0),
    xaxis_title="",
    yaxis_title="Number of Contracts",
    margin=dict(b=100, t=60)
)
st.plotly_chart(fig3, use_container_width=True)

#  summary for leadership
top_cancel = source_summary.sort_values(
    'cancellation_rate', ascending=False
).iloc[0]
best_source = source_summary.sort_values(
    'close_rate', ascending=False
).iloc[0]

st.info(
    f"**Insights** {top_cancel['buyer_source']} has the highest cancellation "
    f"rate at {top_cancel['cancellation_rate']}%. "
    f"{best_source['buyer_source']} produces the highest quality leads "
    f"with a {best_source['close_rate']}% close rate."
)
st.divider()


#Visualization 4: Sales Consultant Scorecard

# X axis is Avg Days to Close abd Y axis is Close Rate % 
# Bubble size - Revenue generated
# Quadrant lines divide chart into 4 performance zones

st.subheader("Sales Consultant Performance")
st.caption("Speed vs quality vs revenue — bubble size shows total revenue generated")

consultant_data = filtered.groupby('sales_consultant').agg(
    total=('contract_id', 'count'),
    closed=('net_closed_unit', 'sum'),
    revenue=('contract_price', 'sum'),
    avg_days=('days_to_close', 'mean'),
    avg_incentive=('incentive_intensity_pct', 'mean')
).reset_index()

consultant_data['close_rate'] = (
    consultant_data['closed'] / consultant_data['total'] * 100
).round(1)
consultant_data['avg_days'] = consultant_data['avg_days'].round(1)
consultant_data['revenue_millions'] = (
    consultant_data['revenue'] / 1_000_000
).round(2)

# Square the revenue to amplify size differences between consultants
consultant_data['bubble_size'] = consultant_data['revenue_millions'] ** 2

fig4 = px.scatter(
    consultant_data,
    x='avg_days',
    y='close_rate',
    size='bubble_size',
    color='close_rate',
    color_continuous_scale=['#E8593C', '#EF9F27', '#1D9E75'],
    text='sales_consultant',
    size_max=80,
    labels={
        'avg_days': 'Avg Days to Close',
        'close_rate': 'Close Rate %',
        'sales_consultant': 'Consultant'
    },
    hover_data={
        'sales_consultant': True,
        'close_rate': True,
        'avg_days': True,
        'revenue_millions': ':.2f',
        'total': True,
        'bubble_size': False
    }
)

fig4.update_traces(
    textposition='top center',
    textfont=dict(size=12, color='white')
)

# Quadrant reference lines at the average
avg_days_mid = consultant_data['avg_days'].mean()
close_rate_mid = consultant_data['close_rate'].mean()

fig4.add_hline(
    y=close_rate_mid,
    line_dash='dash',
    line_color='gray',
    opacity=0.5,
    annotation_text=f'Avg Close Rate {close_rate_mid:.1f}%',
    annotation_position='right'
)
fig4.add_vline(
    x=avg_days_mid,
    line_dash='dash',
    line_color='gray',
    opacity=0.5,
    annotation_text=f'Avg {avg_days_mid:.0f} days',
    annotation_position='top'
)

fig4.update_layout(
    height=500,
    coloraxis_showscale=False,
    xaxis_title='Avg Days to Close (lower is better)',
    yaxis_title='Close Rate % (higher is better)',
    margin=dict(t=40, b=40, r=120)
)

st.plotly_chart(fig4, use_container_width=True)
if len(consultant_data) == 1:
    st.caption("Showing single consultant. Select 'All' in Consultant filter to compare performance.")
st.markdown("""
**How to read this:**
- **Top left** = fast closer and high close rate
- **Top right** = high close rate but longer time
- **Bubble size** = total revenue generated - bigger means more revenue
""")
st.divider()


# Visualization 5: Community Health Heatmap
# every community across 4 key metrics simultaneously

st.subheader("Community Scorecard")
st.caption("Every community rated across key metrics - sort and filter to find what needs attention")

# Calculate metrics per community
community_health = filtered.groupby('community').agg(
    total=('contract_id', 'count'),
    closed=('net_closed_unit', 'sum'),
    cancelled=('cancelled_unit', 'sum'),
    avg_price_sqft=('price_per_sqft', 'mean'),
    avg_days=('days_to_close', 'mean'),
    avg_incentive=('incentive_intensity_pct', 'mean')
).reset_index()

community_health['close_rate'] = (
    community_health['closed'] / community_health['total'] * 100
).round(1)
community_health['cancellation_rate'] = (
    community_health['cancelled'] / community_health['total'] * 100
).round(1)
community_health['avg_price_sqft'] = community_health['avg_price_sqft'].round(1)
community_health['avg_days'] = community_health['avg_days'].round(1)
community_health['avg_incentive'] = community_health['avg_incentive'].round(1)

# Interactive controls
col_sort, col_filter = st.columns(2)

with col_sort:
    sort_by = st.selectbox(
        "Sort communities by:",
        options=[
            'Close Rate %',
            'Cancellation Rate %',
            'Avg Days to Close',
            'Avg Price/Sqft',
            'Incentive Rate %'
        ]
    )

with col_filter:
    health_filter = st.radio(
        "Show communities:",
        options=["All", "At Risk", "Healthy"],
        horizontal=True
    )

sort_map = {
    'Close Rate %': ('close_rate', False),
    'Cancellation Rate %': ('cancellation_rate', False),
    'Avg Days to Close': ('avg_days', True),
    'Avg Price/Sqft': ('avg_price_sqft', False),
    'Incentive Rate %': ('avg_incentive', True)
}

sort_col, sort_asc = sort_map[sort_by]
community_health = community_health.sort_values(sort_col, ascending=sort_asc)

if health_filter == "At Risk":
    community_health = community_health[
        (community_health['cancellation_rate'] > 9) |
        (community_health['close_rate'] < 85)
    ]
elif health_filter == "Healthy":
    community_health = community_health[
        (community_health['cancellation_rate'] <= 5) &
        (community_health['close_rate'] >= 90)
    ]

# Color coding function that works on numeric values
def color_cells(val, col):
    if col == 'Close Rate %':
        if val >= 90: return 'background-color: #1D9E75; color: white'
        elif val >= 85: return 'background-color: #EF9F27; color: white'
        else: return 'background-color: #E8593C; color: white'
    elif col == 'Cancellation Rate %':
        if val <= 5: return 'background-color: #1D9E75; color: white'
        elif val <= 9: return 'background-color: #EF9F27; color: white'
        else: return 'background-color: #E8593C; color: white'
    elif col == 'Avg Days to Close':
        if val <= 120: return 'background-color: #1D9E75; color: white'
        elif val <= 130: return 'background-color: #EF9F27; color: white'
        else: return 'background-color: #E8593C; color: white'
    elif col == 'Incentive Rate %':
        if val <= 1.0: return 'background-color: #1D9E75; color: white'
        elif val <= 1.2: return 'background-color: #EF9F27; color: white'
        else: return 'background-color: #E8593C; color: white'
    return ''

# Numeric display table for color coding
numeric_display = community_health[[
    'community', 'total', 'closed', 'close_rate',
    'cancellation_rate', 'avg_price_sqft', 'avg_days', 'avg_incentive'
]].rename(columns={
    'community': 'Community',
    'total': 'Total Contracts',
    'closed': 'Closed Units',
    'close_rate': 'Close Rate %',
    'cancellation_rate': 'Cancellation Rate %',
    'avg_price_sqft': 'Avg Price/Sqft',
    'avg_days': 'Avg Days to Close',
    'avg_incentive': 'Incentive Rate %'
})

#  color styling on numeric values
styled = numeric_display.style\
    .apply(
        lambda col: [color_cells(v, col.name) for v in col],
        subset=['Close Rate %', 'Cancellation Rate %', 'Avg Days to Close', 'Incentive Rate %']
    )\
    .format({
        'Close Rate %': '{:.1f}',
        'Cancellation Rate %': '{:.1f}',
        'Avg Price/Sqft': '${:.0f}',
        'Avg Days to Close': '{:.0f}',
        'Incentive Rate %': '{:.1f}'
    })

if len(community_health) == 0:
    st.info("No communities match the selected health filter. Try selecting 'All'.")
else:
    st.dataframe(styled, use_container_width=True, hide_index=True, height=320)
st.markdown("""
**Green** = strong performance &nbsp;&nbsp;
**Orange** = monitor closely &nbsp;&nbsp;
**Red** = needs immediate attention
""")
st.divider()


# PART 2B - SNOWFLAKE CORTEX AI FORECAST 2025
st.divider()
st.subheader("AI Sales Forecast - Next 3 Months (2025)")
st.caption("Powered by Snowflake Cortex ML FORECAST - predicts future closing volume by region based on historical patterns")

# Load forecast results from Snowflake
@st.cache_data(ttl=3600)
def load_forecast():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM HOMEBUILDER_DB.MART.SALES_FORECAST_RESULTS ORDER BY region, forecast_month", conn)
    df.columns = df.columns.str.lower()
    df['forecast_month'] = pd.to_datetime(df['forecast_month'])
    return df

df_forecast = load_forecast()

# Filter by selected region
if selected_region != "All":
    df_forecast_filtered = df_forecast[df_forecast['region'] == selected_region]
else:
    df_forecast_filtered = df_forecast

if df_forecast_filtered.empty:
    st.info("No forecast data available for the selected region.")
else:
    # Show forecast chart
    fig_forecast = go.Figure()

    for region in df_forecast_filtered['region'].unique():
        region_data = df_forecast_filtered[df_forecast_filtered['region'] == region]

        # Confidence band
        fig_forecast.add_trace(go.Scatter(
            x=region_data['forecast_month'].tolist() + region_data['forecast_month'].tolist()[::-1],
            y=region_data['upper_bound'].tolist() + region_data['lower_bound'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(83, 74, 183, 0.1)',
            line=dict(color='rgba(255,255,255,0)'),
            name=f'{region} Confidence Range',
            hoverinfo='skip'
        ))

        # Forecast line
        fig_forecast.add_trace(go.Scatter(
            x=region_data['forecast_month'],
            y=region_data['forecasted_units'],
            mode='lines+markers+text',
            name=f'{region} Forecast',
            text=region_data['forecasted_units'].astype(str),
            textposition='top center',
            marker=dict(size=10),
            line=dict(width=3)
        ))

    fig_forecast.update_layout(
        height=450,
        xaxis_title="Month",
        yaxis_title="Forecasted Closed Units",
        xaxis=dict(dtick='M1', tickformat='%b %Y'),
        legend=dict(orientation='h', y=-0.2),
        margin=dict(t=40, b=80)
    )

    st.plotly_chart(fig_forecast, use_container_width=True)

    # Summary table
    st.markdown("**Forecast Detail by Region**")
    display_forecast = df_forecast_filtered[['region', 'forecast_month', 'forecasted_units', 'lower_bound', 'upper_bound']].copy()
    display_forecast['forecast_month'] = display_forecast['forecast_month'].dt.strftime('%b %Y')
    display_forecast.columns = ['Region', 'Month', 'Forecasted Units', 'Lower Bound', 'Upper Bound']
    st.dataframe(display_forecast, use_container_width=True, hide_index=True)

    st.info("Forecast generated by Snowflake Cortex ML trained on 20 months of historical closing data (2023-2024)")
    st.caption("Note: Forecast reflects predictions generated from training data ending Oct 2024. In production this model would retrain on 2025 monthly data and give me results for 2026!")


# CORTEX COMPLETE - AI Executive Summary

st.divider()
st.subheader("AI Executive Summary")
st.caption("Powered by Snowflake Cortex COMPLETE - insights update based on your active filters")

if st.button("Generate AI Summary"):
    st.caption("Reads your current filtered data : closed units, revenue, cancellation rate, top and bottom performing communities and channels and generates 4 bullet points written for the Sales Director.")
    with st.spinner("Analyzing your filtered data and generating executive summary..."):
        try:
            # Dynamic calculations from the data 

            # Worst cancellation community in current filter
            community_cancel_live = filtered.groupby('community').agg(
                total=('contract_id', 'count'),
                cancelled=('cancelled_unit', 'sum')
            ).reset_index()
            community_cancel_live['cancel_rate'] = (
                community_cancel_live['cancelled'] /
                community_cancel_live['total'] * 100
            ).round(1)
            top_row = community_cancel_live.sort_values('cancel_rate', ascending=False).iloc[0]
            top_cancel_community = top_row['community']
            top_cancel_rate = top_row['cancel_rate']
     

            # Best & worst buyer channel in current filter
            source_live = filtered.groupby('buyer_source').agg(
                total=('contract_id', 'count'),
                closed=('net_closed_unit', 'sum'),
                cancelled=('cancelled_unit', 'sum')
            ).reset_index()
            source_live['close_rate'] = (
                source_live['closed'] / source_live['total'] * 100
            ).round(1)
            source_live['cancel_rate'] = (
                source_live['cancelled'] / source_live['total'] * 100
            ).round(1)

            best_row = source_live.sort_values('close_rate', ascending=False).iloc[0]
            best_channel = best_row['buyer_source']
            best_channel_rate = best_row['close_rate']

            worst_row = source_live.sort_values('cancel_rate', ascending=False).iloc[0]
            worst_channel = worst_row['buyer_source']
            worst_channel_rate = worst_row['cancel_rate']

            # Top consultant in current filter
            consultant_live = filtered.groupby('sales_consultant').agg(
                total=('contract_id', 'count'),
                closed=('net_closed_unit', 'sum')
            ).reset_index()
            consultant_live['close_rate'] = (
                consultant_live['closed'] / consultant_live['total'] * 100
            ).round(1)
        
            top_cons_row = consultant_live.sort_values('close_rate', ascending=False).iloc[0]
            top_consultant = top_cons_row['sales_consultant']
            top_consultant_rate = top_cons_row['close_rate']

            # Avg incentive intensity from filtered data
            avg_incentive = filtered['incentive_intensity_pct'].mean()
            avg_incentive = round(avg_incentive, 2) if not pd.isna(avg_incentive) else 0

            # Safe avg_days in case of NaN
            avg_days_safe = round(avg_days, 0) if not pd.isna(avg_days) else "N/A"

            # Prompt
            prompt = (
                f"You are a senior sales analyst reporting to the Director of Data "
                f"at Rhodes Enterprises, a Texas homebuilder. "
                f"Write exactly 4 bullet points for a Sales Director. "
                f"Each bullet must identify a specific risk or opportunity from the data "
                f"and recommend one concrete action for next quarter. "
                f"Do not restate numbers verbatim. Interpret what the patterns mean for the business. "
                f"Here is the current performance data: "
                f"{closed} units closed out of a target, generating ${(total_revenue if not pd.isna(total_revenue) else 0)/1_000_000:.1f}M revenue. "
                f"Cancellation rate is {cancellation_rate}%. "
                f"Average days to close is {avg_days_safe} days."
                f"Target attainment is {target_attainment}%. "
                f"Average incentive intensity is {avg_incentive}% — this measures margin given away to close deals. "
                f"{top_cancel_community} has the highest cancellation rate at {top_cancel_rate}%. "
                f"{best_channel} is the strongest lead channel with a {best_channel_rate}% close rate. "
                f"{worst_channel} has the highest cancellation rate among channels at {worst_channel_rate}%. "
                f"Top performing consultant is {top_consultant} with a {top_consultant_rate}% close rate. "
                f"Format each bullet starting with a bold label: Risk: or Opportunity: "
                f"Keep each bullet to 2-3 sentences maximum."
            )

            # Call Cortex COMPLETE
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', %s)",
                (prompt,)
            )
            result = cursor.fetchone()[0]

            # Show what data was used
            with st.expander("Data used to generate this summary"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"- **Closed Units:** {closed}")
                    st.markdown(f"- **Revenue:** ${total_revenue/1_000_000:.1f}M")
                    st.markdown(f"- **Cancellation Rate:** {cancellation_rate}%")
                    st.markdown(f"- **Avg Days to Close:** {avg_days_safe}")
                    st.markdown(f"- **Target Attainment:** {target_attainment}%")
                with col_b:
                    st.markdown(f"- **Avg Incentive Intensity:** {avg_incentive}%")
                    st.markdown(f"- **Highest Cancel Community:** {top_cancel_community} ({top_cancel_rate}%)")
                    st.markdown(f"- **Best Lead Channel:** {best_channel} ({best_channel_rate}%)")
                    st.markdown(f"- **Worst Lead Channel:** {worst_channel} ({worst_channel_rate}%)")
                    st.markdown(f"- **Top Consultant:** {top_consultant} ({top_consultant_rate}%)")

            st.info(result)

        except Exception as e:
            st.error(f"Could not generate summary. Error: {str(e)}")



# PART 2C - Natural Language Query Feature


st.divider()
st.subheader("Ask Your Data a Question!")
st.caption("Ask AI questions: Sales Data from Snowflake Cortex.")

if selected_region != "All" or selected_consultant != "All" or selected_community != "All" or selected_year != "All" or date_option != "All Time":
    active = []
    if selected_region != "All": active.append(f"Region: {selected_region}")
    if selected_year != "All": active.append(f"Year: {selected_year}")
    if selected_consultant != "All": active.append(f"Consultant: {selected_consultant}")
    if selected_community != "All": active.append(f"Community: {selected_community}")
    if date_option != "All Time": active.append(f"Period: {date_option}")
    st.warning(f"Answers are based on filtered data only — {', '.join(active)}. Change filters to All for full dataset answers.")

# Initialize chat history and add a pre fill 
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "prefill_question" not in st.session_state:
    st.session_state.prefill_question = None

# Build data context snapshot from the filtered dataframe
def build_data_context(filtered_df):
    total = len(filtered_df)
    closed_u = int(filtered_df['net_closed_unit'].sum())
    cancelled_u = int(filtered_df['cancelled_unit'].sum())
    rev = filtered_df[filtered_df['is_closed'] == True]['contract_price'].sum()
    cancel_r = round(cancelled_u / total * 100, 1) if total > 0 else 0
    days = filtered_df[filtered_df['is_closed'] == True]['days_to_close'].mean()
    days = round(days, 0) if not pd.isna(days) else 126

    comm = filtered_df.groupby('community').agg(
        total=('contract_id','count'), cancelled=('cancelled_unit','sum'),
        closed=('net_closed_unit','sum')
    ).reset_index()
    comm['cancel_rate'] = (comm['cancelled']/comm['total']*100).round(1)
    comm['close_rate'] = (comm['closed']/comm['total']*100).round(1)

    src = filtered_df.groupby('buyer_source').agg(
        total=('contract_id','count'), closed=('net_closed_unit','sum'),
        cancelled=('cancelled_unit','sum')
    ).reset_index()
    src['close_rate'] = (src['closed']/src['total']*100).round(1)
    src['cancel_rate'] = (src['cancelled']/src['total']*100).round(1)

    cons = filtered_df.groupby('sales_consultant').agg(
        total=('contract_id','count'), closed=('net_closed_unit','sum')
    ).reset_index()
    cons['close_rate'] = (cons['closed']/cons['total']*100).round(1)

    reg = filtered_df.groupby('region').agg(
        total=('contract_id','count'), closed=('net_closed_unit','sum'),
        target=('regional_unit_target','first')
    ).reset_index()

    context = f"""
You are a data engineer for Rhodes Enterprises, a Texas homebuilders group.
Answer as if briefing a Sales Director. Be concise, direct, use business language, not completely technical language.
Answer questions using only the data provided below. Be concise and direct and analytical.
If the data does not contain enough information to answer the question, say exactly:
"I don't have enough data to answer that. Try adjusting your filters or asking something else."
Never make up numbers. Never answer questions unrelated to this sales data.

Current Data Snapshot (reflects active dashboard from filters)

OVERALL METRICS:
- Total contracts: {total}
- Closed units: {closed_u}
- Cancelled units: {cancelled_u}
- Cancellation rate: {cancel_r}%
- Total revenue (from closed deals): ${rev/1_000_000:.1f}M
- Avg days to close: {days:.0f}

COMMUNITY PERFORMANCE:
{comm[['community','total','closed','cancel_rate','close_rate']].to_string(index=False)}

BUYER SOURCE PERFORMANCE:
{src[['buyer_source','total','close_rate','cancel_rate']].to_string(index=False)}

CONSULTANT PERFORMANCE:
{cons[['sales_consultant','total','closed','close_rate']].sort_values('close_rate', ascending=False).to_string(index=False)}

REGION SUMMARY:
{reg[['region','total','closed','target']].to_string(index=False)}

INCENTIVE INTENSITY BY COMMUNITY (measures margin given away to close deals: higher % = more discounting):
{filtered_df.groupby('community')['incentive_intensity_pct'].mean().round(2).reset_index().rename(columns={'incentive_intensity_pct':'avg_incentive_pct'}).sort_values('avg_incentive_pct', ascending=False).to_string(index=False)}

"""
    return context

def run_cortex_query(question, filtered_df):
    data_context = build_data_context(filtered_df)

    history_text = ""
    if len(st.session_state.chat_history) > 1:
        recent = st.session_state.chat_history[-5:-1]
        for h in recent:
            role = "User" if h["role"] == "user" else "Assistant"
            history_text += f"{role}: {h['content']}\n"

    full_prompt = (
        f"{data_context}\n"
        f"CONVERSATION HISTORY\n{history_text}\n"
        f"CURRENT QUESTION \n{question}\n\n"
        f"Answer in 2-4 sentences. Be specific. Use numbers from the data above."
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', %s)",
        (full_prompt,)
    )
    return cursor.fetchone()[0]



# add some suggested questions if user just wants to explore AI !
st.markdown("**Not sure where to start? Try one of these:**")
sq_col1, sq_col2, sq_col3  = st.columns(3)

suggested = [
    "Which community has the highest cancellation rate?",
    "Who is the top performing consultant and why?",
    "Which lead channel should we invest more in?"
]

with sq_col1:
    if st.button(suggested[0], use_container_width=True):
        st.session_state.prefill_question = suggested[0]
with sq_col2:
    if st.button(suggested[1], use_container_width=True):
        st.session_state.prefill_question = suggested[1]
with sq_col3 :
    if st.button(suggested[2], use_container_width=True):
        st.session_state.prefill_question = suggested[2]

# Any existing chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle prefilled question from suggested buttons
if st.session_state.prefill_question:
    question = st.session_state.prefill_question
    st.session_state.prefill_question = None

    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.chat_history.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = run_cortex_query(question, filtered)
                st.markdown(answer)
                st.caption("You can follow up for more : 'Why might that be?' or 'What should we do about it?' or 'Tell me more information about that consultant.'")
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Could not answer that question. Error: {str(e)}")

# Chat input for questions
col_input, col_btn = st.columns([5, 1])
with col_input:
    user_question = st.text_input(
        "Your question:",
        placeholder="e.g. Which region has the most cancellations?",
        label_visibility="collapsed"
    )
with col_btn:
    ask_clicked = st.button("Ask", use_container_width=True)

if ask_clicked and user_question:
    with st.chat_message("user"):
        st.markdown(user_question)
    st.session_state.chat_history.append({"role": "user", "content": user_question})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = run_cortex_query(user_question, filtered)
                st.markdown(answer)
                st.caption("You can follow up for more : 'Why might that be?' or 'What should we do about it?' or 'Tell me more information about that consultant.'")
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Could not answer that question. Error: {str(e)}")

# Clear chat
if st.session_state.chat_history:
    if st.button("Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()