import time

from shimmer import ShimmerDevice

# Demo of how to use shimmer.py to use the Shimmer for data collection

device = ShimmerDevice('COM9')
device.start_streaming()
time.sleep(1.0)
device.stop_streaming()
