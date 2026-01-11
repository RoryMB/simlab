#!/bin/bash
# Requires MADSci .env to be sourced beforehand (for server URLs)
NODE_URL=http://127.0.0.1:8023/ python ./sim_thermocycler_rest_node.py \
    --node_definition ./sim_thermocycler_1.node.yaml \
    --zmq_server tcp://localhost:5560
