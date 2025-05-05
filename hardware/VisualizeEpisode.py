import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from pathlib import Path
import socket
from flask import send_from_directory

# Configuration
DATA_DIR = Path("dataset").resolve()
PORT = 8050  # Default Dash port

# Initialize Dash app
app = dash.Dash(__name__)


# Load dataset from all episodes
def load_episodes():
    episode_dirs = [d for d in DATA_DIR.glob("*") if d.is_dir()]

    dfs = []
    for episode in episode_dirs:
        csv_file = episode / "data.csv"
        if csv_file.exists():
            df = pd.read_csv(csv_file)
            df["episode"] = episode.name
            df["picam_path"] = df["picam_frame"].apply(
                lambda x: f"/dataset/{episode.name}/picam_frames/{x}"
            )
            df["webcam_path"] = df["webcam_frame"].apply(
                lambda x: f"/dataset/{episode.name}/webcam_frames/{x}"
            )
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


df = load_episodes()

# Create figure
fig = px.line(
    df,
    x="timestamp",
    y=["angle1", "angle2", "angle3"],
    labels={"value": "Angle (degrees)", "timestamp": "Time"},
    title="Robotic Arm Joint Angles",
    hover_data=["episode", "picam_frame", "webcam_frame"],
    color="episode",
)


# Serve dataset files
@app.server.route("/dataset/<path:subpath>")
def serve_dataset(subpath):
    return send_from_directory(DATA_DIR, subpath)


# App layout
app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Robotic Arm Visualization - Multi-Episode Analysis"),
                dcc.Dropdown(
                    id="episode-selector",
                    options=[
                        {"label": ep, "value": ep} for ep in df["episode"].unique()
                    ],
                    multi=True,
                    placeholder="Select episodes to display",
                ),
                html.Div(
                    [
                        dcc.Graph(
                            id="angle-plot",
                            figure=fig,
                            style={"width": "60vw", "height": "80vh"},
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3("PiCam View"),
                                        html.Img(
                                            id="picam-image",
                                            style={
                                                "width": "400px",
                                                "border": "2px solid #333",
                                            },
                                        ),
                                        html.Div(id="picam-info"),
                                    ],
                                    style={"margin-bottom": "20px"},
                                ),
                                html.Div(
                                    [
                                        html.H3("Webcam View"),
                                        html.Img(
                                            id="webcam-image",
                                            style={
                                                "width": "400px",
                                                "border": "2px solid #333",
                                            },
                                        ),
                                        html.Div(id="webcam-info"),
                                    ]
                                ),
                            ],
                            style={"width": "35vw", "padding": "20px"},
                        ),
                    ],
                    style={"display": "flex"},
                ),
            ]
        )
    ]
)


# Update image callback
@app.callback(
    [
        Output("picam-image", "src"),
        Output("webcam-image", "src"),
        Output("picam-info", "children"),
        Output("webcam-info", "children"),
    ],
    [Input("angle-plot", "hoverData")],
)
def update_images(hoverData):
    if hoverData is None:
        return [
            "/assets/placeholder.jpg",
            "/assets/placeholder.jpg",
            "Hover over the plot to see PiCam images",
            "Hover over the plot to see Webcam images",
        ]

    point_index = hoverData["points"][0]["pointIndex"]
    try:
        row = df.iloc[point_index]
        return [
            row["picam_path"],
            row["webcam_path"],
            f"Episode: {row['episode']}<br>Time: {row['timestamp']}",
            f"Episode: {row['episode']}<br>Time: {row['timestamp']}",
        ]
    except IndexError:
        return [
            "/assets/placeholder.jpg",
            "/assets/placeholder.jpg",
            "Invalid data point",
            "Invalid data point",
        ]


# Episode selector callback
@app.callback(Output("angle-plot", "figure"), [Input("episode-selector", "value")])
def update_plot(selected_episodes):
    if selected_episodes:
        filtered_df = df[df["episode"].isin(selected_episodes)]
    else:
        filtered_df = df

    return px.line(
        filtered_df,
        x="timestamp",
        y=["angle1", "angle2", "angle3"],
        labels={"value": "Angle (degrees)", "timestamp": "Time"},
        title="Robotic Arm Joint Angles",
        hover_data=["episode", "picam_frame", "webcam_frame"],
        color="episode",
    )


# Get network IP
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


if __name__ == "__main__":
    print(f"\n{'=' * 40}")
    print(f"Visualization available at:")
    print(f"Local: http://localhost:{PORT}")
    print(f"Network: http://{get_ip()}:{PORT}")
    print(f"{'=' * 40}\n")
    app.run(host="0.0.0.0", port=PORT)
