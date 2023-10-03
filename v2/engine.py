# TODO: Add Lock/Unlock pair links
# TODO: Agents need to report again when server comes back up
# TODO: Serialize Node/NodeInternal objects for robustness
# TODO: Detect job end
# TODO: On job end, unregister all job aliases
# TODO: Switch to ResourceTemplate based locking/aliasing
# TODO:     self.aliases[...] = ResourceTemplate & ResourceID|None
# TODO:     ResourceBundleRequest
# TODO: Thread daemons?
# TODO: Comments
# TODO: Document messaging protocol
# TODO: Organize if/elif/else/match usage
# TODO: Organize ZMQ Contexts
# TODO: Locks should later have an ID matching them with their Unlock.
# TODO:     For now, each alias should have exactly one Lock/Unlock pair.

import json
import time
import traceback
import uuid
from pprint import pprint
from threading import Event, Lock, Thread

import matplotlib.pyplot as plt
import networkx as nx
import zmq
from utils import (CLIENT_SERVER_ADDR, LAB_SERVER_ADDR, Flag, JobID,
                   NodeAction, NodeID, NodeState, ResourceAlias, ResourceID,
                   ResourceTemplate, ZMQAddress, deserialize_graph,
                   deserialize_templs)

DO_PLOTTING = True

class Resource():
    # TODO: Low: Improve
    def __init__(self, **features) -> None:
        self.features = features

def template_match(templ: ResourceTemplate, res: Resource) -> bool:
    if any(name not in res.features for name, val in templ.features.items()):
        return False

    if any(res.features[name] != val for name, val in templ.features.items()):
        return False

    return True

def find_locking_region(G: nx.DiGraph, node: NodeID) -> set[NodeID]:
    # TODO: CRIT: For find_upstream_lock, a better function would do:  locking_region = set(unlocks)

    data = G.nodes[node]

    action: NodeAction = data['action']
    locks: dict[str, ResourceAlias] = data['args']

    assert action == NodeAction.Lock

    locking_region: set[NodeID] = set((node,))
    descendants: set[NodeID] = nx.descendants(G, node)

    for key, lock in locks.items():
        # Find the downstream Unlock
        for desc in descendants:
            desc_dat = G.nodes[desc]
            if desc_dat['action'] == NodeAction.Unlock:
                if key in desc_dat['args']:
                    if desc_dat['args'][key] == lock:
                        unlock = desc
                        break
        else:
            assert False, f'Should have found an Unlock downstream for {lock}'

        ancestors: set[NodeID] = nx.ancestors(G, unlock)
        locking_region |= (descendants & ancestors)
        locking_region |= set((unlock,))

    return locking_region

def find_upstream_locks(G: nx.DiGraph, nodes: set[NodeID]) -> set[NodeID]:
    upstream_locks: set[NodeID] = set()
    ancestors: set[NodeID] = set()

    for node in nodes:
        ancestors |= nx.ancestors(G, node)

    for ancestor in ancestors:
        anc_action: NodeAction = G.nodes[ancestor]['action']
        if anc_action == NodeAction.Lock:
            upstream_locks.add(ancestor)

    return upstream_locks

