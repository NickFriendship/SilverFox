import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import time
from shimmer import ShimmerDevice

# Initialize or update session state
if "disabled" not in st.session_state:
    st.session_state.disabled = False

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

    # Annotations setup
    annotations = [(10, "Speler mist de bal"), (13, "Speler schrikt van onweer"), (19, "Speler moet niezen")]
    annotations_df = pd.DataFrame(annotations, columns=["index", "event"])
    annotations_df["y"] = 0

    if submit_button or st.session_state.disabled == True:

        # Start streaming
        device = ShimmerDevice('COM3')
        device.start_streaming()
        st.toast('Shimmer connected', icon="🎉")

        # Ping form
        with st.form('ping_form', clear_on_submit=True):
            ping_text = st.text_area("Ping text")
            submit_ping = st.form_submit_button("Send ping")

        if submit_ping:
            annotations_df = annotations_df.append({'index': len(st.session_state.line_chart_data) - 1, 'event': ping_text, 'y': 0}, ignore_index=True)
            st.toast('Ping sent', icon="🎉")
        
        colu1, colu2, colu3 = st.columns([1, 1, 0.2])
        with colu3:
            stop_button = st.button('Stop streaming', type="primary")

        placeholder = st.empty()
        # Continuous data generation loop
        for seconds in range(21):
            if seconds > 0:  # To prevent initial duplicate data generation             

                # Append livestreamed values to DataFrame
                live_data = device.get_live_data()
                live_data_tail = live_data.reset_index().tail(5)

                # Build the GSR line chart
                gsr_chart = alt.Chart(live_data).transform_fold(
                    ["gsr_raw"],
                    as_=['Measurement', 'value']
                ).mark_line().encode(
                    x='timestamp:T',
                    y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                    color='Measurement:N'
                ).interactive()

                # Build the PPG line chart
                ppg_chart = alt.Chart(live_data).transform_fold(
                    ["ppg_raw"],
                    as_=['Measurement', 'value']
                ).mark_line().encode(
                    x='timestamp:T',
                    y=alt.Y('value:Q', scale=alt.Scale(nice=True)),
                    color='Measurement:N'
                ).interactive()

                with placeholder.container():
                    st.altair_chart(gsr_chart, theme=None, use_container_width=True)
                    st.altair_chart(ppg_chart, theme=None, use_container_width=True)
                    time.sleep(1)
                
            if seconds == 20:
                    device.stop_streaming()