import time
import pyodbc

from serial import Serial

from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType

import config


def handler(pkt: DataPacket) -> None:
    timestamp = pkt[EChannelType.TIMESTAMP]
    gsr_raw = pkt[EChannelType.GSR_RAW]
    print(pkt.channels)
    print(f'Received new data point at {timestamp}: {gsr_raw}')

    cursor.execute("insert into shimmer_data(sensor_name, data_timestamp, data_gsr_raw) values (?, ?, ?)",
                   dev_name, timestamp, gsr_raw)
    cnxn.commit()


if __name__ == '__main__':
    cnxn = pyodbc.connect(
        driver="{ODBC Driver 17 for SQL Server}", server=config.server_host, database="PSV",
        uid="team", pwd=config.password)
    cursor = cnxn.cursor()

    # noinspection DuplicatedCode
    serial = Serial('COM7', DEFAULT_BAUDRATE)
    shim_dev = ShimmerBluetooth(serial)

    shim_dev.initialize()

    shim_dev.set_rtc(time.time())

    batt = shim_dev.get_battery_state(True)

    dev_name = shim_dev.get_device_name()
    print(f'My name is: {dev_name} and my battery is at {batt}%')

    shim_dev.add_stream_callback(handler)

    shim_dev.start_streaming()
    time.sleep(600.0)
    shim_dev.stop_streaming()

    shim_dev.shutdown()

    exit(0)

exit(0)
