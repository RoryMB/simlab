import logging
import pickle
import time
import uuid
from threading import Event, Lock, Thread

import networkx as nx
import zmq
from utils import (S_CLI_ADDR, S_DSH_ADDR, S_LAB_ADDR, Command, Flags, Job,
                   JobID, KeyedLock, Node, NodeFlags, Resource, ResourceAlias,
                   ResourceID, ZMQAddr, configure_logger, find_linked_nodes,
                   match_alias_to_resources)

context = zmq.Context()
logger = logging.getLogger('simlab')
configure_logger(logger)

# SLEEP_BEAT = 10.00 # How often to heartbeat
# SLEEP_DASH =  1.00 # How often to publish engine details
# SLEEP_SPIN =  0.50 # How often to check if threads are alive
# SLEEP_LOCK =  0.10 # How often to retry a lock
# SLEEP_TICK =  0.01 # How often to check the graph for new things to do

SLEEP_BEAT = 60.00 # How often to heartbeat
SLEEP_DASH =  5.00 # How often to publish engine details
SLEEP_SPIN =  5.00 # How often to check if threads are alive
SLEEP_LOCK =  1.00 # How often to retry a lock
SLEEP_TICK =  0.25 # How often to check the graph for new things to do

class Engine:
    # Rules for the Engine:

    # All operations on Engine data must be done while holding self._lock
    # While self._lock is held, do not call other Engine functions

    # Resources/Jobs may not be passed in or out, only IDs
    # The ONLY exceptions are self.add_job() and self.add_resource()

    def __init__(self) -> None:
        logger.info(f'Engine booting up')

        self.graph = nx.DiGraph()
        self.jobs: dict[JobID, Job] = {}
        self.resources: dict[ResourceID, Resource] = {}
        self.resource_locks: set[ResourceID] = set()

        self._lock = Lock()

        # TEMPORARY
        for i in range(1):
            r = Resource(features={
                'variant': 'group',
                'name': str(i),
            })
            self.add_resource(r)

        self.threads = [
            Thread(target=thread_graph_ticker, name='Main-GraphTicker', args=(self,)),
            Thread(target=thread_client_server, name='Main-ClientServer', args=(self,)),
            Thread(target=thread_lab_server, name='Main-LabServer', args=(self,)),
            Thread(target=thread_data_stream, name='Main-DataStream', args=(self,)),
        ]
        for thread in self.threads:
            thread.daemon = True
            thread.start()

    def spin(self):
        """Sit and make sure all threads are working"""

        try:
            while True:
                for thr in self.threads:
                    if not thr.is_alive():
                        logger.info(f'Engine shutting down: thread "{thr.name}" was dead')
                        assert False
                time.sleep(SLEEP_SPIN)
        except KeyboardInterrupt:
            logger.info(f'Engine shutting down: KeyboardInterrupt')

    def tick_graph(self) -> None:
        """Check the graph for anything new to do"""

        with self._lock:
            nodes: list[Node] = [n for n,d in self.graph.in_degree if d==0]

            for node in nodes:
                assert node._state != NodeFlags.Failed

                if node._state == NodeFlags.Ready:
                    logger.debug(f'Engine starting node {node.name}|{node._id}')
                    node._state = NodeFlags.Running
                    thread = Thread(
                        target=thread_node,
                        name=('Node ' + str(node._id)[:8] + ' ' + node.name[:6]),
                        args=(self, node),
                    )
                    thread.daemon = True
                    thread.start()

                if node._state == NodeFlags.Done:
                    logger.debug(f'Engine deleting node {node.name}|{node._id}')
                    self.graph.remove_node(node)

            for job_id, job in list(self.jobs.items()):
                for node in job.graph.nodes:
                    if node in self.graph:
                        break
                else:
                    logger.info(f'Engine found completed job {job_id}')
                    # TODO: Save out final job/node data here
                    self.jobs.pop(job_id)

    def get_details(self) -> bytes:
        with self._lock:
            resources = []
            for res in self.resources.values():
                resources.append(res.copy(keep_id=True, keep_unserializable=False))

            details = [
                self.graph,
                self.jobs,
                resources,
                self.resource_locks,
            ]

            return pickle.dumps(details)

    def add_job(self, job: Job) -> JobID:
        """Adds a Job to the Engine and ensures Nodes are well-formatted"""

        with self._lock:
            assert all(alias._assigned is None for alias in job.aliases)

            current_ids = set(n._id for n in self.graph.nodes)
            for node in job.graph.nodes:
                assert isinstance(node, Node)
                assert node._state is NodeFlags.Ready
                assert node._result is None
                assert node._id not in current_ids

            job._id = uuid.uuid4()
            self.jobs[job._id] = job

            self.graph.update(job.graph)

            logger.info(f'Engine added job {job._id}')

            return job._id

    def add_resource(self, resource: Resource) -> None:
        """Adds a Resource to the Engine and sets up internal resource state"""

        with self._lock:
            if resource._id in self.resources:
                logger.debug(f'Engine already had resource {resource._id}')
                return

            self.resources[resource._id] = resource

            logger.info(f'Engine added resource {resource._id}')

            if resource.features.get('variant') == 'agent':
                addr_external = resource.features['addr_external']
                logger.debug(f'Engine added resource - Agent at {addr_external}')

                resource._event_agent_down = Event()
                resource._addr_internal = f'inproc://agents/{resource._id}'

                name = 'Agent ' + str(resource._id)[:8]
                if 'name' in resource.features:
                    name += ' ' + resource.features['name'][:6]

                thread = Thread(
                    target=thread_agent,
                    name=name,
                    args=(resource._event_agent_down, resource._addr_internal, addr_external)
                )
                thread.daemon = True
                thread.start()

    def remove_resource(self, resource: Resource) -> None:
        """Removes a Resource from the Engine"""

        with self._lock:
            if resource._id not in self.resources:
                logger.warning(f'Engine tried to remove nonexistant resource {resource._id}')
                return

            # Replace the given resource with ours so we can shut down internal state
            resource = self.resources.pop(resource._id)
            logger.info(f'Engine removed resource {resource._id}')

            if resource.features.get('variant') == 'agent':
                assert resource._event_agent_down
                resource._event_agent_down.set()

    def lock_node(self, node: Node) -> bool:
        """Locks all ResourceAliases requested by a Node (and potentially others, to avoid deadlock)"""

        with self._lock:
            locking_graph = nx.Graph()

            # Find all available resources
            unlocked_resources: list[Resource] = []
            for res_id, res in self.resources.items():
                if res_id not in self.resource_locks:
                    unlocked_resources.append(res)
                    locking_graph.add_node(res, bipartite=0)

            # Find all aliases this node depends on (plus others that could cause deadlock)
            sources: list[Node] = []
            aliases: list[KeyedLock] = []
            nodes = find_linked_nodes(self.graph, node) | set([node])
            for n in nodes:
                sources.extend([n] * len(n.locks))
                aliases.extend(n.locks)

            logger.debug(f'Engine locking {len(aliases)} aliases across {len(nodes)} nodes for node {node.name}|{node._id}')

            # If an alias is needed more than once (e.g. in multiple nodes), fail
            if len(aliases) != len(set(lk[0] for lk in aliases)):
                logger.debug(f'Engine needed a resource more than once to lock node {node.name}|{node._id}')
                return False

            # Pair all aliases with possible resource matches
            for i, (alias, _) in enumerate(aliases):
                locking_graph.add_node(i, bipartite=1)
                if alias._assigned:
                    res = self.resources[alias._assigned]
                    if res not in unlocked_resources:
                        logger.debug(f'Engine needed preassigned alias resource that was locked for node {node.name}|{node._id}')
                        return False
                    locking_graph.add_edge(i, res)
                else:
                    for res in match_alias_to_resources(alias, unlocked_resources, self.resources):
                        locking_graph.add_edge(i, res)

            top = {n for n,d in locking_graph.nodes(data=True) if d['bipartite'] == 0}
            matches = nx.bipartite.maximum_matching(locking_graph, top)

            # If ANYONE couldn't lock, we risk a deadlock
            for i, _ in enumerate(aliases):
                if i not in matches:
                    logger.debug(f'Engine could not find a lock match for all resources for node {node.name}|{node._id}')
                    return False

            # Acquire all locks
            for i, ((alias, key), source) in enumerate(zip(aliases, sources)):
                res: Resource = matches[i]
                if alias._assigned:
                    assert res == self.resources[alias._assigned]
                else:
                    alias._assigned = res._id
                self.resource_locks.add(res._id)
                logger.debug(f'Engine locked resource {res._id}')
                # We may preempt locks from other nodes
                source.locks.remove((alias, key))

            assert len(node.locks) == 0

            logger.debug(f'Engine locked node {node.name}|{node._id}')
            return True

    def unlock_node(self, node: Node) -> None:
        """Unlocks all resources requested by a Node"""

        with self._lock:
            logger.debug(f'Engine unlocking {len(node.unlocks)} aliases for node {node.name}|{node._id}')

            for (alias, key) in node.unlocks:
                rID = alias._assigned
                assert rID
                assert rID in self.resources
                assert rID in self.resource_locks
                self.resource_locks.remove(rID)
                logger.debug(f'Engine unlocked resource {rID}')

            logger.debug(f'Engine unlocked node {node.name}|{node._id}')

    def solve_command(self, command: Command) -> tuple[ZMQAddr, bytes]:
        """Converts a Command into the agent's internal ZMQAddress and the message"""

        with self._lock:
            rID = command.agent._assigned
            assert rID
            assert rID in self.resource_locks, 'Tried to use unlocked resource'

            resource = self.resources[rID]
            assert resource.features.get('variant') == 'agent'
            assert resource._addr_internal

            message = []
            for elem in command.message:
                match elem:
                    case [ResourceAlias(_assigned=alias_rID), str(feature)]:
                        assert alias_rID
                        # assert alias_rID in self.resource_locks
                        alias_resource = self.resources[alias_rID]
                        val = alias_resource.features[feature]
                        message.append(val)
                    case _:
                        message.append(elem)

            return resource._addr_internal, pickle.dumps(message)
            # return resource._addr_internal, pickle.dumps(command.message)

