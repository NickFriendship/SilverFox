# Imports
import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import folium
from streamlit_folium import st_folium
import requests
import urllib.parse
import statistics
import openrouteservice
from openrouteservice import convert
import pyodbc

# Making tabs
tab1, tab2 = st.tabs(["Travel method", "New employee"])

# Creating min & max dates for calendar
today = date.today()
today_minus_80 = today - timedelta(weeks=4160)

# Establish a connection using SQL Server authentication
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Tab 1 - Input travelling days
with tab1:

    # Title
    st.header('Input travel method by day', divider = 'red')

    # Create dates of this week
    mon_date = today - datetime.timedelta(days=today.weekday())
    monday = 'Monday - ' + str(mon_date)
    tue_date = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=1)
    tuesday = 'Tuesday - ' + str(tue_date)
    wed_date = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=2)
    wednesday = 'Wednesday - ' + str(wed_date)
    thu_date = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=3)
    thursday = 'Thursday - ' + str(thu_date)
    fri_date = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=4)
    friday = 'Friday - ' + str(fri_date)

    # Create empty form
    empty_form_travel = st.empty()

    # Form
    with empty_form_travel.form('travel_form', clear_on_submit=True):

        # Add columns
        col1, col2 = st.columns(2, gap="large")

        with col1:
            # Show weeknumber
            week_num = today.isocalendar()[1]
            st.subheader('Week ' + str(week_num))

        with col2:
            # Load in employee data from database 
            sql_query = 'SELECT * FROM(SELECT DISTINCT(e.id), MAX(DATEPART(WEEK, GETDATE())) AS week_now, DATEPART(WEEK, date) AS week_no FROM employee_data e FULL JOIN travel_method_data t ON t.emp_id = e.id WHERE YEAR(date) = DATEPART(YEAR, GETDATE()) OR date IS NULL GROUP BY e.id, t.date)t WHERE week_now != week_no OR week_no IS NULL'
            df_emp_load = pd.read_sql(sql_query, conn)

            # Select ID
            # REMARKS: When loading in pd.DataFrame in selectbox it will select the first column, in this case the employee ID
            emp_id = st.selectbox(label='', options=df_emp_load, index=None, placeholder='Select your Employee ID', label_visibility="collapsed")
        
        # Input widgets 
        mon = st.radio(f'**{monday}**', ["Free", "Bike", "Train", "Bus", "Car", "Worked at home"], horizontal=True, index=None, captions=["❌", "🚲", "🚋", "🚌", "🚗", "🏠"])
        tue = st.radio(f'**{tuesday}**', ["Free", "Bike", "Train", "Bus", "Car", "Worked at home"], horizontal=True, index=None, captions=["❌", "🚲", "🚋", "🚌", "🚗", "🏠"])
        wed = st.radio(f'**{wednesday}**', ["Free", "Bike", "Train", "Bus", "Car", "Worked at home"], horizontal=True, index=None, captions=["❌", "🚲", "🚋", "🚌", "🚗", "🏠"])
        thu = st.radio(f'**{thursday}**', ["Free", "Bike", "Train", "Bus", "Car", "Worked at home"], horizontal=True, index=None, captions=["❌", "🚲", "🚋", "🚌", "🚗", "🏠"])
        fri = st.radio(f'**{friday}**', ["Free", "Bike", "Train", "Bus", "Car", "Worked at home"], horizontal=True, index=None, captions=["❌", "🚲", "🚋", "🚌", "🚗", "🏠"])

        # Every form must have a submit button
        submitted_travel = st.form_submit_button('Send to database')

    # Output
    if submitted_travel:
        empty_form_travel.empty()
        st.markdown(f'''
            **Summary:**
            - Monday: `{mon}`
            - Tuesday: `{tue}`
            - Wednesday: `{wed}`
            - Thursday: `{thu}`
            - Friday: `{fri}`
            ''')        

        # Insert data into the database
        data_to_insert = [(emp_id, mon_date, mon), (emp_id, tue_date, tue), (emp_id, wed_date, wed), (emp_id, thu_date, thu), (emp_id, fri_date, fri)]
        sql_query = "INSERT INTO travel_method_data (emp_id, date, travel_type) VALUES (?, ?, ?)"
        cursor.executemany(sql_query, data_to_insert)
        conn.commit()
        st.success('Data submitted successfully!', icon="🎉")

