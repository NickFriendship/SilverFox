import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pyodbc
import config
import time
import shimmer
from shimmer import ShimmerDevice
from shimmer import convert_ADC_to_GSR  # Import the conversion function
import neurokit2 as nk

# Initialize or update session state
if "disabled" not in st.session_state:
    st.session_state.disabled = False

if "device" not in st.session_state:
    st.session_state.device = None

if "line_chart_data" not in st.session_state:
    st.session_state.line_chart_data = pd.DataFrame(columns=["timestamp", "gsr", "ppg_raw"])

if "annotations_df" not in st.session_state:
    st.session_state.annotations_df = pd.DataFrame(columns=["timestamp", "value", "y"])

# Wide page
st.set_page_config(layout="wide", page_title="PSV Mindgames Dashboard", page_icon="⚽")

# Title
st.header('Dashboard Mindgames - PSV', divider='red')

# Create tabs
tab1, tab2 = st.tabs(["Live monitoring", "Historical data"])

with tab1:
    
    # Form to start monitoring
    with st.form('start_form'):
        col1, col2, col3, col4 = st.columns(4, gap="large")
        with col1:
            st.selectbox('Game', ("Aristotle", "MoveSense"), index=None)
        with col2:
            st.selectbox('Player', ("Luuk de Jong", "Een andere speler van PSV"), index=None)
        submit_button = st.form_submit_button("Start", on_click=lambda: setattr(st.session_state, 'disabled', True), disabled=st.session_state.disabled)

    if submit_button or st.session_state.disabled:
        if st.session_state.device is None:
            # Start streaming
            st.session_state.device = ShimmerDevice('COM3')
            st.session_state.device.start_streaming()
            st.toast('Shimmer connected', icon="🎉")

        # Ping form
        with st.form('ping_form', clear_on_submit=True):
            ping_text = st.text_area("Ping text")
            submit_ping = st.form_submit_button("Send ping")

        if submit_ping:
            new_annotation = {
                'timestamp': st.session_state.line_chart_data.iloc[-1]['timestamp'], 
                'value': ping_text, 
                'y': st.session_state.line_chart_data.iloc[-1]['gsr']
            }
            st.session_state.annotations_df = st.session_state.annotations_df.append(new_annotation, ignore_index=True)
            st.toast('Ping sent', icon="🎉")
        
        colu1, colu2, colu3 = st.columns([1, 1, 0.2])
        with colu3:
            stop_button = st.button('Stop streaming', type="primary")

        placeholder = st.empty()
        # Continuous data generation loop
        for seconds in range(25):
            if seconds > 0:  # To prevent initial duplicate data generation             
                # Append livestreamed values to DataFrame
                live_data = st.session_state.device.get_live_data()
                                
                st.session_state.line_chart_data = pd.concat([st.session_state.line_chart_data, live_data]).drop_duplicates().reset_index(drop=True)
                
                # Keep only the last 40 datapoints
                st.session_state.line_chart_data = st.session_state.line_chart_data.tail(200)

                # Ensure annotations are in sync with the live data
                annotations_data_tail = st.session_state.annotations_df[st.session_state.annotations_df['timestamp'] >= st.session_state.line_chart_data['timestamp'].min()]

                # Build the GSR line chart
                gsr_chart = alt.Chart(st.session_state.line_chart_data).transform_fold(
                    ["gsr"],
                    as_=['Measurement', 'value']
                ).mark_line().encode(
                    x=alt.X('timestamp:T', axis=alt.Axis(title='Timestamp')),
                    y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                    color='Measurement:N'
                ).interactive()

                # Update annotations to move with the data
                annotation_layer = (
                    alt.Chart(annotations_data_tail)
                    .mark_text(size=25, text="⬇️", dx=0, dy=0, align="center")
                    .encode(x=alt.X("timestamp:T", axis=None), y=alt.Y("y:Q"), tooltip=["value"])
                )

                # Show chart
                combined_chart_gsr = gsr_chart + annotation_layer

                # Build the PPG line chart
                ppg_chart = alt.Chart(st.session_state.line_chart_data).transform_fold(
                    ["ppg_raw"],
                    as_=['Measurement', 'value']
                ).mark_line().encode(
                    x='timestamp:T',
                    y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                    color='Measurement:N'
                ).interactive()

                with placeholder.container():
                    st.altair_chart(combined_chart_gsr, theme=None, use_container_width=True)
                    st.altair_chart(ppg_chart, theme=None, use_container_width=True)
                    time.sleep(1)

            if stop_button or seconds == 24:
                st.session_state.device.stop_streaming()
                st.session_state.device = None
                st.toast('Shimmer disconnected', icon="🔌")
                break