class ResourceManager():
    def __init__(self) -> None:
        self.resources: dict[ResourceID, Resource] = {}
        self.aliases: dict[tuple[JobID, ResourceAlias], tuple[ResourceTemplate, ResourceID|None]] = {}
        self.locks: dict[ResourceID, JobID] = {}

        self._lock = Lock()

    def add(self, res: Resource) -> ResourceID:
        res_id = uuid.uuid4()

        print('ResourceManager adding resource:', res_id, res)

        with self._lock:
            self.resources[res_id] = res

        return res_id

    def remove(self, res_id: ResourceID) -> Resource|None:
        with self._lock:
            res = self.resources.pop(res_id, None)

        print('ResourceManager removing resource:', res_id, res)

        return res

    # FOR NOW, ONLY GraphManager.lock IS ALLOWED TO USE THIS
    def lock(self, job_id: JobID, primary: list[ResourceAlias], secondary: list[ResourceAlias]) -> tuple[list[bool], list[bool]]:
        with self._lock:
            G = nx.Graph()

            primaries = [(f'p{i}',alias) for i,alias in enumerate(primary)]
            secondaries = [(f's{i}',alias) for i,alias in enumerate(secondary)]

            unlocked_ids = self.resources.keys() - self.locks.keys()
            for unlocked_id in unlocked_ids:
                G.add_node(unlocked_id, bipartite=1)

            for gid, alias in primaries + secondaries:
                G.add_node(gid, alias=alias, bipartite=0)
                templ, ID = self.aliases[(job_id, alias)]

                if ID:
                    assert template_match(templ, self.resources[ID]), f'ResourceManager an [alias {alias}] failed a match to an already assigned ID???'

                    if ID in self.locks:
                        print(f'ResourceManager [alias {alias}] an assigned [ID {ID}] was already locked')
                        return [], []

                    G.add_edge(gid, ID)
                    continue

                for unlocked_id in unlocked_ids:
                    if template_match(templ, self.resources[unlocked_id]):
                        G.add_edge(gid, unlocked_id)

            top = {n for n, d in G.nodes(data=True) if d['bipartite'] == 0}
            gmatch = nx.bipartite.maximum_matching(G, top)

            print('ResourceManager nodes', G.nodes)
            print('ResourceManager edges', G.edges)
            print('ResourceManager match', gmatch)

            # BEFORE LOCKING - Make sure bundle is lockable
            for gid, alias in primaries + secondaries:
                templ, ID = self.aliases[(job_id, alias)]

                if gid not in gmatch:
                    print(f'ResourceManager [alias {alias}] a request had no match')
                    return [], []

            # Must get all primary locks
            primaries_acquired = [False] * len(primary)
            for i, (gid, alias) in enumerate(primaries):
                templ, ID = self.aliases[(job_id, alias)]

                if ID:
                    assert gid in gmatch
                    assert ID == gmatch[gid]
                    print(f'ResourceManager [alias {alias}] already had {ID}')
                    self.locks[ID] = job_id
                    primaries_acquired[i] = True

                else:
                    assert gid in gmatch
                    new_ID = gmatch[gid]
                    print(f'ResourceManager [alias {alias}] got assigned {new_ID}')
                    self.aliases[(job_id, alias)] = (templ, new_ID)
                    self.locks[new_ID] = job_id
                    primaries_acquired[i] = True

            # Must get all secondary locks that had only 1 possible match
            # TODO: CRIT: 1 possible match is the wrong constraint
            #        Fix: `all edges from gid point to a resource that was used`
            secondaries_acquired = [False] * len(secondary)
            for i, (gid, alias) in enumerate(secondaries):
                templ, ID = self.aliases[(job_id, alias)]

                # Aliases with already assigned IDs count as "only 1 possible match"
                if ID:
                    assert gid in gmatch
                    assert ID == gmatch[gid]
                    print(f'ResourceManager [alias {alias}] already had {ID}')
                    self.locks[ID] = job_id
                    secondaries_acquired[i] = True

                # Find other secondaries with only 1 possible match
                elif len(G.edges(gid)) == 1:
                    assert gid in gmatch
                    new_ID = gmatch[gid]
                    print(f'ResourceManager [alias {alias}] got assigned {new_ID}')
                    self.aliases[(job_id, alias)] = (templ, new_ID)
                    self.locks[new_ID] = job_id
                    secondaries_acquired[i] = True

        return primaries_acquired, secondaries_acquired

    # FOR NOW, ONLY GraphManager.unlock IS ALLOWED TO USE THIS
    def unlock(self, job_id: JobID, aliases: list[ResourceAlias]) -> bool:
        with self._lock:
            res_ids = [self.aliases[(job_id, alias)] for alias in aliases]

            for templ, res_id in res_ids:
                if res_id not in self.locks.keys():
                    return False

            for templ, res_id in res_ids:
                assert res_id, 'ResourceManager tried to unlock "None"???'
                self.locks.pop(res_id)

        return True

    def is_locked(self, job_id: JobID, alias: ResourceAlias) -> bool:
        with self._lock:
            _, res_id = self.aliases[job_id, alias]

            if res_id is None:
                return False

            if self.locks.get(res_id) != job_id:
                return False

        return True

    def register_alias(self, job_id: JobID, alias: ResourceAlias, templ: ResourceTemplate) -> None:
        with self._lock:
            self.aliases[(job_id, alias)] = (templ, None)

    def unregister_alias(self, job_id: JobID, alias: ResourceAlias) -> None:
        with self._lock:
            self.aliases.pop((job_id, alias))

    def get_aliased(self, job_id: JobID, alias: ResourceAlias) -> tuple[ResourceTemplate, ResourceID|None]:
        with self._lock:
            return self.aliases[(job_id, alias)]

