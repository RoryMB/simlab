import json
import sys
import time

import zmq
from utils import LAB_SERVER_ADDR, Flag

context = zmq.Context()

def hello(addr, name):
    with context.socket(zmq.PUB) as sock_pub:
        addr = addr.replace('*', 'localhost')
        sock_pub.connect(LAB_SERVER_ADDR.replace('*', 'localhost'))
        time.sleep(1)
        print('Publishing address:', addr)
        sock_pub.send_multipart([
            Flag.HELLO.value.encode(),
            addr.encode(),
            json.dumps({
                'variant': 'agent',
                'model': 'ur5e',
                'name': name,
            }).encode(),
        ])

def goodbye(addr):
    with context.socket(zmq.PUB) as sock_pub:
        addr = addr.replace('*', 'localhost')
        sock_pub.connect(LAB_SERVER_ADDR.replace('*', 'localhost'))
        time.sleep(1)
        print('Publishing address:', addr)
        sock_pub.send_multipart([
            Flag.GOODBYE.value.encode(),
            addr.encode(),
        ])

def main(port, name):
    addr = f'tcp://*:{port}'
    with context.socket(zmq.REP) as sock:
        sock.bind(addr)

        hello(addr.replace('*', 'localhost'), name)

        try:
            while True:
                msg = sock.recv()
                msg = json.loads(msg.decode())
                print('Received message:', msg)

                time.sleep(0.5)

                msg = json.dumps({
                    'action_response': 0, # typically 0 (good) or -1 (bad)
                    'action_msg': '', # str
                    'action_log': '', # str
                }).encode()
                sock.send(msg)
        except:
            goodbye(addr.replace('*', 'localhost'))
            raise

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
