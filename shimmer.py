import pyodbc
from serial import Serial
from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType
import config


class ShimmerDevice:
    def __init__(self, com_port):
        self.serial = Serial(com_port, DEFAULT_BAUDRATE)
        self.shim_dev = ShimmerBluetooth(self.serial)
        self.shim_dev.initialize()

        self.batt = self.shim_dev.get_battery_state(True)
        self.dev_name = self.shim_dev.get_device_name()
        print(f'My name is: {self.dev_name} and my battery is at {self.batt}%')

        self.shim_dev.add_stream_callback(self.handler)

        self.cnxn = pyodbc.connect(
            driver="{ODBC Driver 17 for SQL Server}", server=config.server_host, database="PSV",
            uid="team", pwd=config.password)
        self.cursor = self.cnxn.cursor()

    def handler(self, pkt: DataPacket):
        timestamp = pkt[EChannelType.TIMESTAMP]
        gsr_raw = pkt[EChannelType.GSR_RAW]
        print(pkt.channels)
        print(f'Received new data point at {timestamp}: {gsr_raw}')

        self.cursor.execute("insert into shimmer_data(sensor_name, data_timestamp, data_gsr_raw) values (?, ?, ?)",
                            self.dev_name, timestamp, gsr_raw)
        self.cnxn.commit()

    def start_streaming(self):
        self.shim_dev.start_streaming()

    def stop_streaming(self):
        self.shim_dev.stop_streaming()
        self.shim_dev.shutdown()
