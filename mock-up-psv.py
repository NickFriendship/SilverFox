import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import time
from shimmer import ShimmerDevice
from shimmer import convert_ADC_to_GSR  # Import the conversion function

# Initialize or update session state
if "disabled" not in st.session_state:
    st.session_state.disabled = False

if "device" not in st.session_state:
    st.session_state.device = None

if "line_chart_data" not in st.session_state:
    st.session_state.line_chart_data = pd.DataFrame(columns=["timestamp", "gsr_raw", "ppg_raw"])

if "annotations_df" not in st.session_state:
    st.session_state.annotations_df = pd.DataFrame(columns=["timestamp", "value", "y"])

# Wide page
st.set_page_config(layout="wide", page_title="PSV Mindgames Dashboard", page_icon="⚽")

# Title
st.header('Dashboard Mindgames - PSV', divider='red')

# Create tabs
tab1, tab2, tab3 = st.tabs(["Live monitoring", "Historical HRV", "Historical GSR"])

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
                'y': st.session_state.line_chart_data.iloc[-1]['gsr_raw']
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
                
                # Convert GSR raw values to integers
                live_data['gsr_raw'] = live_data['gsr_raw'].astype(int)
                
                # Apply GSR conversion to the raw GSR values
                #live_data['gsr_raw'] = live_data['gsr_raw'].apply(convert_ADC_to_GSR)
                
                st.session_state.line_chart_data = pd.concat([st.session_state.line_chart_data, live_data]).drop_duplicates().reset_index(drop=True)
                
                # Keep only the last 40 datapoints
                st.session_state.line_chart_data = st.session_state.line_chart_data.tail(100)

                # Ensure annotations are in sync with the live data
                annotations_data_tail = st.session_state.annotations_df[st.session_state.annotations_df['timestamp'] >= st.session_state.line_chart_data['timestamp'].min()]

                # Build the GSR line chart
                gsr_chart = alt.Chart(st.session_state.line_chart_data).transform_fold(
                    ["gsr_raw"],
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
