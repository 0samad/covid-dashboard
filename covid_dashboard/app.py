# app.py - Final Grouped Bar Chart Dashboard
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import numpy as np
from datetime import datetime, date

# --- 1. Data Loading and Preprocessing ---
try:
    data = pd.read_csv("covid-data.csv")
except FileNotFoundError:
    print("Error: 'covid-data.csv' not found. Please ensure the file is in the same directory.")
    exit()

data = data[['Country_Region', 'Last_Update', 'Confirmed', 'Deaths']].copy()
data = data.rename(columns={'Country_Region': 'Country', 'Last_Update': 'Date'})

# CRITICAL FIX: Standardize to Date (Day) and remove time components
data['Date'] = pd.to_datetime(data['Date'], utc=True, errors='coerce').dt.tz_localize(None).dt.date
data.dropna(subset=['Date'], inplace=True)

data = data.groupby(['Country', 'Date'], as_index=False).agg({
    'Confirmed': 'sum',
    'Deaths': 'sum'
})

# Feature Engineering
data['Recovered'] = np.clip((data['Confirmed'] - data['Deaths']) * 0.8, a_min=0, a_max=None).astype(int)
data['Active'] = data['Confirmed'] - data['Deaths'] - data['Recovered']


# --- 2. Initialize App and Set Theme ---
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "COVID-19 Tracker"
server = app.server

# Get min/max dates for picker (convert back to datetime for the DatePickerRange)
MIN_DATE = datetime.combine(data['Date'].min(), datetime.min.time())
MAX_DATE = datetime.combine(data['Date'].max(), datetime.min.time())


# --- 3. Layout ---
app.layout = dbc.Container([
    # Title Bar
    dbc.Row([
        dbc.Col(html.H1("🦠 Global COVID-19 Tracker", className="text-center text-primary my-4"), width=12)
    ]),

    # Filters Row
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Label("Select Country:", className="text-white"),
                dcc.Dropdown(
                    id='country-dropdown',
                    options=[{'label': c, 'value': c} for c in sorted(data['Country'].unique())],
                    value='Morocco',
                    clearable=False,
                    className="dbc"
                ),
            ], className="mb-4"),
            md=6
        ),
        dbc.Col(
            html.Div([
                html.Label("Select Date Range:", className="text-white"),
                dcc.DatePickerRange(
                    id='date-picker',
                    min_date_allowed=MIN_DATE,
                    max_date_allowed=MAX_DATE,
                    start_date=MIN_DATE,
                    end_date=MAX_DATE,
                    className="dbc-date-picker"
                ),
            ], className="mb-4"),
            md=6
        )
    ]),
    
    # KPI Cards Row
    dbc.Row(id='cards-row', className="mb-4 gx-3"),

    # Graph Row
    dbc.Row([
        dbc.Col(dcc.Graph(id='cases-graph', config={'displayModeBar': False}), md=12)
    ])
    
], fluid=True, className="bg-dark p-4")


# --- 4. Callback ---
@app.callback(
    [Output('cards-row', 'children'),
     Output('cases-graph', 'figure')],
    [Input('country-dropdown', 'value'),
     Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date')]
)
def update_dashboard(selected_country, start_date_str, end_date_str):
    # Convert date picker strings to date objects for filtering
    start_date = datetime.strptime(start_date_str.split('T')[0], '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str.split('T')[0], '%Y-%m-%d').date()
    
    # Filter Data
    filtered = data[(data['Country'] == selected_country) &
                    (data['Date'] >= start_date) &
                    (data['Date'] <= end_date)].sort_values('Date').copy()

    # KPI Calculation
    if filtered.empty:
        total_cases, total_deaths, total_recovered, active_cases = 0, 0, 0, 0
    else:
        total_cases = int(filtered['Confirmed'].max())
        total_deaths = int(filtered['Deaths'].max())
        total_recovered = int(filtered['Recovered'].max())
        active_cases = int(filtered.iloc[-1]['Active'])


    # Card Generation
    card_data = [
        ("Confirmed", total_cases, "warning", "fas fa-lungs-virus"),
        ("Active Cases", active_cases, "primary", "fas fa-users-slash"),
        ("Total Deaths", total_deaths, "danger", "fas fa-skull-crossbones"),
        ("Total Recovered", total_recovered, "success", "fas fa-heartbeat"),
    ]

    cards = [
        dbc.Col(dbc.Card([
            dbc.CardHeader(html.Div([html.I(className=f"{icon} me-2"), title], className="fw-bold")),
            dbc.CardBody(html.H3(f"{value:,}", className="card-title text-center")),
        ],
        color=color, inverse=True, outline=False, className="shadow-lg h-100"),
        md=3) for title, value, color, icon in card_data
    ]

    # --- Graph: Grouped Bar Chart Implementation ---
    fig = px.bar(
        filtered, 
        x='Date', 
        y=['Confirmed', 'Active', 'Deaths', 'Recovered'],
        labels={'value':'Case Count', 'Date':'Date', 'variable':'Category'},
        title=f"COVID-19 Trend Comparison in {selected_country}",
        
        # CRITICAL: Set barmode to 'group' for side-by-side bars
        barmode='group', 
        
        # Keep the categorical X-axis fix for stable plotting
        category_orders={'Date': filtered['Date'].astype(str).tolist()}, 
        
        color_discrete_map={
            'Confirmed': '#ffc107',
            'Active': '#0d6efd',
            'Deaths': '#dc3545',
            'Recovered': '#198754'
        }
    )

    # Template and Styling
    fig.update_layout(
        template='plotly_dark',
        title_font_size=24,
        title_x=0.5,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text='Category',
        
        # Explicitly set X-axis type to 'category'
        xaxis={'type': 'category'} 
    )
    
    # Bar chart specific styling
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#3a3a3a')

    return cards, fig

# --- 5. Run Application ---
if __name__ == '__main__':
    app.run(debug=True)