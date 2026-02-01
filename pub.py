#!/usr/bin/env python3
"""
Simple ZMQ PUB demo to send scene JSON periodically.
Save as: pub.py
Usage: python pub.py
"""
import time
import json
import zmq

ctx = zmq.Context()
sock = ctx.socket(zmq.PUB)
sock.bind('tcp://127.0.0.1:5556')

print('Publisher bound to tcp://127.0.0.1:5556')
# give subscribers time to connect
time.sleep(0.2)

try:
    t = 0
    while True:
        pts = [
            {"x": 2.0 * (i % 5) + (t % 5) * 0.1, "y": (i // 5) * 1.5, "z": (i % 3) * 0.7, "size": 6, "color": [1, 0, 0, 1]} 
            for i in range(10)
        ]
        segs = [
            {"start": [0,0,0], "end": [t*0.05, 0.5, 0.2], "color": [0,1,0,1], "width": 2}
        ]
        msg = {"points": pts, "segments": segs}
        sock.send_string(json.dumps(msg))
        t += 1
        time.sleep(0.2)
except KeyboardInterrupt:
    print('Stopping publisher')
finally:
    sock.close()
    ctx.term()