import pickle

import networkx as nx
import zmq
from utils import CLI_ADDR, Command, Flags, Job, JobID, Node, ResourceAlias


def custom_job() -> Job:
    group = ResourceAlias(
        template={
            'variant': 'group',
            'name': '0',
        },
    )

    sci = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'platecrane_sciclops',
            'group': (group, 'name'),
        },
    )
    pf400 = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'pf400',
            'group': (group, 'name'),
        },
    )
    ot2_0 = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'ot2',
            'group': (group, 'name'),
        },
    )
    ot2_1 = ResourceAlias(
        template={
            'variant': 'agent',
            'model': 'ot2',
            'group': (group, 'name'),
        },
    )

    aliases = [
        group,
        sci,
        pf400,
        ot2_0,
        ot2_1,
    ]

    nodes = [
        Node('Lock group', locks=[(group, 'key_0')]),
        Node('Lock machines', locks=[(sci, 'key_0'), (pf400, 'key_0'), (ot2_0, 'key_0'), (ot2_1, 'key_0')]),

        Node('0 sci 0', command=Command(sci, ['home'])),

        Node('0 sci 1', command=Command(sci, ['move_close', (sci, 'plate_stack_position')])),
        Node('0 sci 2', command=Command(sci, ['move_to',    (sci, 'plate_stack_position')])),
        Node('0 sci 3', command=Command(sci, ['grab'])),
        Node('0 sci 4', command=Command(sci, ['move_close', (sci, 'plate_stack_position')])),

        Node('0 sci 5', command=Command(sci, ['move_close', (sci, 'plate_transfer_position')])),
        Node('0 sci 6', command=Command(sci, ['move_to',    (sci, 'plate_transfer_position')])),
        Node('0 sci 7', command=Command(sci, ['release'])),
        Node('0 sci 8', command=Command(sci, ['move_close', (sci, 'plate_transfer_position')])),

        Node('0 sci 9', command=Command(sci, ['home'])),

        Node('0 pf400 0', command=Command(pf400, ['home'])),

        Node('0 pf400 1', command=Command(pf400, ['move_close', (sci, 'plate_transfer_position')])),
        Node('0 pf400 2', command=Command(pf400, ['move_to',    (sci, 'plate_transfer_position')])),
        Node('0 pf400 3', command=Command(pf400, ['grab'])),
        Node('0 pf400 4', command=Command(pf400, ['move_close', (sci, 'plate_transfer_position')])),

        Node('0 pf400 5', command=Command(pf400, ['home'])),

        Node('0 pf400 6', command=Command(pf400, ['move_close', (ot2_0, 'deck_position')])),
        Node('0 pf400 7', command=Command(pf400, ['move_to',    (ot2_0, 'deck_position')])),
        Node('0 pf400 8', command=Command(pf400, ['release'])),
        Node('0 pf400 9', command=Command(pf400, ['move_close', (ot2_0, 'deck_position')])),

        Node('0 pf400 10', command=Command(pf400, ['home'])),

        Node('ot2_0 0', command=Command(ot2_0, ['home'])),
        Node('ot2_0 1', command=Command(ot2_0, ['move_close', (ot2_0, 'deck_position')])),
        Node('ot2_0 2s', sleep=3),
        Node('ot2_0 3', command=Command(ot2_0, ['home'])),
        Node('ot2_0 4s', sleep=0.5),
        Node('ot2_0 5', command=Command(ot2_0, ['move_close', (ot2_0, 'deck_position')])),
        Node('ot2_0 6s', sleep=3),
        Node('ot2_0 7', command=Command(ot2_0, ['home'])),
        Node('ot2_0 8s', sleep=0.5),
        Node('ot2_0 9', command=Command(ot2_0, ['move_close', (ot2_0, 'deck_position')])),
        Node('ot2_0 10s', sleep=3),
        Node('ot2_0 11', command=Command(ot2_0, ['home'])),



        Node('1 sci 0', command=Command(sci, ['home'])),

        Node('1 sci 1', command=Command(sci, ['move_close', (sci, 'plate_stack_position')])),
        Node('1 sci 2', command=Command(sci, ['move_to',    (sci, 'plate_stack_position')])),
        Node('1 sci 3', command=Command(sci, ['grab'])),
        Node('1 sci 4', command=Command(sci, ['move_close', (sci, 'plate_stack_position')])),

        Node('1 sci 5', command=Command(sci, ['move_close', (sci, 'plate_transfer_position')])),
        Node('1 sci 6', command=Command(sci, ['move_to',    (sci, 'plate_transfer_position')])),
        Node('1 sci 7', command=Command(sci, ['release'])),
        Node('1 sci 8', command=Command(sci, ['move_close', (sci, 'plate_transfer_position')])),

        Node('1 sci 9', command=Command(sci, ['home'])),

        Node('1 pf400 0', command=Command(pf400, ['home'])),

        Node('1 pf400 1', command=Command(pf400, ['move_close', (sci, 'plate_transfer_position')])),
        Node('1 pf400 2', command=Command(pf400, ['move_to',    (sci, 'plate_transfer_position')])),
        Node('1 pf400 3', command=Command(pf400, ['grab'])),
        Node('1 pf400 4', command=Command(pf400, ['move_close', (sci, 'plate_transfer_position')])),

        Node('1 pf400 5', command=Command(pf400, ['home'])),

        Node('1 pf400 6', command=Command(pf400, ['move_close', (ot2_1, 'deck_position')])),
        Node('1 pf400 7', command=Command(pf400, ['move_to',    (ot2_1, 'deck_position')])),
        Node('1 pf400 8', command=Command(pf400, ['release'])),
        Node('1 pf400 9', command=Command(pf400, ['move_close', (ot2_1, 'deck_position')])),

        Node('1 pf400 10', command=Command(pf400, ['home'])),

        Node('ot2_1 0', command=Command(ot2_1, ['home'])),
        Node('ot2_1 1', command=Command(ot2_1, ['move_close', (ot2_1, 'deck_position')])),
        Node('ot2_1 2s', sleep=3),
        Node('ot2_1 3', command=Command(ot2_1, ['home'])),
        Node('ot2_1 4s', sleep=0.5),
        Node('ot2_1 5', command=Command(ot2_1, ['move_close', (ot2_1, 'deck_position')])),
        Node('ot2_1 6s', sleep=3),
        Node('ot2_1 7', command=Command(ot2_1, ['home'])),
        Node('ot2_1 8s', sleep=0.5),
        Node('ot2_1 9', command=Command(ot2_1, ['move_close', (ot2_1, 'deck_position')])),
        Node('ot2_1 10s', sleep=3),
        Node('ot2_1 11', command=Command(ot2_1, ['home'])),

        # Node('Unlock machines', unlocks=[(sci, 'key_0'), (pf400, 'key_0'), (ot2_0, 'key_0'), (ot2_1, 'key_0')]),
        # Node('Unlock group', unlocks=[(group, 'key_0')]),
    ]

    def gn(name: str) -> None|Node:
        for node in nodes:
            if node.name == name:
                return node
        return None

    edges = [
        # (gn('a0'), gn('a1')),
        # (gn('b0'), gn('b1')),
        (gn('Lock group'), gn('Lock machines')),

        (gn('Lock machines'), gn('0 sci 0')),

        (gn('0 sci 0'), gn('0 sci 1')),
        (gn('0 sci 1'), gn('0 sci 2')),
        (gn('0 sci 2'), gn('0 sci 3')),
        (gn('0 sci 3'), gn('0 sci 4')),
        (gn('0 sci 4'), gn('0 sci 5')),
        (gn('0 sci 5'), gn('0 sci 6')),
        (gn('0 sci 6'), gn('0 sci 7')),
        (gn('0 sci 7'), gn('0 sci 8')),
        (gn('0 sci 8'), gn('0 sci 9')),
        (gn('0 sci 9'), gn('0 pf400 0')),


        (gn('0 pf400 0'), gn('0 pf400 1')),
        (gn('0 pf400 1'), gn('0 pf400 2')),
        (gn('0 pf400 2'), gn('0 pf400 3')),
        (gn('0 pf400 3'), gn('0 pf400 4')),
        (gn('0 pf400 4'), gn('0 pf400 5')),
        (gn('0 pf400 5'), gn('0 pf400 6')),
        (gn('0 pf400 5'), gn('1 sci 0')),
        (gn('0 pf400 6'), gn('0 pf400 7')),
        (gn('0 pf400 7'), gn('0 pf400 8')),
        (gn('0 pf400 8'), gn('0 pf400 9')),
        (gn('0 pf400 9'), gn('0 pf400 10')),
        (gn('0 pf400 10'), gn('ot2_0 0')),
        (gn('0 pf400 10'), gn('1 pf400 0')),

        (gn('ot2_0 0'),   gn('ot2_0 1')),
        (gn('ot2_0 1'),   gn('ot2_0 2s')),
        (gn('ot2_0 2s'),  gn('ot2_0 3')),
        (gn('ot2_0 3'),   gn('ot2_0 4s')),
        (gn('ot2_0 4s'),  gn('ot2_0 5')),
        (gn('ot2_0 5'),   gn('ot2_0 6s')),
        (gn('ot2_0 6s'),  gn('ot2_0 7')),
        (gn('ot2_0 7'),   gn('ot2_0 8s')),
        (gn('ot2_0 8s'),  gn('ot2_0 9')),
        (gn('ot2_0 9'),   gn('ot2_0 10s')),
        (gn('ot2_0 10s'), gn('ot2_0 11')),

        (gn('1 sci 0'), gn('1 sci 1')),
        (gn('1 sci 1'), gn('1 sci 2')),
        (gn('1 sci 2'), gn('1 sci 3')),
        (gn('1 sci 3'), gn('1 sci 4')),
        (gn('1 sci 4'), gn('1 sci 5')),
        (gn('1 sci 5'), gn('1 sci 6')),
        (gn('1 sci 6'), gn('1 sci 7')),
        (gn('1 sci 7'), gn('1 sci 8')),
        (gn('1 sci 8'), gn('1 sci 9')),
        (gn('1 sci 9'), gn('1 pf400 0')),

        (gn('1 pf400 0'), gn('1 pf400 1')),
        (gn('1 pf400 1'), gn('1 pf400 2')),
        (gn('1 pf400 2'), gn('1 pf400 3')),
        (gn('1 pf400 3'), gn('1 pf400 4')),
        (gn('1 pf400 4'), gn('1 pf400 5')),
        (gn('1 pf400 5'), gn('1 pf400 6')),
        (gn('1 pf400 6'), gn('1 pf400 7')),
        (gn('1 pf400 7'), gn('1 pf400 8')),
        (gn('1 pf400 8'), gn('1 pf400 9')),
        (gn('1 pf400 9'), gn('1 pf400 10')),
        (gn('1 pf400 10'), gn('ot2_1 0')),

        (gn('ot2_1 0'),   gn('ot2_1 1')),
        (gn('ot2_1 1'),   gn('ot2_1 2s')),
        (gn('ot2_1 2s'),  gn('ot2_1 3')),
        (gn('ot2_1 3'),   gn('ot2_1 4s')),
        (gn('ot2_1 4s'),  gn('ot2_1 5')),
        (gn('ot2_1 5'),   gn('ot2_1 6s')),
        (gn('ot2_1 6s'),  gn('ot2_1 7')),
        (gn('ot2_1 7'),   gn('ot2_1 8s')),
        (gn('ot2_1 8s'),  gn('ot2_1 9')),
        (gn('ot2_1 9'),   gn('ot2_1 10s')),
        (gn('ot2_1 10s'), gn('ot2_1 11')),

        # (gn('ot2_0 11'), gn('Unlock machines')),
        # (gn('ot2_1 11'), gn('Unlock machines')),

        # (gn('Unlock machines'), gn('Unlock group')),
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