with tab2:
    # Database connection function
    def get_db_connection():
        try:
            conn = pyodbc.connect(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={config.server_host};"
                f"DATABASE=PSV;"
                f"UID=team;"
                f"PWD={config.password}"
            )
            return conn
        except pyodbc.Error as e:
            st.error(f"Database connection failed: {e}")
            st.stop()

    # Fetch sensor data from the database
    def fetch_sensor_data(conn):
        query = "SELECT * FROM dbo.sensor_data"
        sensor_data = pd.read_sql(query, conn)
        sensor_data['gsr'] = sensor_data['gsr_raw'].apply(shimmer.convert_ADC_to_GSR)
        return sensor_data

    # Fetch measurement data from the database
    def fetch_measurement_data(conn):
        query = "SELECT * FROM dbo.measurement"
        measurement_data = pd.read_sql(query, conn)
        return measurement_data

    # Fetch shimmer data from the database
    def fetch_shimmer_data(conn):
        query = "SELECT * FROM dbo.shimmer"
        shimmer_data = pd.read_sql(query, conn)
        return shimmer_data

    # Main function to fetch and display data
    def main():
        # Create a connection to the database
        conn = get_db_connection()

    # Create a connection to the database
    conn = get_db_connection()

    # Fetch data
    sensor_data = fetch_sensor_data(conn)
    measurement_data = fetch_measurement_data(conn)
    shimmer_data = fetch_shimmer_data(conn)
    st.toast('Database connecting', icon="🔌")

    # Create box with filter
    with st.expander("Filter"):
        col1, col2, col3, col4 = st.columns(4, gap="large")
        with col1:
            start_date = st.date_input("Start date", sensor_data['datetime'].min().date())
        with col2:
            end_date = st.date_input("End date", sensor_data['datetime'].max().date())
        with col3:
            st.selectbox('Training type', ("aristotle", "MoveSense"), index=None)
        with col4:
            st.selectbox('Player', ("Luuk de Jong", "Een andere speler van PSV"), index=None)

    # Filter data based on user input
    filtered_data = sensor_data[
        (sensor_data['datetime'].dt.date >= start_date) & (sensor_data['datetime'].dt.date <= end_date)]

    # calculate the peaks from raw ppg
    peaks, info = nk.ppg_peaks(filtered_data['ppg_raw'], sampling_rate=100)
    hrv_time = nk.hrv_time(peaks, sampling_rate=100, show=True)

    # Calculate the heart rate
    rr_intervals_s = np.array(hrv_time['HRV_MeanNN']) / 1000.0
    average_rr_interval_s = np.mean(rr_intervals_s)
    heart_rate = 60 / average_rr_interval_s

    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4, gap="large")

    # Display average Heart rate in a box
    col1.metric("Average Heart rate", f"{heart_rate:.0f} bpm")

    # Display max HRV in a box
    max_hrv = hrv_time['HRV_MaxNN'].iloc[0]
    col2.metric("Max HRV", f"{max_hrv:.0f} ms")

    # Display minimum HRV in a box
    min_hrv = hrv_time['HRV_MinNN'].iloc[0]
    col3.metric("Min HRV", f"{min_hrv:.0f} ms")

    # Display average HRV in a box
    average_hrv = hrv_time['HRV_MeanNN'].iloc[0]
    col4.metric("Average HRV", f"{average_hrv:.0f} ms")

    # Create a selection interval for the date range slider
    date_range = alt.selection_interval(bind='scales', encodings=['x', 'y'])

    # Create an Altair line chart with the filtered data and add the selection
    alt_chart = alt.Chart(filtered_data).mark_line().encode(
        x='datetime:T',
        y='gsr:Q',
        tooltip=['datetime', 'gsr']
    ).add_selection(
        date_range
    ).properties(
        title='GSR (galvanic skin response)'
    )

    # Display the Altair chart
    st.altair_chart(alt_chart, use_container_width=True)