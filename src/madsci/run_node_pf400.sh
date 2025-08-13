#!/bin/bash
NODE_URL=http://127.0.0.1:8020/ python modules/sim_pf400.py \
    --node_definition node_definitions/sim_pf400_1.node.yaml \
    --zmq_server tcp://localhost:5557
