import sys
import time

import zmq


def main():
    addr = sys.argv[1]

    context = zmq.Context()

    socket = context.socket(zmq.REP)
    socket.bind(f'tcp://*:{addr}')

    while True:
        # Wait for a request from the client
        message = socket.recv_string()
        print(f'Received request: {message}')

        # Pretend to work
        time.sleep(5)

        # Send the response back to the client
        socket.send_string(f'Robot finished {message}')

if __name__ == '__main__':
    main()
