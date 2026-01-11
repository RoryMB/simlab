#!/bin/bash
set -a; source ../../madsci/config/.env; set +a
NODE_URL=http://127.0.0.1:8022/ python ./sim_peeler_rest_node.py \
    --node_definition ./sim_peeler_1.node.yaml \
    --zmq_server tcp://localhost:5559
