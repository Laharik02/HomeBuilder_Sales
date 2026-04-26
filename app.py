import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

from datetime import date
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
if date_option in ["2024 Only", "H2 2024 (Jul-Oct, partial)", "H1 2024 (Jan-Jun)"] or selected_year == 2024:
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

    # Add a dashed straight-line target for each region

    for region in closed_df['region'].unique():
        target = filtered[filtered['region'] == region]['regional_unit_target'].iloc[0]
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

#####

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