def thread_graph_ticker(engine: Engine):
    """Ensures the graph gets checked periodically"""

    logger.info(f'graph_ticker starting')

    while True:
        engine.tick_graph()
        time.sleep(SLEEP_TICK)

def thread_client_server(engine: Engine):
    """Handle all requests from clients"""

    logger.info(f'client_server starting')

    sock = context.socket(zmq.REP)
    sock.bind(S_CLI_ADDR)

    while True:
        msg = sock.recv_multipart()
        logger.debug(f'Thread client_server received a message')

        try:
            match msg:
                case [Flags.SUBMIT_JOB, job]:
                    reply = engine.add_job(pickle.loads(job))
                case _:
                    logger.warning(f'Thread client_server received a bad message')
                    assert False
        except Exception:
            logger.exception(f'Thread client_server encountered a problem')
            sock.send_multipart([Flags.FAILURE])
        else:
            logger.debug(f'Thread client_server replying')
            sock.send_multipart([Flags.SUCCESS, pickle.dumps(reply)])

def thread_lab_server(engine: Engine):
    """Handle all publications from the lab"""

    logger.info(f'lab_server starting')

    sock = context.socket(zmq.SUB)
    sock.bind(S_LAB_ADDR)
    sock.setsockopt(zmq.SUBSCRIBE, b'')

    while True:
        msg = sock.recv_multipart()
        logger.debug(f'Thread lab_server received a message')

        try:
            match msg:
                case [Flags.RESOURCE_UP, resource]:
                    engine.add_resource(pickle.loads(resource))
                case [Flags.RESOURCE_DN, resource]:
                    engine.remove_resource(pickle.loads(resource))
                case _:
                    logger.warning(f'Thread lab_server received a bad message')
        except Exception:
            logger.exception(f'Thread lab_server encountered a problem')

