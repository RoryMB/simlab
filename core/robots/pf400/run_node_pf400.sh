#!/bin/bash
set -a; source ../../madsci/config/.env; set +a
NODE_URL=http://127.0.0.1:8020/ python ./sim_pf400_rest_node.py \
    --node_definition ./sim_pf400_1.node.yaml \
    --zmq_server tcp://localhost:5557
