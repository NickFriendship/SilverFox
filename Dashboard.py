import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
import numpy as np
import altair as alt
import time
import config

# Wide page
st.set_page_config(layout="wide", page_title="PSV Mindgames Dashboard", page_icon="⚽")


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
        st.write("Database connection successful")
        return conn
    except pyodbc.Error as e:
        st.error(f"Database connection failed: {e}")
        st.stop()


# Fetch sensor data from the database
def fetch_sensor_data(conn):
    query = "SELECT * FROM dbo.sensor_data"
    sensor_data = pd.read_sql(query, conn)
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


def fetch_PSV_DATA(conn):
    query = "SELECT * FROM dbo.PSV_DATA"
    PSV_DATA = pd.read_sql(query, conn)
    return PSV_DATA


# Main function to fetch and display data
def main():
    # Create a connection to the database
    conn = get_db_connection()


# Title
st.header('Dashboard Mindgames - PSV')

# Create tabs
tab1, tab2 = st.tabs(["Live monitoring", "Historical data"])

with tab1:
    # Initialize or update session state
    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    if "line_chart_data" not in st.session_state:
        # Initialize line chart data
        st.session_state.line_chart_data = pd.DataFrame(np.random.randn(20, 3),
                                                        columns=["HRV", "PPM", "Skin Conductance"])

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
    annotations_df = pd.DataFrame(annotations, columns=["index", "event"])
    annotations_df["y"] = 0

    if submit_button or st.session_state.disabled == True:
        st.write("Monitoring started")

        # Ping form
        with st.form('ping_form', clear_on_submit=True):
            ping_text = st.text_area("Ping text")
            submit_ping = st.form_submit_button("Send ping")

        if submit_ping:
            st.session_state.line_chart_data.loc[len(st.session_state.line_chart_data)] = np.random.randn(3)
            annotations_df = annotations_df.append(
                {'index': len(st.session_state.line_chart_data) - 1, 'event': ping_text, 'y': 0}, ignore_index=True)
            st.toast('Ping sent', icon="🎉")

        colu1, colu2, colu3 = st.columns([1, 1, 0.2])
        with colu3:
            stop_button = st.button('Stop streaming', type="primary")
            if stop_button:
                st.stop()

        placeholder = st.empty()
        # Continuous data generation loop
        for seconds in range(200):
            if seconds > 0:  # To prevent initial duplicate data generation
                # Generating random data for each second
                line_chart_data_more = pd.DataFrame(np.random.randn(1, 3), columns=["HRV", "PPM", "Skin Conductance"])
                # Append new data to existing DataFrame
                st.session_state.line_chart_data = pd.concat([st.session_state.line_chart_data, line_chart_data_more],
                                                             ignore_index=True)

            # Select the last 20 rows for both line chart data and annotations
            line_chart_data_tail = st.session_state.line_chart_data.reset_index().tail(20)
            annotations_df_tail = annotations_df[annotations_df['index'] >= line_chart_data_tail['index'].min()]

            # Update the line chart
            base_line_chart = alt.Chart(line_chart_data_tail).transform_fold(
                ["HRV", "PPM", "Skin Conductance"],
                as_=['Measurement', 'value']
            ).mark_line().encode(
                x='index:Q',
                y='value:Q',
                color='Measurement:N'
            ).interactive()

            # Update annotations to move with the data
            annotation_layer = (
                alt.Chart(annotations_df_tail)
                .mark_text(size=25, text="⬇️", dx=0, dy=100, align="center")
                .encode(x="index:Q", y=alt.Y("y:Q"), tooltip=["event"])
            )

            # Show chart
            combined_chart = base_line_chart + annotation_layer

            with placeholder.container():
                st.altair_chart(combined_chart, theme=None, use_container_width=True)
                time.sleep(1)

with tab2:
    # Create a connection to the database
    conn = get_db_connection()

    # Fetch data
    data = fetch_sensor_data(conn)

    # Check if data is fetched
    if data.empty:
        st.warning("No data available")
    else:
        data['datetime'] = pd.to_datetime(data['datetime'])

    # Create box with filter
    with st.expander("Filter"):
        col1, col2, col3, col4 = st.columns(4, gap="large")
        with col1:
            start_date = st.date_input("Start date", data['datetime'].min().date())
        with col2:
            end_date = st.date_input("End date", data['datetime'].max().date())
        with col3:
            st.selectbox('Training type', ("aristotle", "MoveSense"), index=None)
        with col4:
            st.selectbox('Player', ("Luuk de Jong", "Een andere speler van PSV"), index=None)

    # Filter data based on user input
    filtered_data = data[(data['datetime'].dt.date >= start_date) & (data['datetime'].dt.date <= end_date)]

    # Check if filtered data is empy
    if filtered_data.empty:
        st.warning("No data available for the selected data range")
    else:
        # Create columns for metrics
        col1, col2, col3, col4, col5 = st.columns(5, gap="large")

    # Display average Heart rate in a box
    average_gsr = filtered_data['gsr_raw'].mean()
    col1.metric("Average Heart rate", f"{average_gsr:.0f} ms")

    # Display max HRV in a box
    max_hrv = filtered_data['gsr_raw'].max()
    col2.metric("Max HRV", f"{max_hrv:.0f} ms")

    # Display minimum HRV in a box
    min_hrv = filtered_data['gsr_raw'].min()
    col3.metric("Min HRV", f"{min_hrv:.0f} ms")

    # Display average HRV in a box
    average_hrv = filtered_data['gsr_raw'].mean()
    col4.metric("Average HRV", f"{average_hrv:.0f} ms")

    # Display Peaks per minute in a box
    ppm = filtered_data['ppg_raw'].mean()
    col5.metric("Peaks per minute", f"{ppm:.0f} ppm")

    # Create a Plotly line chart with a date range slider
    fig = px.line(filtered_data, x='datetime', y='gsr_raw', title='GSR (galvanic skin response)')

    fig.update_xaxes(rangeslider_visible=True)

    # Display the Plotly figure
    st.plotly_chart(fig)

    # Fetch data from the tables
    sensor_data = fetch_sensor_data(conn)
    measurement_data = fetch_measurement_data(conn)
    shimmer_data = fetch_shimmer_data(conn)

    # Merge the tables to create a complete dataset
    merged_data = pd.merge(sensor_data, shimmer_data, left_on="shimmer_id", right_on="id")
    merged_data = pd.merge(merged_data, measurement_data, left_on="shimmer_id", right_on="shimmer_id")

    # Calculate the average GSR per event
    average_gsr_per_event = merged_data.groupby('event')['gsr_raw'].mean().reset_index()

    # Display the results
    st.header('Average GSR per Event')
    st.dataframe(average_gsr_per_event)

if __name__ == "__main__":
    main()

    # Create a connection to the database
    conn = get_db_connection()

    # Fetch data
    PSV_DATA = fetch_PSV_DATA(conn)

    # Calculate average RRMSSD per player
    average_rrmssd_per_player = PSV_DATA.groupby('PlayerID')['RMSSD'].mean().reset_index()

    # Create a bar chart for average RRMSSD per player
    fig = px.bar(average_rrmssd_per_player, x='PlayerID', y='RMSSD', title='Average HRV per Player')

    # Display the bar chart in Streamlit
    st.plotly_chart(fig)