# Tab 2 - Commuting data for new employee
with tab2:
    
    # Title
    st.header('Commuting data for new employee', divider = 'red')

    with st.form('my_form', clear_on_submit=True):
        # Input widgets
        emp_id = st.number_input("Employee ID", placeholder="ID", value=None, step=1)
        name = st.text_input('Full name', placeholder="Name")
        sex = st.radio('What is your gender?', ['Male', 'Female', 'Other'], index=None)
        dob = st.date_input('What is your date of birth?', value=None, min_value=today_minus_80, max_value=today)
        street = st.text_input('Street name', placeholder="Street")
        streetno = st.text_input('Steet number', placeholder="Number") 
        city = st.text_input('City', placeholder="City")
        cons = st.slider('What is the consumption of your car in grams per kilometers (g/km)?', 50, 250, 50)
        with st.expander('More info about consumption'):
            st.write('You can find your consumption by visiting this website: https://www.anwb.nl/auto/tests-en-specificaties/zoeken/')

        # Every form must have a submit button
        submitted_emp = st.form_submit_button('Send to database')
    
        # Create session state for form button
        if 'submitted_emp_state' not in st.session_state:
            st.session_state.submitted_emp_state = False

        try:
            # Session state so that it only runs once
            if submitted_emp or st.session_state.submitted_emp_state:
                st.session_state.submitted_emp_state = True

                # Gathering coördinates with OpenStreetMap API
                address = street + '+' + streetno + '+' + city
                work_lat = 51.450876
                work_lon = 5.453602

                url = 'https://nominatim.openstreetmap.org/search?addressdetails=1&q=' + urllib.parse.quote(address) + '&format=jsonv2&limit=1'

                response = requests.get(url).json()
                home_lat = float(response[0]["lat"])
                home_lon = float(response[0]["lon"])

                # Calculating mean coördinates
                mean_lat = statistics.mean([home_lat, work_lat])
                mean_lon = statistics.mean([home_lon, work_lon])

                # Calculating min & max for optimal zoom
                data = {'Lat': [work_lat, home_lat], 'Lon': [work_lon, home_lon]}
                df = pd.DataFrame(data)

                sw_corner = df[['Lat', 'Lon']].min().values.tolist()
                ne_corner = df[['Lat', 'Lon']].max().values.tolist()

                # Creating map
                m = folium.Map(location=[mean_lat, mean_lon], zoom_start=12)
                m.fit_bounds([sw_corner, ne_corner]) 
                folium.Marker([home_lat, home_lon], tooltip="Home", icon=folium.Icon(color="green", icon="glyphicon glyphicon-home")).add_to(m)
                folium.Marker([work_lat, work_lon], tooltip="Work", icon=folium.Icon(color="purple", icon="glyphicon glyphicon-briefcase")).add_to(m)

                # Creating route with OpenRouteService API
                client = openrouteservice.Client(key='5b3ce3597851110001cf624800cde29c02534a258eb0d776169dee84')
                coords = ((home_lon, home_lat), (work_lon, work_lat))
                res = client.directions(coords)
                geometry = client.directions(coords)['routes'][0]['geometry']
                decoded = convert.decode_polyline(geometry)
                folium.GeoJson(decoded).add_to(m)

                # Calculate the distance + duration
                dtw = str(round(res['routes'][0]['summary']['distance']/1000,1))
                dur = str(round(res['routes'][0]['summary']['duration']/60,1))

                # Calculate the consumption per trip
                cons_trip = round(float(cons) * float(dtw), ndigits=2)

                # Making pop-up for map
                distance_txt = "<h5> Distance:&nbsp" + "<strong>"+dtw+" km </strong>" +"</h5></b>"
                duration_txt = "<h5> Duration:&nbsp" + "<strong>"+dur+" min. </strong>" +"</h5></b>"
                folium.GeoJson(decoded).add_child(folium.Popup(distance_txt+duration_txt,max_width=300)).add_to(m)

                st_data = st_folium(m, width=725)
                
                # Clean up data: multiply distance and duration by 2 (back and forth), make dob 'date' type
                dtw = float(dtw) * 2
                dur = float(dur) * 2
                dob = str(dob)

                # Output
                st.markdown(f'''
                    **Summary:**
                    - ID: `{emp_id}`
                    - Name: `{name}`
                    - Gender: `{sex}`
                    - Date of birth: `{dob}`
                    - Distance to work: `{dtw}` km (back and forth)
                    - Duration to work: `{dur}` min. (back and forth)
                    - CO2 consumption per trip: `{cons_trip}` g
                    ''')
                    
                # Insert data into the database
                data_to_insert = (emp_id, name, sex, dob, street, streetno, city, cons, dtw, dur)
                sql_query = "INSERT INTO employee_data (id, name, gender, date_of_birth, street, street_no, city, car_consumption, distance_to_work, duration_to_work) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                cursor.execute(sql_query, data_to_insert)
                conn.commit()
                st.success('Data submitted successfully!', icon="🎉")
        except (IndexError):
            ""
