#!/usr/bin/env bash
# Run the ESS swarm-invasion stability test (task 1.8).
cd "$(dirname "$0")/../server"
python -m pytest agora/tests/test_ess_stability.py -v --tb=short 2>&1