class LabManager():
    def __init__(self, resource_manager: ResourceManager) -> None:
        self.resource_manager = resource_manager
        self.agent_data: dict[ResourceID, tuple[Thread, Event, ZMQAddress, ZMQAddress]] = {}

        self._lock = Lock()

    def add_agent(self, addr_external: ZMQAddress, agent_details: dict):
        print('LabManager adding agent:', addr_external, agent_details)

        with self._lock:
            for _, (_, _, _, addr) in list(self.agent_data.items()):
                if addr == addr_external:
                    return

        res_id = self.resource_manager.add(Resource(**agent_details))
        addr_internal = f'inproc://agents/{res_id}'
        shutdown_event = Event()

        thr = Thread(target=agent_thread, args=(addr_internal, addr_external, shutdown_event))
        thr.start()

        with self._lock:
            self.agent_data[res_id] = (thr, shutdown_event, addr_internal, addr_external)

    def remove_agent(self, addr_external: ZMQAddress):
        print('LabManager removing agent:', addr_external)

        with self._lock:
            l = list(self.agent_data.items())

        for _, (_, shutdown_event, _, addr) in l:
            if addr == addr_external:
                shutdown_event.set()

    def clean_dead_agents(self):
        with self._lock:
            l = list(self.agent_data.items())

        for res_id, (thr, _, _, _) in l:
            if not thr.is_alive():
                self.resource_manager.remove(res_id)

                with self._lock:
                    self.agent_data.pop(res_id)

    def get_proxy_addr(self, res_id: ResourceID) -> ZMQAddress:
        with self._lock:
            addr = self.agent_data[res_id][2]

        return addr

    def shutdown(self) -> None:
        print('LabManager shutdown')

        with self._lock:
            l = list(self.agent_data.items())

        for _, (_, shutdown_event, _, _) in l:
            shutdown_event.set()

class GraphManager():
    def __init__(self, resource_manager: ResourceManager, lab_manager: LabManager) -> None:
        self.resource_manager = resource_manager
        self.lab_manager = lab_manager
        self.graph = nx.DiGraph()

        self._lock = Lock()

    ##
    def tick(self) -> None:
        with self._lock:
            for node, data in list(self.graph.nodes.data()):
                # Check for in_degree==0 since lock nodes can acquire early if another lock helps them
                if data['state'] is NodeState.Done and self.graph.in_degree(node) == 0:
                    print('GraphManager node finished:', data['user_defined_name'], node, data)
                    self.graph.remove_node(node)

            for node, data in self.graph.nodes.data():
                if data['state'] is NodeState.Ready and self.graph.in_degree(node) == 0:
                    print('GraphManager starting node:', data['user_defined_name'], node, data)
                    data['state'] = NodeState.Running

                    thread = Thread(target=node_thread, args=(node, self, self.lab_manager, self.resource_manager))
                    thread.daemon = True
                    thread.start()

            if DO_PLOTTING:
                cm = {
                    NodeAction.Lock: 'red',
                    NodeAction.Unlock: 'green',
                    NodeAction.Sleep: 'gray',
                    NodeAction.Command: 'blue',
                }
                pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
                node_color = [cm.get(d['action'], 'yellow') for (n,d) in self.graph.nodes(data=True)]
                labeldict = {n:d['args'] for (n,d) in self.graph.nodes(data=True)}
                plt.clf()
                nx.draw(self.graph, pos, labels=labeldict, with_labels=True, node_color=node_color, font_size=5, arrowsize=10, node_size=200)
                plt.pause(0.01)

    def lock(self, node: NodeID):
        while True:
            with self._lock:
                data = self.graph.nodes[node]

                action: NodeAction = data['action']
                job_id: JobID = data['job_id']
                args: dict[str, ResourceAlias] = data['args']
                name = data['user_defined_name']

                assert action == NodeAction.Lock

                if not(data['args']):
                    print(f'GraphManager {name} another lock must have gotten this one for us')
                    return

                locking_region = find_locking_region(self.graph, node)
                upstream_locks = find_upstream_locks(self.graph, locking_region)
                upstream_locks -= set((node,))
                upstream_locks = list(upstream_locks)

                primaries: list[ResourceAlias] = list(args.values())
                secondaries: list[ResourceAlias] = []
                secondaries_key: list[str] = []
                secondaries_src: list[NodeID] = []
                for n in upstream_locks:
                    for k,v in self.graph.nodes[n]['args'].items():
                        secondaries.append(v)
                        secondaries_key.append(k)
                        secondaries_src.append(n)

                print(f'GraphManager {name} lock {primaries} {secondaries}')
                # for n in locking_region:
                #     print(f'    GManager {name} region', ' '.join(self.graph.nodes[n]['args']))
                # for n in upstream_locks:
                #     print(f'    GManager {name} upstrm', ' '.join(self.graph.nodes[n]['args']))

                primaries_acquired, secondaries_acquired = self.resource_manager.lock(job_id, primaries, secondaries)
                if primaries_acquired:
                    print(f'GraphManager {name} got locks {primaries_acquired} {secondaries_acquired}')
                    # for alias, acq in zip(primaries, primaries_acquired):
                    #     print(f'    GManager {name} {"+" if acq else "-"} primary {alias}')
                    # for alias, acq in zip(secondaries, secondaries_acquired):
                    #     print(f'    GManager {name} {"+" if acq else "-"} secondary {alias}')

                    assert all(primaries_acquired)

                    # TODO: This is bit hacky. Find a better way.
                    for key, locked_node, acq in zip(secondaries_key, secondaries_src, secondaries_acquired):
                        if acq:
                            self.graph.nodes[locked_node]['args'].pop(key)

                    break

            assert len(secondaries_acquired) == 0
            print(f'GraphManager {name} lock failed, trying again...')
            time.sleep(1)

    def unlock(self, node: NodeID):
        with self._lock:
            data = self.graph.nodes[node]

            action: NodeAction = data['action']
            job_id: JobID = data['job_id']
            args: dict[str, ResourceAlias] = data['args']

            assert action == NodeAction.Unlock

            self.resource_manager.unlock(job_id, list(args.values()))

    # TODO: Add entrypoint node to link a job to an existing
    # TODO: Add exitpoint node to tell when a job is done
    def add(self, templs: dict[ResourceAlias, ResourceTemplate], G: nx.DiGraph) -> JobID|None:
        job_id = uuid.uuid4()

        for node, data in G.nodes.data():
            data['action'] = NodeAction(data['action'])
            data['args'] # For now this ensures ('args' in data). Later may want to change.
            data['job_id'] = job_id
            data['state']  = NodeState.Ready
            data['result'] = None
            data['user_defined_name'] = node

        mapping = {n:uuid.uuid4() for n in G.nodes}
        G = nx.relabel_nodes(G, mapping)

        pprint(('GraphManager add', mapping))

        for alias, templ in templs.items():
            self.resource_manager.register_alias(job_id, alias, templ)

        with self._lock:
            self.graph.update(G)

        return job_id

