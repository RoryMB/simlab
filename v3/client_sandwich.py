import pickle

import networkx as nx
import zmq
from utils import CLI_ADDR, Command, Flags, Job, JobID, Node, ResourceAlias


def custom_job() -> Job:
    arm1 = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'ur5e',
            'name': 'Arm1',
        }
    )
    arm2 = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'ur5e',
            'name': 'Arm2',
        }
    )
    arm3 = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'ur5e',
            'name': 'Arm3',
        }
    )
    aliases = [
        arm1,
        arm2,
        arm3,
    ]

    nodes = [
        # N('a1', locks=[(arm1, 'key_a'),]),
        # N('a2', cmd=(arm1, ['moveto', 'PlateStation'])),
        # N('a3', cmd=(arm1, ['grab'])),
        # N('a4', unlocks=[(arm1, 'key_a'),]),
        Node('a1', locks=[(arm1, 'a')]),
        Node('a2', command=Command(arm1, ['moveto', 'PlateStation'])),
        Node('a3', command=Command(arm1, ['grab'])),
        Node('a5', command=Command(arm1, ['moveto', 'BuildStation'])),
        Node('a6', command=Command(arm1, ['release'])),
        Node('a7', command=Command(arm1, ['moveto', 'HomeStation'])),
        Node('a9', unlocks=[(arm1, 'a')]),

        Node('b1', locks=[(arm2, 'b')]),
        Node('b2', command=Command(arm2, ['moveto', 'BreadStation'])),
        Node('b3', command=Command(arm2, ['grab'])),
        Node('b5', command=Command(arm2, ['moveto', 'BuildStation'])),
        Node('b6', command=Command(arm2, ['release'])),
        Node('b7', command=Command(arm2, ['moveto', 'HomeStation'])),
        Node('b9', unlocks=[(arm2, 'b')]),

        Node('c1', locks=[(arm1, 'c')]),
        Node('c2', command=Command(arm1, ['moveto', 'HamStation'])),
        Node('c3', command=Command(arm1, ['grab'])),
        Node('c5', command=Command(arm1, ['moveto', 'BuildStation'])),
        Node('c6', command=Command(arm1, ['release'])),
        Node('c7', command=Command(arm1, ['moveto', 'HomeStation'])),
        Node('c9', unlocks=[(arm1, 'c')]),

        Node('d1', locks=[(arm2, 'd')]),
        Node('d2', command=Command(arm2, ['moveto', 'CheeseStation'])),
        Node('d3', command=Command(arm2, ['grab'])),
        Node('d5', command=Command(arm2, ['moveto', 'BuildStation'])),
        Node('d6', command=Command(arm2, ['release'])),
        Node('d7', command=Command(arm2, ['moveto', 'HomeStation'])),
        Node('d9', unlocks=[(arm2, 'd')]),

        Node('e1', locks=[(arm2, 'e')]),
        Node('e2', command=Command(arm2, ['moveto', 'BreadStation'])),
        Node('e3', command=Command(arm2, ['grab'])),
        Node('e5', command=Command(arm2, ['moveto', 'BuildStation'])),
        Node('e6', command=Command(arm2, ['release'])),
        Node('e7', command=Command(arm2, ['moveto', 'HomeStation'])),
        Node('e9', unlocks=[(arm2, 'e')]),

        Node('f1', locks=[(arm3, 'f')]),
        Node('f3', command=Command(arm3, ['moveto', 'BuildStation'])),
        Node('f4', command=Command(arm3, ['grab'])),
        Node('f5', command=Command(arm3, ['moveto', 'CustomerStation'])),
        Node('f7', command=Command(arm3, ['release'])),
        Node('f8', command=Command(arm3, ['moveto', 'HomeStation'])),
        Node('f9', unlocks=[(arm3, 'f')]),
    ]

    def gn(name: str) -> None|Node:
        for node in nodes:
            if node.name == name:
                return node
        return None

    edges = [
        # (gn('a0'), gn('a1')),
        # (gn('b0'), gn('b1')),
        # (gn('c0'), gn('c1')),
        # (gn('d0'), gn('d1')),
        # (gn('e0'), gn('e1')),
        # (gn('f0'), gn('f1')),

        (gn('a1'), gn('a2')),
        (gn('a2'), gn('a3')),
        (gn('a3'), gn('a5')),
        # (gn('a3'), gn('a4')),
        # (gn('a4'), gn('a5')),
        (gn('a5'), gn('a6')),
        (gn('a6'), gn('a7')),
        (gn('a7'), gn('a9')),
        # (gn('a7'), gn('a8')),
        # (gn('a8'), gn('a9')),

        (gn('b1'), gn('b2')),
        (gn('b2'), gn('b3')),
        (gn('b3'), gn('b5')),
        # (gn('b3'), gn('b4')),
        # (gn('b4'), gn('b5')),
        (gn('b5'), gn('b6')),
        (gn('b6'), gn('b7')),
        (gn('b7'), gn('b9')),
        # (gn('b7'), gn('b8')),
        # (gn('b8'), gn('b9')),

        (gn('c1'), gn('c2')),
        (gn('c2'), gn('c3')),
        (gn('c3'), gn('c5')),
        # (gn('c3'), gn('c4')),
        # (gn('c4'), gn('c5')),
        (gn('c5'), gn('c6')),
        (gn('c6'), gn('c7')),
        (gn('c7'), gn('c9')),
        # (gn('c7'), gn('c8')),
        # (gn('c8'), gn('c9')),

        (gn('d1'), gn('d2')),
        (gn('d2'), gn('d3')),
        (gn('d3'), gn('d5')),
        # (gn('d3'), gn('d4')),
        # (gn('d4'), gn('d5')),
        (gn('d5'), gn('d6')),
        (gn('d6'), gn('d7')),
        (gn('d7'), gn('d9')),
        # (gn('d7'), gn('d8')),
        # (gn('d8'), gn('d9')),

        (gn('e1'), gn('e2')),
        (gn('e2'), gn('e3')),
        (gn('e3'), gn('e5')),
        # (gn('e3'), gn('e4')),
        # (gn('e4'), gn('e5')),
        (gn('e5'), gn('e6')),
        (gn('e6'), gn('e7')),
        (gn('e7'), gn('e9')),
        # (gn('e7'), gn('e8')),
        # (gn('e8'), gn('e9')),

        (gn('f1'), gn('f3')),
        # (gn('f1'), gn('f2')),
        # (gn('f2'), gn('f3')),
        (gn('f3'), gn('f4')),
        (gn('f4'), gn('f5')),
        (gn('f5'), gn('f7')),
        # (gn('f5'), gn('f6')),
        # (gn('f6'), gn('f7')),
        (gn('f7'), gn('f8')),
        (gn('f8'), gn('f9')),

        (gn('a7'), gn('b5')),
        (gn('b7'), gn('c5')),
        (gn('c7'), gn('d5')),
        (gn('d7'), gn('e5')),
        (gn('e7'), gn('f3')),
    ]

    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    return Job(aliases=aliases, graph=graph)

def submit(job: Job) -> None|JobID:
    context: zmq.Context[zmq.Socket] = zmq.Context.instance()
    with context.socket(zmq.REQ) as sock:
        sock.connect(CLI_ADDR)
        sock.send_multipart([Flags.SUBMIT_JOB, pickle.dumps(job)])
        msg = sock.recv_multipart()

    match msg:
        case [Flags.SUCCESS, reply]:
            return pickle.loads(reply)
        case [Flags.FAILURE]:
            return None
        case _:
            assert False

def main():
    job = custom_job()

    print(f'Client submitting graph')
    job_id = submit(job)

    print(f'Client received job ID {job_id}')

    # import matplotlib.pyplot as plt
    # pos = nx.nx_agraph.graphviz_layout(job.graph, prog='dot')
    # labeldict = {n:n.name for n in job.graph.nodes}
    # nx.draw(job.graph, pos, labels=labeldict, with_labels=True, font_size=5, arrowsize=10, node_size=200)
    # plt.show()

if __name__ == '__main__':
    main()
