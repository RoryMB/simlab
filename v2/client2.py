import matplotlib.pyplot as plt
import networkx as nx
from client1 import graph_GPT, submit
from utils import (NodeAction, ResourceAlias, ResourceTemplate,
                   deserialize_graph, serialize_graph)


def custom_graph() -> tuple[dict[ResourceAlias, ResourceTemplate], nx.DiGraph]:
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

    nodes = [
        # ('a0', {'action': NodeAction.Sleep.value, 'args': ['10']}),
        # ('b0', {'action': NodeAction.Sleep.value, 'args': ['1']}),
        # ('c0', {'action': NodeAction.Sleep.value, 'args': ['100']}),
        # ('d0', {'action': NodeAction.Sleep.value, 'args': ['100']}),
        # ('e0', {'action': NodeAction.Sleep.value, 'args': ['100']}),
        # ('f0', {'action': NodeAction.Sleep.value, 'args': ['100']}),

        ('a1', {'action': NodeAction.Lock.value, 'args': {'A Arm':'Arm1'}}),
        ('a2', {'action': NodeAction.Command.value, 'args': ['Arm1', 'moveto', 'PlateStation']}),
        ('a3', {'action': NodeAction.Command.value, 'args': ['Arm1', 'grab']}),
        ('a5', {'action': NodeAction.Command.value, 'args': ['Arm1', 'moveto', 'BuildStation']}),
        ('a6', {'action': NodeAction.Command.value, 'args': ['Arm1', 'release']}),
        ('a7', {'action': NodeAction.Command.value, 'args': ['Arm1', 'moveto', 'HomeStation']}),
        ('a9', {'action': NodeAction.Unlock.value, 'args': {'A Arm':'Arm1'}}),

        ('b1', {'action': NodeAction.Lock.value, 'args': {'B Arm':'Arm2'}}),
        ('b2', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'BreadStation']}),
        ('b3', {'action': NodeAction.Command.value, 'args': ['Arm2', 'grab']}),
        ('b5', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'BuildStation']}),
        ('b6', {'action': NodeAction.Command.value, 'args': ['Arm2', 'release']}),
        ('b7', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'HomeStation']}),
        ('b9', {'action': NodeAction.Unlock.value, 'args': {'B Arm':'Arm2'}}),

        ('c1', {'action': NodeAction.Lock.value, 'args': {'C Arm':'Arm1'}}),
        ('c2', {'action': NodeAction.Command.value, 'args': ['Arm1', 'moveto', 'HamStation']}),
        ('c3', {'action': NodeAction.Command.value, 'args': ['Arm1', 'grab']}),
        ('c5', {'action': NodeAction.Command.value, 'args': ['Arm1', 'moveto', 'BuildStation']}),
        ('c6', {'action': NodeAction.Command.value, 'args': ['Arm1', 'release']}),
        ('c7', {'action': NodeAction.Command.value, 'args': ['Arm1', 'moveto', 'HomeStation']}),
        ('c9', {'action': NodeAction.Unlock.value, 'args': {'C Arm':'Arm1'}}),

        ('d1', {'action': NodeAction.Lock.value, 'args': {'D Arm':'Arm2'}}),
        ('d2', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'CheeseStation']}),
        ('d3', {'action': NodeAction.Command.value, 'args': ['Arm2', 'grab']}),
        ('d5', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'BuildStation']}),
        ('d6', {'action': NodeAction.Command.value, 'args': ['Arm2', 'release']}),
        ('d7', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'HomeStation']}),
        ('d9', {'action': NodeAction.Unlock.value, 'args': {'D Arm':'Arm2'}}),

        ('e1', {'action': NodeAction.Lock.value, 'args': {'E Arm':'Arm2'}}),
        ('e2', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'BreadStation']}),
        ('e3', {'action': NodeAction.Command.value, 'args': ['Arm2', 'grab']}),
        ('e5', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'BuildStation']}),
        ('e6', {'action': NodeAction.Command.value, 'args': ['Arm2', 'release']}),
        ('e7', {'action': NodeAction.Command.value, 'args': ['Arm2', 'moveto', 'HomeStation']}),
        ('e9', {'action': NodeAction.Unlock.value, 'args': {'E Arm':'Arm2'}}),

        ('f1', {'action': NodeAction.Lock.value, 'args': {'F Arm':'Arm3'}}),
        ('f3', {'action': NodeAction.Command.value, 'args': ['Arm3', 'moveto', 'BuildStation']}),
        ('f4', {'action': NodeAction.Command.value, 'args': ['Arm3', 'grab']}),
        ('f5', {'action': NodeAction.Command.value, 'args': ['Arm3', 'moveto', 'CustomerStation']}),
        ('f7', {'action': NodeAction.Command.value, 'args': ['Arm3', 'release']}),
        ('f8', {'action': NodeAction.Command.value, 'args': ['Arm3', 'moveto', 'HomeStation']}),
        ('f9', {'action': NodeAction.Unlock.value, 'args': {'F Arm':'Arm3'}}),
    ]

    edges = [
        # ('a0', 'a1'),
        # ('b0', 'b1'),
        # ('c0', 'c1'),
        # ('d0', 'd1'),
        # ('e0', 'e1'),
        # ('f0', 'f1'),

        ('a1', 'a2'),
        ('a2', 'a3'),
        ('a3', 'a5'),
        # ('a3', 'a4'),
        # ('a4', 'a5'),
        ('a5', 'a6'),
        ('a6', 'a7'),
        ('a7', 'a9'),
        # ('a7', 'a8'),
        # ('a8', 'a9'),

        ('b1', 'b2'),
        ('b2', 'b3'),
        ('b3', 'b5'),
        # ('b3', 'b4'),
        # ('b4', 'b5'),
        ('b5', 'b6'),
        ('b6', 'b7'),
        ('b7', 'b9'),
        # ('b7', 'b8'),
        # ('b8', 'b9'),

        ('c1', 'c2'),
        ('c2', 'c3'),
        ('c3', 'c5'),
        # ('c3', 'c4'),
        # ('c4', 'c5'),
        ('c5', 'c6'),
        ('c6', 'c7'),
        ('c7', 'c9'),
        # ('c7', 'c8'),
        # ('c8', 'c9'),

        ('d1', 'd2'),
        ('d2', 'd3'),
        ('d3', 'd5'),
        # ('d3', 'd4'),
        # ('d4', 'd5'),
        ('d5', 'd6'),
        ('d6', 'd7'),
        ('d7', 'd9'),
        # ('d7', 'd8'),
        # ('d8', 'd9'),

        ('e1', 'e2'),
        ('e2', 'e3'),
        ('e3', 'e5'),
        # ('e3', 'e4'),
        # ('e4', 'e5'),
        ('e5', 'e6'),
        ('e6', 'e7'),
        ('e7', 'e9'),
        # ('e7', 'e8'),
        # ('e8', 'e9'),

        ('f1', 'f3'),
        # ('f1', 'f2'),
        # ('f2', 'f3'),
        ('f3', 'f4'),
        ('f4', 'f5'),
        ('f5', 'f7'),
        # ('f5', 'f6'),
        # ('f6', 'f7'),
        ('f7', 'f8'),
        ('f8', 'f9'),

        ('a7', 'b5'),
        ('b7', 'c5'),
        ('c7', 'd5'),
        ('d7', 'e5'),
        ('e7', 'f3'),
    ]

    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # entrypoints = set(n for n, d in G.in_degree() if d==0)
    # exitpoints = set(n for n, d in G.out_degree() if d==0)
    # G.add_node('entry', action=NodeAction.Lock.value, args=list(templs.keys()))
    # G.add_node('exit', action=NodeAction.Unlock.value, args=list(templs.keys()))
    # G.add_edges_from([('entry', node) for node in entrypoints])
    # G.add_edges_from([(node, 'exit') for node in exitpoints])

    return templs, G

def main():
    # res_hamcheese, graph_hamcheese = graph_GPT('Build a ham and cheese sandwich')
    # res_vegetarian, graph_vegetarian = graph_GPT('Build a lettuce, tomato, and avocado sandwich')
    res_hamcheese, graph_hamcheese = custom_graph()

    job_id_hamcheese = submit(res_hamcheese, graph_hamcheese)
    # print('Received job id:', job_id_hamcheese)

    # jobid_vegetarian = submit(graph_vegetarian)
    # print('Received job id:', job_id_hamcheese)



    # cm = {
    #     NodeAction.Lock.value: 'red',
    #     NodeAction.Unlock.value: 'green',
    #     NodeAction.Sleep.value: 'gray',
    #     NodeAction.Command.value: 'blue',
    # }
    # pos = nx.nx_agraph.graphviz_layout(graph_hamcheese, prog='dot')
    # color_map = [cm.get(d['action'], 'yellow') for (n,d) in graph_hamcheese.nodes(data=True)]

    # plt.figure(figsize=(8, 6))
    # nx.draw(graph_hamcheese, pos, with_labels=True, font_size=5, arrowsize=8, node_size=150, node_color=color_map)
    # plt.show()

if __name__ == '__main__':
    main()
