from enum import Enum
import json
from typing import TypeAlias
import uuid

import networkx as nx

CLIENT_SERVER_ADDR = 'tcp://*:5560'
LAB_SERVER_ADDR = 'tcp://*:5561'

NodeID: TypeAlias = uuid.UUID
JobID: TypeAlias = uuid.UUID
ResourceID: TypeAlias = uuid.UUID
ResourceAlias: TypeAlias = str
ZMQAddress: TypeAlias = str

class Flag(Enum):
    SRV_ID = 'SRV_ID'

    CLI_GSUB = 'CLI_GSUB'

    AGT_ANNC = 'AGT_ANNC'
    AGT_RSRC = 'AGT_RSRC'
    AGT_GRPH = 'AGT_GRPH'

    HELLO = 'HELLO'
    GOODBYE = 'GOODBYE'

    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'

class NodeAction(Enum):
    Lock = 'Lock'
    Unlock = 'Unlock'
    Sleep = 'Sleep'
    Command = 'Command'

class NodeState(Enum):
    Ready = 'Ready'
    Running = 'Running'
    Done = 'Done'
    Fail = 'Fail'

class ResourceTemplate():
    def __init__(self, **features) -> None:
        # TODO: Low: Change ResourceTemplate format
        self.features = features

def serialize_templs(templs: dict[ResourceAlias, ResourceTemplate]) -> str:
    # TODO: Low: Change ResourceTemplate format
    return json.dumps({k:v.features for k,v in templs.items()})

def deserialize_templs(s: str) -> dict[ResourceAlias, ResourceTemplate]:
    # TODO: Low: Change ResourceTemplate format
    return {k:ResourceTemplate(**v) for k,v in json.loads(s).items()}

def serialize_graph(G: nx.DiGraph) -> str:
    return json.dumps(nx.node_link_data(G))

def deserialize_graph(s: str) -> nx.DiGraph:
    return nx.node_link_graph(json.loads(s))
