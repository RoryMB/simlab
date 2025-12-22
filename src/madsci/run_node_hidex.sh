#!/bin/bash
NODE_URL=http://127.0.0.1:8024/ python modules/sim_hidex_rest_node.py \
    --node_definition node_definitions/sim_hidex_1.node.yaml \
    --zmq_server tcp://localhost:5561
