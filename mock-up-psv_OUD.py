import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import time

# Wide page
st.set_page_config(layout="wide", page_title="PSV Mindgames Dashboard", page_icon="⚽")

# Title
st.header('Dashboard Mindgames - PSV', divider='red')

# Create tabs
tab1, tab2, tab3 = st.tabs(["Live monitoring", "Historical HRV", "Historical GSR"])

with tab1:
    # Initialize or update session state
    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    if "line_chart_data" not in st.session_state:
        # Initialize line chart data
        st.session_state.line_chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["HRV", "PPM", "Skin Conductance"])

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

        # Ping form
        with st.form('ping_form', clear_on_submit=True):
            ping_text = st.text_area("Ping text")
            submit_ping = st.form_submit_button("Send ping")

        if submit_ping:
            st.session_state.line_chart_data.loc[len(st.session_state.line_chart_data)] = np.random.randn(3)
            annotations_df = annotations_df.append({'index': len(st.session_state.line_chart_data) - 1, 'event': ping_text, 'y': 0}, ignore_index=True)
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
                st.session_state.line_chart_data = pd.concat([st.session_state.line_chart_data, line_chart_data_more], ignore_index=True)

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