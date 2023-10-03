import uuid

import networkx as nx
import zmq
from utils import (CLIENT_SERVER_ADDR, Flag, JobID, NodeAction,
                   ResourceAlias, ResourceTemplate, serialize_graph,
                   serialize_templs)

context = zmq.Context()

def graph_GPT(prompt: str) -> tuple[dict[ResourceAlias, ResourceTemplate], nx.DiGraph]:
    templs = {
        'Arm1': ResourceTemplate(**{
            'variant': 'agent',
            'model': 'ur5e',
            'name': 'Arm1',
        }),
        'Arm2': ResourceTemplate(**{
            'variant': 'agent',
            'model': 'ur5e',
            'name': 'Arm2',
        }),
        'Arm3': ResourceTemplate(**{
            'variant': 'agent',
            'model': 'ur5e',
            'name': 'Arm3',
        }),
    }

    nodes = []
    with open('nodes.txt') as f:
        for line in f:
            line = line.split('#', 1)[0].strip()
            if not line:
                continue

            ID, robot_alias, *action = line.split(' ')

            nodes.append((
                ID,
                {
                    'action': NodeAction.Command.value,
                    'args': [robot_alias, *action],
                },
            ))

    edges = []
    with open('edges.txt') as f:
        for line in f:
            line = line.strip().split()
            if not line:
                continue

            edges.append(line)

    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    entrypoints = set(n for n, d in G.in_degree() if d==0)
    exitpoints = set(n for n, d in G.out_degree() if d==0)
    G.add_node('entry', action=NodeAction.Lock.value, args=list(templs.keys()))
    G.add_node('exit', action=NodeAction.Unlock.value, args=list(templs.keys()))
    G.add_edges_from([('entry', node) for node in entrypoints])
    G.add_edges_from([(node, 'exit') for node in exitpoints])

    return templs, G

def submit(templs: dict[ResourceAlias, ResourceTemplate], G: nx.DiGraph) -> JobID|None:
    with context.socket(zmq.REQ) as sock:
        sock.connect(CLIENT_SERVER_ADDR.replace('*', 'localhost'))
        sock.setsockopt(zmq.RCVTIMEO, 2000)

        sock.send_multipart([
            Flag.CLI_GSUB.value.encode(),
            serialize_templs(templs).encode(),
            serialize_graph(G).encode(),
        ])
        try:
            flag, *msg = sock.recv_multipart()
        except zmq.error.Again:
            return None

    if flag == Flag.SUCCESS.value.encode():
        job_id = uuid.UUID(msg[0].decode())
    else:
        return None

    return job_id
