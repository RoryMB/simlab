#!/bin/bash
docker rm -f workcell_manager experiment_manager data_manager lab_manager resource_manager event_manager redis mongodb postgres
docker compose down --remove-orphans
docker compose up