def client_server_thread(graph_manager: GraphManager, shutdown_event: Event):
    print(f'client_server_thread starting')

    with context.socket(zmq.REP) as sock:
        sock.bind(CLIENT_SERVER_ADDR)
        sock.setsockopt(zmq.RCVTIMEO, 100)

        while not shutdown_event.is_set():
            try:
                flag, *msg = sock.recv_multipart()
                print('client_server_thread rcvd:', flag, *msg)
            except zmq.error.Again:
                continue
            except ValueError:
                sock.send_multipart([Flag.FAILURE.value.encode(), b'Bad msg format'])
                continue

            if flag == Flag.CLI_GSUB.value.encode():
                try:
                    templs, G = msg
                except ValueError:
                    sock.send_multipart([Flag.FAILURE.value.encode(), b'Bad msg format'])
                    continue

                job_id = graph_manager.add(
                    deserialize_templs(templs.decode()),
                    deserialize_graph(G.decode()),
                )

                if job_id:
                    sock.send_multipart([Flag.SUCCESS.value.encode(), str(job_id).encode()])
                    continue
                else:
                    sock.send_multipart([Flag.FAILURE.value.encode(), b'Failed graph add'])
                    continue

            else:
                sock.send_multipart([Flag.FAILURE.value.encode(), b'Bad req type'])
                continue

##
def lab_server_thread(lab_manager: LabManager, shutdown_event: Event):
    print(f'lab_server_thread starting')

    with context.socket(zmq.SUB) as sock:
        sock.bind(LAB_SERVER_ADDR)
        sock.setsockopt(zmq.SUBSCRIBE, Flag.HELLO.value.encode())
        sock.setsockopt(zmq.SUBSCRIBE, Flag.GOODBYE.value.encode())
        sock.setsockopt(zmq.RCVTIMEO, 100)

        while not shutdown_event.is_set():
            try:
                flag, addr, *msg = sock.recv_multipart()
                print('lab_server_thread rcvd:', flag, addr, *msg)
            except zmq.error.Again:
                continue
            except ValueError:
                continue

            if flag == Flag.HELLO.value.encode():
                lab_manager.add_agent(addr.decode(), json.loads(msg[0].decode()))
            elif flag == Flag.GOODBYE.value.encode():
                lab_manager.remove_agent(addr.decode())

