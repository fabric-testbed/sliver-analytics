import dash

from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import requests
import pandas as pd
import plotly.express as px
import os


# Get API URL from environment variable
API_URL = os.getenv("API_URL", "http://localhost:5000")


# Function to format datetime to UTC ISO
def to_iso_format(datetime_value):
    if datetime_value:
        return f"{datetime_value}:00Z"  # Ensuring seconds and UTC format
    return None


# Function to fetch users
def fetch_users():
    try:
        response = requests.get(f"{API_URL}/users")
        return response.json() if response.status_code == 200 else []
    except requests.RequestException as e:
        print(f"Error fetching users: {e}")
        return []


# Function to fetch projects
def fetch_projects():
    try:
        response = requests.get(f"{API_URL}/projects")
        return response.json() if response.status_code == 200 else []
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        return []


# Function to fetch all slices for a user, project, or time range
def fetch_slices(user_uuid=None, project_uuid=None, start_time=None, end_time=None):
    params = {"per_page": 100, "page": 1}  # Start with page 1
    all_slices = []

    if user_uuid:
        params["user_uuid"] = user_uuid
    if project_uuid:
        params["project_uuid"] = project_uuid
    if start_time and end_time:
        params["start_time"] = start_time
        params["end_time"] = end_time

    try:
        while True:
            response = requests.get(f"{API_URL}/slices", params=params)
            if response.status_code != 200:
                print(f"Error fetching slices: {response.status_code} - {response.text}")
                break  # Exit loop if request fails

            slices = response.json().get("slices", [])
            if not slices:
                break  # Stop if no more slices are returned

            all_slices.extend(slices)
            params["page"] += 1  # Move to the next page

        return all_slices

    except requests.RequestException as e:
        print(f"Error fetching slices: {e}")
        return []


# Function to fetch resource usage for a user, project, or time range
def fetch_resource_usage(component_type, user_uuid=None, project_uuid=None, start_time=None, end_time=None):
    params = {"component_type": component_type}

    if user_uuid:
        params["user_uuid"] = user_uuid
    if project_uuid:
        params["project_uuid"] = project_uuid
    if start_time and end_time:
        params["start_time"] = start_time
        params["end_time"] = end_time

    try:
        response = requests.get(f"{API_URL}/resource_usage", params=params)
        return response.json() if response.status_code == 200 else {}
    except requests.RequestException as e:
        print(f"Error fetching resource usage: {e}")
        return {}


# Load users and projects
users = fetch_users()
projects = fetch_projects()

# Create Dash app with Bootstrap styling
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Updated layout using DBC
app.layout = dbc.Container([
    html.H1("Resource & Allocation Dashboard", className="text-center mb-4"),

    dcc.Tabs([
        # Tab 1: Slices Based on Time Range
        dcc.Tab(label="Slices Per Site (Time Range)", children=[
            dbc.Row([
                dbc.Col(html.Label("Select User:"), width=3),
                dbc.Col(dcc.Dropdown(
                    id="user-dropdown-slices",
                    options=[{"label": user["user_email"], "value": user["user_uuid"]} for user in users],
                    placeholder="Select a user...",
                ), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("Select Project:"), width=3),
                dbc.Col(dcc.Dropdown(
                    id="project-dropdown-slices",
                    options=[{"label": project["project_name"], "value": project["project_uuid"]} for project in projects],
                    placeholder="Select a project...",
                ), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("Start DateTime (UTC):"), width=3),
                dbc.Col(dbc.Input(id="start-datetime-slices", type="datetime-local"), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("End DateTime (UTC):"), width=3),
                dbc.Col(dbc.Input(id="end-datetime-slices", type="datetime-local"), width=9),
            ], className="mb-2"),

            dcc.Graph(id="slices-chart"),
        ]),

        # Tab 2: Resource Usage
        dcc.Tab(label="Resource Usage", children=[
            dbc.Row([
                dbc.Col(html.Label("Select Component Type:"), width=3),
                dbc.Col(dcc.Dropdown(
                    id="resource-dropdown",
                    options=[{"label": c, "value": c} for c in ["SharedNIC", "SmartNIC", "FPGA", "GPU", "NVME", "Storage"]],
                    placeholder="Select a component"
                ), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("Select User:"), width=3),
                dbc.Col(dcc.Dropdown(
                    id="user-dropdown-resource",
                    options=[{"label": user["user_email"], "value": user["user_uuid"]} for user in users],
                    placeholder="Select a user...",
                ), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("Select Project:"), width=3),
                dbc.Col(dcc.Dropdown(
                    id="project-dropdown-resource",
                    options=[{"label": project["project_name"], "value": project["project_uuid"]} for project in projects],
                    placeholder="Select a project...",
                ), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("Start DateTime (UTC):"), width=3),
                dbc.Col(dbc.Input(id="start-datetime-resource", type="datetime-local"), width=9),
            ], className="mb-2"),

            dbc.Row([
                dbc.Col(html.Label("End DateTime (UTC):"), width=3),
                dbc.Col(dbc.Input(id="end-datetime-resource", type="datetime-local"), width=9),
            ], className="mb-2"),

            html.Div(id="resource-output")
        ]),
    ])
], fluid=True)


# === CALLBACKS ===

@app.callback(
    Output("slices-chart", "figure"),
    [
        Input("user-dropdown-slices", "value"),
        Input("project-dropdown-slices", "value"),
        Input("start-datetime-slices", "value"),
        Input("end-datetime-slices", "value"),
    ]
)
def update_slices_chart(selected_user, selected_project, start_datetime, end_datetime):
    start_time = to_iso_format(start_datetime) if start_datetime else None
    end_time = to_iso_format(end_datetime) if end_datetime else None

    slices = fetch_slices(user_uuid=selected_user, project_uuid=selected_project, start_time=start_time,
                          end_time=end_time)
    df = pd.DataFrame(slices)

    if df.empty or "site_name" not in df:
        return px.bar(title="No Data Available")

    site_counts = df["site_name"].value_counts().reset_index()
    site_counts.columns = ["Site", "Slices Count"]

    return px.bar(
        site_counts,
        x="Site",
        y="Slices Count",
        title="Slices Per Site (Time Range)",
        color="Site"
    )


@app.callback(
    Output("resource-output", "children"),
    [
        Input("resource-dropdown", "value"),
        Input("user-dropdown-resource", "value"),
        Input("project-dropdown-resource", "value"),
        Input("start-datetime-resource", "value"),
        Input("end-datetime-resource", "value"),
    ]
)
def update_resource(component_type, selected_user, selected_project, start_datetime, end_datetime):
    start_time = to_iso_format(start_datetime) if start_datetime else None
    end_time = to_iso_format(end_datetime) if end_datetime else None

    data = fetch_resource_usage(component_type=component_type, user_uuid=selected_user, project_uuid=selected_project,
                                start_time=start_time, end_time=end_time)

    if not data or not isinstance(data, list):
        return "No data found"

    response_str = "\n".join(
        [f"User: {entry['user_email']}/{entry['user_uuid']} | Project: {entry['project_name']}/{entry['project_uuid']} | Count: {entry['count']}" for entry in data]
    )

    return html.Pre(response_str)


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