def thread_data_stream(engine: Engine):
    """Stream data out periodically"""

    logger.info(f'data_stream starting')

    sock = context.socket(zmq.PUB)
    sock.bind(S_DSH_ADDR)
    time.sleep(1)
    logger.debug(f'Thread data_stream heartbeating')
    sock.send_multipart([Flags.ENGINE_HEARTBEAT])

    while True:
        details = engine.get_details()

        logger.debug(f'Thread data_stream publishing details')
        sock.send_multipart([Flags.DASH_DETAILS, details])

        time.sleep(SLEEP_DASH)

def thread_agent(event_agent_down: Event, addr_internal: ZMQAddr, addr_external: ZMQAddr) -> None:
    """Forward all communications for an agent"""

    logger.info(f'Thread starting for agent {addr_external}')

    with context.socket(zmq.ROUTER) as sock_engine,\
         context.socket(zmq.DEALER) as sock_agent:
        sock_engine.bind(addr_internal)
        sock_agent.connect(addr_external)

        poller = zmq.Poller()
        poller.register(sock_engine, zmq.POLLIN)
        poller.register(sock_agent, zmq.POLLIN)

        while not event_agent_down.is_set():
            socks = dict(poller.poll(timeout=1000))

            if socks.get(sock_engine) == zmq.POLLIN:
                msg = sock_engine.recv_multipart()
                sock_agent.send_multipart(msg)

            if socks.get(sock_agent) == zmq.POLLIN:
                msg = sock_agent.recv_multipart()
                sock_engine.send_multipart(msg)

    logger.info(f'Thread  ending  for agent {addr_external}')

