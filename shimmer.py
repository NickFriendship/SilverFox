import atexit
import time
import threading
import pyodbc
import pandas as pd
import re
from datetime import datetime
from serial import Serial
from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType
import config


def connect_db():
    cnxn = pyodbc.connect(
        driver="{ODBC Driver 17 for SQL Server}", server=config.server_host, database="PSV",
        uid="team", pwd=config.password)
    return cnxn


class ShimmerDevice:

    def __init__(self, com_port, fake_fallback: bool = False, live_upload: bool = False):
        # register exit methods
        atexit.register(self.safe_stop)

        self.live_data = pd.DataFrame(columns=['gsr',
                                               'datetime',
                                               'timestamp',
                                               'gsr_raw',
                                               'ppg_raw'])
        self.com_port = com_port
        self.live_upload = live_upload

        try:
            self.serial = Serial(com_port, DEFAULT_BAUDRATE)
            self.shim_dev = ShimmerBluetooth(self.serial)
        except Exception as e:
            print(f"Failed to initialize Serial object with com_port: {com_port}. Error: {e}")
            error_code = re.search(r'None, (\d+)\)', str(e))
            if fake_fallback and error_code and error_code.group(1) == '121':
                print("Falling back to FakeShimmerBluetooth")
                self.shim_dev = FakeShimmerBluetooth()
            else:
                raise e

        self.shim_dev.initialize()
        self.init_time = datetime.now()

        self.batt = self.shim_dev.get_battery_state(True)
        self.dev_name = self.shim_dev.get_device_name()
        print(f'My name is: {self.dev_name} and my battery is at {self.batt}%')

        self.shim_dev.add_stream_callback(self.handler)

        self.cnxn = connect_db()

        with self.cnxn.cursor() as cursor:
            cursor.execute("""MERGE INTO dbo.shimmer AS target
        USING (SELECT ?, ?, ?) AS source (name, port, battery_perc)
        ON (target.name = source.name)
        WHEN MATCHED THEN
            UPDATE SET target.port = source.port, target.battery_perc = source.battery_perc
        WHEN NOT MATCHED THEN
            INSERT (name, port, battery_perc)
            VALUES (source.name, source.port, source.battery_perc)
        OUTPUT INSERTED.id;
                    """, (self.dev_name, self.com_port, self.batt))
            self.id = cursor.fetchone()[0]

        self.cnxn.commit()

    def handler(self, pkt: DataPacket):
        curtime = datetime.now()

        timestamp = pkt[EChannelType.TIMESTAMP]
        gsr_raw = pkt[EChannelType.GSR_RAW]
        ppg_raw = pkt[EChannelType.INTERNAL_ADC_13]
        # print(pkt.channels)
        # print(f'Received new data point at {timestamp}: GSR {gsr_raw}, PPG {ppg_raw}')

        # Ignore the first few seconds of data coming in as it's unreliable
        if (curtime - self.init_time).total_seconds() < 4:
            return

        new_row = pd.DataFrame({'datetime': [curtime],
                                'gsr': [convert_ADC_to_GSR(gsr_raw)],
                                'timestamp': [timestamp],
                                'gsr_raw': [gsr_raw],
                                'ppg_raw': [ppg_raw]
                                })
        self.live_data = pd.concat([self.live_data, new_row], ignore_index=True)

        if self.live_upload:
            with self.cnxn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO sensor_data(shimmer_id, data_timestamp, gsr_raw, ppg_raw)
                VALUES (?, ?, ?, ?)""",
                    self.id, timestamp, gsr_raw, ppg_raw)
                self.cnxn.commit()

    def get_live_data(self):
        return self.live_data

    def start_streaming(self):
        self.shim_dev.start_streaming()

    def stop_streaming(self, stop_event: bool = True, upload_data: bool = True):
        self.shim_dev.stop_streaming()
        if stop_event:
            # Crate stop_game event based on the device's last start_game event
            with self.cnxn.cursor() as cursor:
                query = """
                WITH RecentPlayerId AS (
                    SELECT TOP 1 player_id, note
                    FROM measurement
                    WHERE shimmer_id = ? AND event = 'start_game'
                    ORDER BY datetime DESC
                )
                INSERT INTO measurement (player_id, shimmer_id, event, note)
                SELECT player_id, ?, 'stop_game', note
                FROM RecentPlayerId
                """
                cursor.execute(query, (self.id, self.id))
                self.cnxn.commit()

        if upload_data:
            for index, row in self.live_data.iterrows():
                with self.cnxn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO sensor_data(datetime, shimmer_id, data_timestamp, gsr_raw, ppg_raw)
                        VALUES (?, ?, ?, ?, ?)""",
                        row['datetime'], self.id, row['timestamp'], row['gsr_raw'], row['ppg_raw'])
                    self.cnxn.commit()

                # Clear the live_data DataFrame
                self.live_data = pd.DataFrame(columns=['gsr', 'datetime', 'timestamp', 'gsr_raw', 'ppg_raw'])

        self.live_data = pd.DataFrame(columns=['gsr', 'datetime', 'timestamp', 'gsr_raw', 'ppg_raw'])
        self.shim_dev.shutdown()
        self.shim_dev._initialized = False

    def safe_stop(self):
        if self.shim_dev.initialized():
            self.stop_streaming()
        if self.cnxn:
            self.cnxn.close()
            print("Database connection closed.")

    def __del__(self):
        self.safe_stop()

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
        self.cnxn = connect_db()

        # Fetch the data from the database
        self.data = self.fetch_data()

    def fetch_data(self):
        with self.cnxn.cursor() as cursor:
            cursor.execute("""
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
            data = cursor.fetchall()
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

    def initialized(self):
        return self._initialized
