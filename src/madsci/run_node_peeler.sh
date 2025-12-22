#!/bin/bash
NODE_URL=http://127.0.0.1:8022/ python modules/sim_peeler_rest_node.py \
    --node_definition node_definitions/sim_peeler_1.node.yaml \
    --zmq_server tcp://localhost:5559
