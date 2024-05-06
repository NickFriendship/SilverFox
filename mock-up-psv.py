# Imports
import streamlit as st
import pandas as pd
import numpy as np
import time

# Wide page
st.set_page_config(layout="wide", page_title="PSV Mindgames Dashboard", page_icon="⚽")

# Title
st.header('MOCK-UP Dashboard - PSV', divider = 'red')

# Disable the submit button after it is clicked
def disable():
    st.session_state.disabled = True

# Initialize disabled for form_submit_button to False
if "disabled" not in st.session_state:
    st.session_state.disabled = False

# Create input fields
with st.form('start_form'):
    
    # Add columns
    col1, col2, col3, col4 = st.columns(4, gap="large")

    with col1:
        st.selectbox('Game', ("Aristotle", "MoveSense"), index=None)

    with col2:
        st.selectbox('Player', ("Luuk de Jong", "Een andere speler van PSV"), index=None)

    submit_button = st.form_submit_button("Start", on_click=disable, disabled=st.session_state.disabled)

# Create empty placeholder
placeholder = st.empty()    

if submit_button:
    line_chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["HRV", "PPM", "Skin Conductance"])
    st.toast('Shimmer connected', icon="🎉")

    for seconds in range(200):

        # Generating random data for each second
        line_chart_data_more = pd.DataFrame(np.random.randn(1, 3), columns=["HRV", "PPM", "Skin Conductance"])
        
        # Append new data to existing DataFrame
        line_chart_data = line_chart_data.append(line_chart_data_more, ignore_index=True) 

        with placeholder.container():
            st.line_chart(line_chart_data)
            time.sleep(1)