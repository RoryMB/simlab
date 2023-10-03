import logging
import uuid
from enum import Enum
from threading import Event
from typing import TypeAlias

import networkx as nx


CLI_ADDR = 'tcp://localhost:5560'
LAB_ADDR = 'tcp://localhost:5561'
DSH_ADDR = 'tcp://localhost:5562'
S_CLI_ADDR = CLI_ADDR.replace('localhost', '*')
S_LAB_ADDR = LAB_ADDR.replace('localhost', '*')
S_DSH_ADDR = DSH_ADDR.replace('localhost', '*')

class Flags:
    FAILURE = b'FAILURE'
    SUCCESS = b'SUCCESS'
    SUBMIT_JOB = b'SUBMIT_JOB'
    RESOURCE_UP = b'RESOURCE_UP'
    RESOURCE_DN = b'RESOURCE_DN'
    AGENT_CMD = b'AGENT_CMD'
    DASH_DETAILS = b'DASH_DETS'
    ENGINE_HEARTBEAT = b'ENGINE_HEARTBEAT'

class NodeFlags(Enum):
    Ready = 'Ready'
    Running = 'Running'
    Failed = 'Failed'
    Done = 'Done'

ResourceID: TypeAlias = uuid.UUID

class ResourceAlias:
    def __init__(self, template: dict[str, str|tuple['ResourceAlias', str]]) -> None:
        self.template = template

        self._assigned: None|ResourceID = None

class Command:
    def __init__(self, agent: ResourceAlias, message: list[str|tuple[ResourceAlias, str]]) -> None:
        self.agent = agent
        self.message = message

KeyedLock: TypeAlias = tuple[ResourceAlias, str]

class Node:
    def __init__(
        self,
        name: str,
        locks: None|list[KeyedLock] = None,
        unlocks: None|list[KeyedLock] = None,
        command: None|Command = None,
        sleep: float = 0,
    ) -> None:
        self.name = name
        self.locks = [] if locks is None else locks
        self.unlocks = [] if unlocks is None else unlocks
        self.command = command
        self.sleep = sleep

        self._id: uuid.UUID = uuid.uuid4()
        self._state: NodeFlags = NodeFlags.Ready
        self._result: None|bytes = None

ZMQAddr: TypeAlias = str

class Resource:
    def __init__(self, features: dict[str, str]) -> None:
        self.features = features

        self._id: ResourceID = uuid.uuid4()
        self._addr_internal: None|ZMQAddr = None
        self._event_agent_down: None|Event = None

    def copy(self, keep_id: bool=True, keep_unserializable: bool=True):
        """Returns a perfect copy of the Resource, optionally regenerating id and non-serializable attributes"""

        res_new = Resource(features=self.features.copy())
        res_new._addr_internal = self._addr_internal
        if keep_id:
            res_new._id = self._id
        if keep_unserializable:
            res_new._event_agent_down = self._event_agent_down

        return res_new

JobID: TypeAlias = uuid.UUID

class Job:
    def __init__(self, aliases: list[ResourceAlias], graph: nx.DiGraph) -> None:
        self.aliases = aliases
        self.graph = graph

        self._id: JobID = uuid.uuid4()

def match_alias_to_resources(alias: ResourceAlias, matchable_resources: list[Resource], all_resources: dict[ResourceID, Resource]) -> list[Resource]:
    """Finds all resources that match the given alias"""

    matches = []

    # from pprint import pprint
    # print('----------------------------------------------------------------')
    # print('MATCHING ALIAS')
    # pprint(alias.template)
    # print()
    # print('OPTIONS')
    # pprint([r.features for r in matchable_resources])
    # print()

    for res in matchable_resources:
        # print('CHECK')
        for name, val in alias.template.items():
            if name not in res.features:
                # print('    NO NAME', name)
                break

            match val:
                case [ResourceAlias(_assigned=alias_rID), str(feature)]:
                    if not alias_rID:
                        # print('    NO ASSIGN', name)
                        break
                    # assert alias_rID in self.resource_locks
                    alias_resource = all_resources[alias_rID]
                    val = alias_resource.features[feature]

            if res.features[name] != val:
                # print(f'    BAD VAL {name}: {val}!={res.features[name]}')
                break
        else:
            # print('    FOUND MATCH')
            # pprint(res.features)
            matches.append(res)

    # print('RETURNING')
    # pprint(matches)
    return matches

def find_linked_nodes(graph: nx.DiGraph, node: Node) -> set[Node]:
    """Finds all Nodes that need to be locked alongside `node` or risk deadlock"""

    # Find downstream unlocks
    descendants: set[Node] = nx.descendants(graph, node)

    unlock_nodes: set[Node] = set()
    for keyed_lock in node.locks:
        for d_node in descendants:
            if keyed_lock in d_node.unlocks:
                unlock_nodes.add(d_node)

    # Find upstream locks
    ancestors: set[Node] = set()
    for node in unlock_nodes:
        ancestors |= nx.ancestors(graph, node)

    lock_nodes: set[Node] = set()
    for a_node in ancestors:
        if a_node.locks:
            lock_nodes.add(a_node)

    return lock_nodes

def configure_logger(logger: logging.Logger):
    class CustomFormatter(logging.Formatter):
        def __init__(self, fmt:str, datefmt=None, style='%', validate=True, *, defaults=None):
            super().__init__(fmt, datefmt, style, validate, defaults=defaults)

            self.styles = {
                logging.DEBUG:    logging.PercentStyle('\033[90m%(levelname)-8s\033[0m' + fmt),
                logging.INFO:     logging.PercentStyle('\033[34m%(levelname)-8s\033[0m' + fmt),
                logging.WARNING:  logging.PercentStyle('\033[33m%(levelname)-8s\033[0m' + fmt),
                logging.ERROR:    logging.PercentStyle('\033[91m%(levelname)-8s\033[0m' + fmt),
                logging.CRITICAL: logging.PercentStyle('\033[30;101m%(levelname)-8s\033[0m' + fmt),
            }
            self.defstyle = logging.PercentStyle('%(levelname)-8s' + fmt)

        def format(self, record):
            self._style = self.styles.get(record.levelno, self.defstyle)
            return super().format(record)

    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(f'logs/{logger.name}.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-8s %(filename)10s:%(lineno)-3d %(funcName)-22s %(threadName)-21s | %(message)s'
    ))

    gh = logging.FileHandler(f'logs/{logger.name}.color.log')
    gh.setLevel(logging.DEBUG)
    gh.setFormatter(CustomFormatter(
        ' \033[32m%(filename)10s\033[0m:%(lineno)-3d \033[96m%(funcName)-22s\033[0m \033[90m%(threadName)-21s\033[0m | %(message)s'
    ))

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(CustomFormatter(
        ' \033[32m%(filename)10s\033[0m:%(lineno)-3d \033[96m%(funcName)-22s\033[0m \033[90m%(threadName)-21s\033[0m | %(message)s'
    ))

    logger.addHandler(fh)
    logger.addHandler(gh)
    logger.addHandler(ch)
