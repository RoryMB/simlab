# Run from simlab/

python scripts/orchestrate.py \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_ot2.sh" \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_pf400.sh" \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_sealer.sh" \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_peeler.sh" \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_thermocycler.sh" \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_hidex.sh" \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/prism && python run_phys.py" \
    --madsci-cmd "cd src/madsci/ && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/prism && python run_workflow.py workflow.yaml" \
    --timeout 240
