import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import time
from shimmer import ShimmerDevice
import pyodbc
import config

# Wide page
st.set_page_config(layout="wide", page_title="PSV Mindgames Dashboard", page_icon="⚽")

# Title
st.header('Dashboard Mindgames - PSV', divider='red')

# Create tabs
tab1, = st.tabs(["Live monitoring"])

# Database connection function
def get_db_connection():
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={config.server_host};"
        f"DATABASE=PSV;"
        f"UID=team;"
        f"PWD={config.password}"
    )
    return conn

# Fetch sensor data from the database
def fetch_sensor_data(conn):
    query = "SELECT * FROM dbo.sensor_data"
    data = pd.read_sql(query, conn)
    return data

with tab1:
    # Initialize or update session state
    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    if "line_chart_data" not in st.session_state:
        # Initialize line chart data
        st.session_state.line_chart_data = pd.DataFrame(columns=["timestamp", "GSR", "HRV"])

    # Form to start monitoring
    with st.form('start_form'):
        col1, col2, col3, col4 = st.columns(4, gap="large")
        with col1:
            st.selectbox('Game', ("Aristotle", "MoveSense"), index=None)
        with col2:
            st.selectbox('Player', ("Luuk de Jong", "Een andere speler van PSV"), index=None)
        submit_button = st.form_submit_button("Start", on_click=lambda: setattr(st.session_state, 'disabled', True),
                                              disabled=st.session_state.disabled)

    # Annotations setup
    annotations = [(10, "Speler mist de bal"), (13, "Speler schrikt van onweer"), (19, "Speler moet niezen")]
    annotations_df = pd.DataFrame(annotations, columns=["timestamp", "event"])
    annotations_df["y"] = 0

    if submit_button or st.session_state.disabled:

        # Start streaming
        device = ShimmerDevice('COM3')
        device.start_streaming()
        st.toast('Shimmer connected', icon="🎉")

        # Ping form
        with st.form('ping_form', clear_on_submit=True):
            ping_text = st.text_area("Ping text")
            submit_ping = st.form_submit_button("Send ping")

        if submit_ping:
            annotations_df = annotations_df.append(
                {'timestamp': st.session_state.line_chart_data["timestamp"].iloc[-1], 'event': ping_text, 'y': 0},
                ignore_index=True)
            st.toast('Ping sent', icon="🎉")

        colu1, colu2, colu3 = st.columns([1, 1, 0.2])
        with colu3:
            stop_button = st.button('Stop streaming', type="primary")

        placeholder = st.empty()
        # Continuous data generation loop
        for seconds in range(21):  # Limited to 20 seconds
            if seconds > 0:  # To prevent initial duplicate data generation
                # Append livestreamed values to DataFrame
                live_data = device.get_live_data()

                # Debug: Print live_data structure
                st.write("Live Data:", live_data)

                # Convert live_data to DataFrame if it is a list of dictionaries
                if isinstance(live_data, list):
                    new_data = pd.DataFrame(live_data)
                    if not new_data.empty and all(col in new_data.columns for col in ["timestamp", "gsr_raw", "ppg_raw"]):
                        new_data.rename(columns={"gsr_raw": "GSR", "ppg_raw": "HRV"}, inplace=True)
                        st.session_state.line_chart_data = pd.concat(
                            [st.session_state.line_chart_data, new_data], ignore_index=True)
                    else:
                        st.error("Unexpected data columns in live_data. Please check the data structure.")
                else:
                    st.error("Unexpected data format from device. Please check the data structure.")
                    break

            # Select the last 20 rows for both line chart data and annotations
            line_chart_data_tail = st.session_state.line_chart_data.tail(20)
            annotations_df_tail = annotations_df[annotations_df['timestamp'] >= line_chart_data_tail['timestamp'].min()]

            # Update the GSR line chart
            gsr_chart = alt.Chart(line_chart_data_tail).mark_line().encode(
                x='timestamp:T',
                y=alt.Y('GSR:Q', title='GSR'),
                color=alt.value('blue')
            ).interactive()

            # Update the HRV line chart
            hrv_chart = alt.Chart(line_chart_data_tail).mark_line().encode(
                x='timestamp:T',
                y=alt.Y('HRV:Q', title='HRV'),
                color=alt.value('red')
            ).interactive()

            # Update annotations to move with the data
            annotation_layer = (
                alt.Chart(annotations_df_tail)
                .mark_text(size=12, text="⬇️", dx=0, dy=-10, align="center")
                .encode(x="timestamp:T", y=alt.Y("y:Q"), tooltip=["event"])
            )

            # Show charts
            with placeholder.container():
                st.altair_chart(gsr_chart + annotation_layer, theme=None, use_container_width=True)
                st.altair_chart(hrv_chart + annotation_layer, theme=None, use_container_width=True)
                time.sleep(1)

            if stop_button or seconds == 20:  # Stop streaming after 20 seconds
                device.stop_streaming()
                break