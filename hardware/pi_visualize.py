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

# Load dataset
csv_files = list(DATA_DIR.glob("*.csv"))
df = pd.concat([pd.read_csv(f) for f in csv_files])
df["image_path"] = df["video_frame"].apply(lambda x: f"/dataset/videos/{x}")

# Create figure
fig = px.line(
    df,
    x="timestamp",
    y=["angle1", "angle2"],
    labels={"value": "Angle (degrees)", "timestamp": "Time"},
    title="Robotic Arm Joint Angles",
)


# Serve images from dataset/videos
@app.server.route("/dataset/videos/<path:filename>")
def serve_image(filename):
    return send_from_directory(DATA_DIR / "videos", filename)


# App layout
app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Robotic Arm Visualization"),
                html.Div(
                    [
                        dcc.Graph(
                            id="angle-plot",
                            figure=fig,
                            style={"width": "60vw", "height": "80vh"},
                        ),
                        html.Div(
                            [
                                html.Img(
                                    id="current-image",
                                    style={
                                        "width": "400px",
                                        "border": "2px solid #333",
                                    },
                                ),
                                html.Div(id="image-info"),
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
    [Output("current-image", "src"), Output("image-info", "children")],
    [Input("angle-plot", "hoverData")],
)
def update_image(hoverData):
    if hoverData is None:
        return "/assets/placeholder.jpg", "Hover over the plot to see images"

    point_index = hoverData["points"][0]["pointIndex"]
    img_path = df.iloc[point_index]["image_path"]
    timestamp = df.iloc[point_index]["timestamp"]

    return img_path, f"Time: {timestamp}"


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
    app.run(host="0.0.0.0", port=PORT)  # Fixed line
