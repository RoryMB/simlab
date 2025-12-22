#!/bin/bash
NODE_URL=http://127.0.0.1:8023/ python modules/sim_thermocycler_rest_node.py \
    --node_definition node_definitions/sim_thermocycler_1.node.yaml \
    --zmq_server tcp://localhost:5560
