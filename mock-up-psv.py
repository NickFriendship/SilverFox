import sys
import pyodbc
import config
import time
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import neurokit2 as nk
import shimmer
from shimmer import ShimmerDevice

# from sqlalchemy import create_engine

# Config of variables
fake_fallback = False

# Check if a COM port is provided as an argument
if len(sys.argv) > 1 and "COM" in sys.argv[1]:
    com_port = sys.argv[1]
else:
    com_port = "COM8"  # Default value if no input is provided


# Fetch player data from the database
def fetch_player_data(con):
    qry = "SELECT * FROM dbo.player"
    player_dt = pd.read_sql(qry, con)
    return player_dt


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


def fetch_recent_sensor_data(conn):
    query = """
    SELECT * FROM dbo.sensor_data
    WHERE datetime >= DATEADD(day, -7, GETDATE())
    """
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


def fetch_measurement_ranges(conn):
    # query = """
    # WITH StartGame AS (
    #     SELECT
    #         player_id,
    #         shimmer_id,
    #         datetime AS start_time,
    #         ROW_NUMBER() OVER (PARTITION BY player_id, shimmer_id ORDER BY datetime) AS row_num
    #     FROM dbo.measurement
    #     WHERE event = 'start_game'
    # ),
    # StopGame AS (
    #     SELECT
    #         player_id,
    #         shimmer_id,
    #         datetime AS end_time,
    #         ROW_NUMBER() OVER (PARTITION BY player_id, shimmer_id ORDER BY datetime) AS row_num
    #     FROM dbo.measurement
    #     WHERE event = 'stop_game'
    # ),
    # MeasurementPairs AS (
    #     SELECT
    #         sg.player_id,
    #         sg.shimmer_id,
    #         sg.start_time,
    #         st.end_time
    #     FROM StartGame sg
    #     INNER JOIN StopGame st ON sg.player_id = st.player_id AND sg.shimmer_id = st.shimmer_id AND sg.row_num = st.row_num
    #     WHERE sg.start_time < st.end_time
    # )
    # SELECT
    #     player_id,
    #     shimmer_id,
    #     start_time,
    #     end_time
    # FROM MeasurementPairs
    # ORDER BY start_time DESC;
    # """

    query = """
        WITH DataWithPreviousTime AS (
        SELECT *,
               LAG(datetime) OVER (ORDER BY datetime) AS PreviousTime
        FROM dbo.sensor_data
    ),
    DataWithStreamId AS (
        SELECT *,
               SUM(CASE WHEN DATEDIFF(SECOND, PreviousTime, datetime) > 1 THEN 1 ELSE 0 END) OVER (ORDER BY datetime) AS StreamId
        FROM DataWithPreviousTime
    ),
    StreamDetails AS (
        SELECT StreamId,
               MIN(datetime) AS start_time,
               MAX(datetime) AS end_time
        FROM DataWithStreamId
        GROUP BY StreamId
    )
    SELECT
        start_time,
        end_time
    FROM StreamDetails
    ORDER BY start_time DESC;
    """
    measurement_ranges = pd.read_sql(query, conn)
    return measurement_ranges


# Initialize or update session state
if "disabled" not in st.session_state:
    st.session_state.disabled = False

if "device" not in st.session_state:
    st.session_state.device = None

if "line_chart_data" not in st.session_state:
    st.session_state.line_chart_data = pd.DataFrame(columns=["datetime", "gsr", "ppg_raw"])

if "annotations_df" not in st.session_state:
    st.session_state.annotations_df = pd.DataFrame(columns=["datetime", "value", "y"])

# Wide page
st.set_page_config(layout="wide", page_title="PSV Stress Dashboard", page_icon="⚽")

# Title
# st.header('Dashboard Mindgames - PSV', divider='red')
st.markdown("<h1 style='text-align: center; margin-top: -30px;'>PSV Stress visualisation</h1>", unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["Live monitoring", "Historical data"])

# Create a connection to the database
conn = get_db_connection()

player_data = fetch_player_data(conn)
# Create a dictionary mapping player names to their IDs
player_dict = dict(zip(player_data['name'], player_data['id']))

