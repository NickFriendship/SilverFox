import time
import threading

import pyodbc
import pandas as pd
import re
from serial import Serial
from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType
import config


def connect_db():
    cnxn = pyodbc.connect(
        driver="{ODBC Driver 17 for SQL Server}", server=config.server_host, database="PSV",
        uid="team", pwd=config.password)
    cursor = cnxn.cursor()
    return cnxn, cursor


class ShimmerDevice:

    def __init__(self, com_port, fake_fallback: bool = False):
        self.live_data = pd.DataFrame(columns=['timestamp', 'gsr_raw', 'ppg_raw'])
        self.com_port = com_port
        try:
            self.serial = Serial(com_port, DEFAULT_BAUDRATE)
            self.shim_dev = ShimmerBluetooth(self.serial)
        except Exception as e:
            print(f"Failed to initialize Serial object with com_port: {com_port}. Error: {e}")
            error_code = re.search(r'None, (\d+)\)', str(e))
            if fake_fallback and error_code and error_code.group(1) == '121':
                self.shim_dev = FakeShimmerBluetooth()
            else:
                raise e
        self.shim_dev.initialize()

        self.batt = self.shim_dev.get_battery_state(True)
        self.dev_name = self.shim_dev.get_device_name()
        print(f'My name is: {self.dev_name} and my battery is at {self.batt}%')

        self.shim_dev.add_stream_callback(self.handler)

        self.cnxn, self.cursor = connect_db()

        # Updating the shimmer info in the database
        self.cursor.execute("""MERGE INTO dbo.shimmer AS target
USING (SELECT ?, ?, ?) AS source (name, port, battery_perc)
ON (target.name = source.name)
WHEN MATCHED THEN
    UPDATE SET target.port = source.port, target.battery_perc = source.battery_perc
WHEN NOT MATCHED THEN
    INSERT (name, port, battery_perc)
    VALUES (source.name, source.port, source.battery_perc)
OUTPUT INSERTED.id;
            """,
                            self.dev_name, self.com_port, self.batt)
        self.id = self.cursor.fetchone()[0]

        self.cnxn.commit()

    def handler(self, pkt: DataPacket):
        timestamp = pkt[EChannelType.TIMESTAMP]
        gsr_raw = pkt[EChannelType.GSR_RAW]
        ppg_raw = pkt[EChannelType.INTERNAL_ADC_13]
        # print(pkt.channels)
        # print(f'Received new data point at {timestamp}: GSR {gsr_raw}, PPG {ppg_raw}')

        new_row = pd.DataFrame({'timestamp': [timestamp], 'gsr_raw': [gsr_raw], 'ppg_raw': [ppg_raw],
                                'gsr': [convert_ADC_to_GSR(gsr_raw)]})
        self.live_data = pd.concat([self.live_data, new_row], ignore_index=True)
        self.cursor.execute("insert into sensor_data(shimmer_id, data_timestamp, gsr_raw, ppg_raw) values (?, ?, ?, ?)",
                            self.id, timestamp, gsr_raw, ppg_raw)
        self.cnxn.commit()

    def get_live_data(self):
        return self.live_data

    def start_streaming(self):
        self.shim_dev.start_streaming()

    def stop_streaming(self):
        self.shim_dev.stop_streaming()
        time.sleep(1)
        self.shim_dev.shutdown()


# noinspection DuplicatedCode
def convert_ADC_to_GSR(gsr_raw_value):
    r_feedback_per_range = [
        40.2,  # range 0
        287.0,  # range 1
        1000.0,  # range 2
        3300.0  # range 3
    ]

    gsr_range = (gsr_raw_value >> 14) & 0x03;
    gsr_raw_value = gsr_raw_value & 4095
    if gsr_range == 3 and gsr_raw_value < 683:
        gsr_raw_value = 683
    adcRange = pow(2, 12) - 1
    ref_adc_voltage = 3.0

    calVolts = (((gsr_raw_value * ref_adc_voltage) / adcRange))

    r_feedback = r_feedback_per_range[gsr_range]
    gsr_ref_voltage = 0.5
    gsr_resistance = r_feedback / ((calVolts / gsr_ref_voltage) - 1.0)
    conductance = 1000.0 / gsr_resistance
    return conductance


class FakeShimmerBluetooth:
    def __init__(self):
        self._initialized = False
        self.index = 0
        self.stop_thread = False

        self.live_data = pd.DataFrame(columns=['timestamp', 'gsr_raw', 'ppg_raw'])

        # Establish a connection to the database
        self.cnxn, self.cursor = connect_db()

        # Fetch the data from the database
        self.data = self.fetch_data()

    def fetch_data(self):
        self.cursor.execute("""
            WITH StreamData AS (
                SELECT event,
                       datetime
                FROM [PSV].[dbo].[measurement]
                WHERE shimmer_id = 3 AND event IN ('fake_start', 'fake_end')
            )
            SELECT *
            FROM [PSV].[dbo].[sensor_data]
            WHERE datetime BETWEEN (SELECT datetime FROM StreamData WHERE event = 'fake_start') 
                              AND (SELECT datetime FROM StreamData WHERE event = 'fake_end')
        """)

        # Fetch the results and convert them to a DataFrame
        data = self.cursor.fetchall()
        data = pd.DataFrame.from_records(data, columns=[column[0] for column in self.cursor.description])

        return data

    def initialize(self):
        self._initialized = True

    def get_battery_state(self, arg):
        return 0

    def get_device_name(self):
        return "Fake Device"

    def add_stream_callback(self, handler):
        pass

    def start_streaming(self):
        def stream_data():
            while self.index < len(self.data):
                if self.stop_thread:  # Check the flag in each iteration
                    break
                self.handler(self.data.iloc[self.index])
                self.index += 1
                time.sleep(0.25)  # Wait for 1 second before the next iteration

        threading.Thread(target=stream_data).start()

    def handler(self, pkt):
        timestamp = pkt['data_timestamp']
        gsr_raw = pkt['gsr_raw']
        ppg_raw = pkt['ppg_raw']
        # print(pkt.channels)
        # print(f'Received new data point at {timestamp}: GSR {gsr_raw}, PPG {ppg_raw}')

        new_row = pd.DataFrame({'timestamp': [timestamp], 'gsr_raw': [gsr_raw], 'ppg_raw': [ppg_raw],
                                'gsr': [convert_ADC_to_GSR(gsr_raw)]})
        self.live_data = pd.concat([self.live_data, new_row], ignore_index=True)

    def stop_streaming(self):
        self.stop_thread = True

    def shutdown(self):
        pass