##
def agent_thread(addr_internal: ZMQAddress, addr_external: ZMQAddress, shutdown_event: Event):
    print(f'agent_thread [{addr_internal}] [{addr_external}] starting')

    with context.socket(zmq.ROUTER) as sock_internal,\
         context.socket(zmq.DEALER) as sock_external:
        sock_internal.bind(addr_internal)
        sock_external.connect(addr_external)

        poller = zmq.Poller()
        poller.register(sock_internal, zmq.POLLIN)
        poller.register(sock_external, zmq.POLLIN)

        while not shutdown_event.is_set():
            socks = dict(poller.poll())

            if socks.get(sock_internal) == zmq.POLLIN:
                message = sock_internal.recv_multipart()
                print(f'agent_thread [{addr_internal}] -> [{addr_external}]:', message)
                sock_external.send_multipart(message)

            if socks.get(sock_external) == zmq.POLLIN:
                message = sock_external.recv_multipart()
                print(f'agent_thread [{addr_internal}] <- [{addr_external}]:', message)
                sock_internal.send_multipart(message)

# TODO: Remove: with graph_manager._lock:
def node_thread(node: NodeID, graph_manager: GraphManager, lab_manager: LabManager, resource_manager: ResourceManager):
    print(f'node_thread [{node}] starting')

    with graph_manager._lock:
        data = graph_manager.graph.nodes[node]

        action: NodeAction = data['action']
        job_id: JobID = data['job_id']
        args = data['args']
        name = data['user_defined_name']

    try:
        if action == NodeAction.Lock:
            graph_manager.lock(node)

        elif action == NodeAction.Unlock:
            graph_manager.unlock(node)

        elif action == NodeAction.Sleep:
            time.sleep(float(args[0]))

        elif action == NodeAction.Command:
            # TODO: Add graph checks so this can't happen
            assert resource_manager.is_locked(job_id, args[0]), 'Tried to use unlocked resource'
            templ, res_id = resource_manager.get_aliased(job_id, args[0])

            assert res_id # Above assertion will fail first. This just appeases Pylance.
            addr = lab_manager.get_proxy_addr(res_id)

            with context.socket(zmq.REQ) as sock:
                sock.connect(addr)

                # TODO: Handle timeouts? As part of commands?
                # msg = [m.encode() for m in args[1:]]
                msg = json.dumps({
                    "action_handle": args[1], # str
                    "action_vars": {f'arg{i}':a for i,a in enumerate(args[2:])}, # dict
                }).encode()
                print(f'node_thread {name} {node} [{action}, {args}] send:', msg)
                sock.send(msg)

                msg = sock.recv()
                msg = json.loads(msg.decode())
                print(f'node_thread {name} {node} [{action}, {args}] recv:', msg)

            with graph_manager._lock:
                graph_manager.graph.nodes[node]['result'] = msg

        else:
            with graph_manager._lock:
                graph_manager.graph.nodes[node]['state'] = NodeState.Fail
            return

    except Exception as e:
        print(f'node_thread [{action}, {args}] exception {traceback.format_exc()}')
        with graph_manager._lock:
            graph_manager.graph.nodes[node]['state'] = NodeState.Fail
        return

    with graph_manager._lock:
        graph_manager.graph.nodes[node]['state'] = NodeState.Done

class Engine():
    def __init__(self) -> None:
        self.resource_manager = ResourceManager()
        self.lab_manager = LabManager(self.resource_manager)
        self.graph_manager = GraphManager(self.resource_manager, self.lab_manager)

        self.shutdown_event = Event()

        self.client_server_thread = Thread(target=client_server_thread, args=(self.graph_manager, self.shutdown_event))
        self.client_server_thread.start()

        self.lab_server_thread = Thread(target=lab_server_thread, args=(self.lab_manager, self.shutdown_event))
        self.lab_server_thread.start()

    ##
    # TODO: Reboot dead threads?
    def tick(self) -> None:
        self.graph_manager.tick()
        self.lab_manager.clean_dead_agents()
        assert self.client_server_thread.is_alive()
        assert self.lab_server_thread.is_alive()

    ##
    def __enter__(self):
        return self

    ##
    # TODO: Low: context.term() ?
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.shutdown_event.set()
        self.lab_manager.shutdown()
        self.client_server_thread.join()
        self.lab_server_thread.join()

context = zmq.Context()

def main():
    if DO_PLOTTING:
        plt.ion()
    with Engine() as engine:
        while True:
            engine.tick()

if __name__ == '__main__':
    main()
