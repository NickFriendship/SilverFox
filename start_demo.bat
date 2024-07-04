set /p COMPORT=Enter the COM port:
.venv\Scripts\python.exe -m streamlit run mock-up-psv.py -- %COMPORT%

