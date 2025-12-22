#!/bin/bash
NODE_URL=http://127.0.0.1:8021/ python modules/sim_sealer_rest_node.py \
    --node_definition node_definitions/sim_sealer_1.node.yaml \
    --zmq_server tcp://localhost:5558
