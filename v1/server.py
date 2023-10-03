from queue import Queue
from threading import Thread

import networkx as nx
import zmq


def robot_thread(addr, q: Queue):
    context = zmq.Context.instance()

    socket = context.socket(zmq.REQ)
    socket.connect(addr)

    while True:
        message = q.get()

        socket.send_string(message)
        response = socket.recv_string()

        q.task_done()

class Robot():
    def __init__(self, name, addr):
        self.name = name

        self.q = Queue()
        self.thread = Thread(target=robot_thread, args=(addr, self.q))
        self.thread.daemon = True
        self.thread.start()

class Action():
    def __init__(self, robot, message):
        self.robot = robot
        self.message = message
        self.state = 'new'

    def start(self):
        print(f'Sending [{self.robot.name}] [{self.message}]')

        if 'moveto' in self.message:
            stations = {
                'PlateStation': '0.40 0.89',
                'BreadStation': '0.42 -0.32',
                'HamStation': '0.05 0.51',
                'CheeseStation': '0.54 -0.84',
                'BuildStation': '0 0',
                'CustomerStation': '-0.69 -0.23',
            }
            if self.robot.name == 'Arm1':
                stations['HomeStation'] = '0.32 0.57'
            elif self.robot.name == 'Arm2':
                stations['HomeStation'] = '0.19 -0.64'
            elif self.robot.name == 'Arm3':
                stations['HomeStation'] = '-0.42 0.15'

            pos = stations[self.message.split()[-1]]

            self.robot.q.put(f'moveto {pos} 0.350 0 1 0 0')

            if 'BuildStation' in self.message or 'CustomerStation' in self.message:
                self.robot.q.put(f'moveto {pos} 0.286 0 1 0 0')
            else:
                self.robot.q.put(f'moveto {pos} 0.196 0 1 0 0')
        elif 'clear' in self.message:
            pass
        else:
            self.robot.q.put(self.message)

        self.state = 'running'

def design_graph(robots):
    # Create the directed graph
    G = nx.DiGraph()

    with open('nodes.txt') as f:
        for line in f:
            line = line.split('#', 1)[0].strip()
            if not line:
                continue

            node, robot, message = line.split(' ', 2)

            node = int(node.rstrip('.'))

            G.add_node(node, action=Action(robots[robot], message))

    relations = []
    with open('edges.txt') as f:
        for line in f:
            line = line.strip().split()
            if not line:
                continue

            relations.append(tuple(map(int, line)))

    G.add_edges_from(relations)

    return G

def main():
    robots = {
        'Arm1': Robot('Arm1', 'tcp://192.168.86.217:5561'),
        'Arm2': Robot('Arm2', 'tcp://192.168.86.217:5562'),
        'Arm3': Robot('Arm3', 'tcp://192.168.86.217:5563'),
    }

    G = design_graph(robots)

    assert nx.algorithms.dag.is_directed_acyclic_graph(G)

    while len(G) > 0:
        # Tell all upcoming nodes to run their command
        # Mark all of those nodes as running
        for node in G:
            action = G.nodes[node]['action']
            if G.in_degree(node) == 0 and action.state == 'new':
                action.start()
                action.state = 'running'

        # Find all 'running' nodes that have a 'completed' message
        # Remove those from the graph
        completed_nodes = []
        for node in G:
            action = G.nodes[node]['action']
            if action.state == 'running' and action.robot.q.unfinished_tasks == 0:
                print(f'Done [{action.robot.name}] [{action.message}]')
                completed_nodes.append(node)
        for node in completed_nodes:
            G.remove_node(node)

if __name__ == '__main__':
    main()