def thread_node(engine: Engine, node: Node) -> None:
    """Performs the operations of a single node"""

    logger.info(f'Thread starting for node {node.name}|{node._id}')

    try:
        if node.locks:
            logger.debug(f'Node locking ... {node.name}|{node._id}')
            while not engine.lock_node(node):
                time.sleep(SLEEP_LOCK)
            logger.debug(f'Node locking done {node.name}|{node._id}')

        if node.command:
            logger.debug(f'Node handling command ... {node.name}|{node._id}')

            addr, command_msg = engine.solve_command(node.command)

            with context.socket(zmq.REQ) as sock:
                sock.connect(addr)

                sock.send_multipart([Flags.AGENT_CMD, command_msg])
                msg = sock.recv_multipart()

            match msg:
                case [Flags.SUCCESS, result]:
                    node._result = result
                case _:
                    logger.warning(f'Node received a bad message {node.name}|{node._id}')
                    assert False

            logger.debug(f'Node handling command done {node.name}|{node._id}')

        if node.sleep:
            logger.debug(f'Node sleeping ... {node.name}|{node._id}')
            time.sleep(node.sleep)
            logger.debug(f'Node sleeping done {node.name}|{node._id}')

        if node.unlocks:
            logger.debug(f'Node unlocking ... {node.name}|{node._id}')
            engine.unlock_node(node)
            logger.debug(f'Node unlocking done {node.name}|{node._id}')

    except Exception:
        logger.exception(f'Node failed {node.name}|{node._id}')
        node._state = NodeFlags.Failed

    else:
        logger.debug(f'Node finished successfully {node.name}|{node._id}')
        node._state = NodeFlags.Done

    logger.info(f'Thread  ending  for node {node.name}|{node._id}')

def main():
    engine = Engine()
    engine.spin()

if __name__ == '__main__':
    main()
