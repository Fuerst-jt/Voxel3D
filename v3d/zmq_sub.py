"""
ZMQ subscriber running in a QThread and exposing Qt signals for integration with UI.
"""
import json
import traceback
from PySide6 import QtCore
import zmq

class ZMQSubscriber(QtCore.QThread):
    msg_received = QtCore.Signal(object)
    status = QtCore.Signal(str)

    def __init__(self, addr: str = 'tcp://127.0.0.1:5556', topic: bytes = b'', poll_ms: int = 200):
        super().__init__()
        self.addr = addr
        self.topic = topic
        self.poll_ms = poll_ms
        self._running = True

    def run(self):
        try:
            ctx = zmq.Context()
            sock = ctx.socket(zmq.SUB)
            sock.setsockopt(zmq.SUBSCRIBE, self.topic)
            sock.connect(self.addr)
            poller = zmq.Poller()
            poller.register(sock, zmq.POLLIN)
            self.status.emit(f"ZMQ connected -> {self.addr}")
            while self._running:
                socks = dict(poller.poll(self.poll_ms))
                if sock in socks and socks[sock] == zmq.POLLIN:
                    raw = sock.recv()
                    try:
                        msg = json.loads(raw.decode('utf-8'))
                        self.msg_received.emit(msg)
                    except Exception as e:
                        self.status.emit(f"Bad message: {e}")
            sock.close()
            ctx.term()
        except Exception as e:
            self.status.emit(f"ZMQ thread error: {e}")
            traceback.print_exc()

    def stop(self):
        self._running = False
        self.wait(500)