with tab1:
    # Form to start monitoring
    with st.form('start_form'):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            game = st.selectbox('Game', ("Aristotle", "MoveSense", "Stack Tower"), index=None, key='game')
        with col2:
            selected_player_name = st.selectbox('Player', options=list(player_dict.keys()), index=None, key='player')
            submit_button = st.form_submit_button("Start", on_click=lambda: setattr(st.session_state, 'disabled', True),
                                                  disabled=st.session_state.disabled)

    if submit_button or st.session_state.disabled:
        if st.session_state.device is None:
            # Start streaming
            st.session_state.device = ShimmerDevice(com_port, fake_fallback)
            st.session_state.device.start_streaming()
            st.toast('Shimmer connected', icon="🎉")

        # Put the chosen game and player in the database
        st.session_state.selected_game = st.session_state.game
        st.session_state.selected_player = st.session_state.player
        st.session_state.selected_player_id = player_dict[st.session_state.player]

        query = f"""
         INSERT INTO measurement (player_id, shimmer_id, event, note)
         VALUES ({st.session_state.selected_player_id}, {st.session_state.device.id}, 'start_game', '{st.session_state.selected_game}')
         """
        conn.cursor().execute(query)
        conn.commit()

        # Ping form
        with st.form('ping_form', clear_on_submit=True):
            ping_text = st.text_area("Ping text")
            submit_ping = st.form_submit_button("Send ping")

        if submit_ping:
            new_annotation = pd.DataFrame({
                'datetime': [st.session_state.line_chart_data.iloc[-1]['datetime']],
                'value': [ping_text],
                'y': [st.session_state.line_chart_data.iloc[-1]['gsr']]
            })
            st.session_state.annotations_df = pd.concat([st.session_state.annotations_df, new_annotation],
                                                        ignore_index=True)
            st.toast('Ping sent', icon="🎉")

        colu1, colu2, colu3 = st.columns([1, 1, 0.2])
        with colu3:
            stop_button = st.button('Stop streaming', type="primary")

        placeholder = st.empty()
        # Continuous data generation loop
        while True:
            # Append livestreamed values to DataFrame
            live_data = st.session_state.device.get_live_data()

            st.session_state.line_chart_data = pd.concat(
                [st.session_state.line_chart_data, live_data]).drop_duplicates().reset_index(drop=True)

            # Keep only the last 80 datapoints, to create scrolling window effect
            st.session_state.line_chart_data = st.session_state.line_chart_data.tail(80)

            # Ensure annotations are in sync with the live data
            annotations_data_tail = st.session_state.annotations_df[
                st.session_state.annotations_df['datetime'] >= st.session_state.line_chart_data['datetime'].min()]

            # Build the GSR line chart
            gsr_chart = alt.Chart(st.session_state.line_chart_data).transform_fold(
                ["gsr"],
                as_=['Measurement', 'value']
            ).mark_line().encode(
                x=alt.X('datetime:T', axis=alt.Axis(title='Datetime')),
                y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                color='Measurement:N'
            ).interactive()

            # Update annotations to move with the data
            annotation_layer = (
                alt.Chart(annotations_data_tail)
                .mark_text(size=25, text="⬇️", dx=0, dy=0, align="center")
                .encode(x=alt.X("datetime:T", axis=None), y=alt.Y("y:Q"), tooltip=["value"])
            )
            # Show chart
            combined_chart_gsr = gsr_chart + annotation_layer

            # Build the GSR_raw line chart
            gsr_raw_chart = alt.Chart(st.session_state.line_chart_data).transform_fold(
                ["gsr_raw"],
                as_=['Measurement', 'value']
            ).mark_line().encode(
                x=alt.X('datetime:T', axis=alt.Axis(title='datetime')),
                y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                color='Measurement:N'
            ).interactive()

            # Build the PPG line chart
            ppg_chart = alt.Chart(st.session_state.line_chart_data).transform_fold(
                ["ppg_raw"],
                as_=['Measurement', 'value']
            ).mark_line().encode(
                x='datetime:T',
                y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                color='Measurement:N'
            ).interactive()

            with placeholder.container():
                st.altair_chart(combined_chart_gsr, theme=None, use_container_width=True)
                st.altair_chart(ppg_chart, theme=None, use_container_width=True)
                st.altair_chart(gsr_raw_chart, theme=None, use_container_width=True)
                time.sleep(1)

            if stop_button:
                st.session_state.device.stop_streaming()
                st.session_state.device = None
                st.toast('Shimmer disconnected', icon="🔌")
                query = f"""
                 INSERT INTO measurement (player_id, shimmer_id, event, note)
                 VALUES ({st.session_state.selected_player_id}, {st.session_state.device.id}, 'stop_game', '{st.session_state.selected_game}')
                 """
                conn.cursor().execute(query)
                conn.commit()
                break

with tab2:
    st.toast('Database connecting', icon="🔌")

    # Fetch data
    # sensor_data = fetch_sensor_data(conn)
    sensor_data = fetch_recent_sensor_data(conn)
    measurement_data = fetch_measurement_data(conn)
    shimmer_data = fetch_shimmer_data(conn)

    measurement_ranges = fetch_measurement_ranges(conn)
    # Convert start_time to string for display purposes
    measurement_ranges['start_time_str'] = measurement_ranges['start_time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Create box with filter
    with st.expander("Filter"):
        col1, col2, col3, col4, col5 = st.columns(5, gap="large")
        with col1:
            start_date = st.date_input("Start date", sensor_data['datetime'].min().date())
        with col2:
            end_date = st.date_input("End date", sensor_data['datetime'].max().date())
        with col3:
            st.selectbox('Training type', ("aristotle", "MoveSense"), index=None)
        with col4:
            selected_player = st.selectbox('Player', options=list(player_dict.keys()), index=None, key='hist_player')
        with col5:
            # Create a dropdown for selecting a measurement session

            # Default index for usable datastream
            target_start_time_str = "2024-07-03 15:07:51"

            # Find the index of the target start time in the measurement_ranges dataframe
            default_index = measurement_ranges.index[
                measurement_ranges['start_time_str'] == target_start_time_str].tolist()

            # If the target start time is found in the list, use its index, otherwise default to 0
            default_index_n = default_index[0] if default_index else 1

            selected_measurement_start = st.selectbox(
                'Measurement Session Start',
                options=measurement_ranges['start_time_str'],
                index=default_index_n,
                format_func=lambda x: x
            )

    selected_range = measurement_ranges[measurement_ranges['start_time_str'] == selected_measurement_start].iloc[0]

    # Filter data based on user input
    filtered_data = sensor_data.loc[
        (sensor_data['datetime'] >= selected_range['start_time']) &
        (sensor_data['datetime'] <= selected_range['end_time'])
        ]

    rate = 100

    # calculate the peaks from raw ppg
    peaks, info = nk.ppg_peaks(filtered_data['ppg_raw'], sampling_rate=rate)
    # Step 1: Check if `peaks` is empty
    if len(peaks) == 0:
        st.error("No peaks detected in the data. Please check the input data or adjust the peak detection parameters.")
    else:
        try:
            # Proceed with HRV calculations as before
            hrv_time = nk.hrv_time(peaks, sampling_rate=rate, show=True)

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

        except IndexError as e:
            st.error(f"An error occurred during HRV calculation: {e}")

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
