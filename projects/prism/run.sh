# Run from simlab/

python tools/orchestrate.py \
    --node-cmd "set -a; source projects/prism/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/ot2/ && ./run_node_ot2.sh" \
    --node-cmd "set -a; source projects/prism/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/pf400/ && ./run_node_pf400.sh" \
    --node-cmd "set -a; source projects/prism/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/sealer/ && ./run_node_sealer.sh" \
    --node-cmd "set -a; source projects/prism/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/peeler/ && ./run_node_peeler.sh" \
    --node-cmd "set -a; source projects/prism/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/thermocycler/ && ./run_node_thermocycler.sh" \
    --node-cmd "set -a; source projects/prism/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/hidex/ && ./run_node_hidex.sh" \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/prism && python run_phys.py" \
    --madsci-cmd "cd projects/prism/madsci/ && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/prism && python run_workflow.py workflow.yaml" \
    --timeout 240
