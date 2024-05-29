import time

from shimmer import ShimmerDevice

# Demo of how to use shimmer.py to use the Shimmer for data collection
if __name__ == '__main__':
    device = ShimmerDevice('COM3')
    device.start_streaming()
    time.sleep(10.0)
    device.stop_streaming()

exit(0)
