#!/bin/bash
# Requires MADSci .env to be sourced beforehand (for server URLs)
NODE_URL=http://127.0.0.1:8018/ python ./sim_ur5e_rest_node.py \
    --node_definition ./sim_ur5e_1.node.yaml \
    --zmq_server tcp://localhost:5555
