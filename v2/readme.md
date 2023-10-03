# Version 2
This version focused on improving the capabilities of the Engine (previously named server) by adding resource management.

Developed between June 30th 2023 - July 5th 2023.

Video of results here:
https://people.cs.uchicago.edu/~rorymb/videos/sandwich2.mp4

I heavily suggest skipping this version and looking at Version 3 instead. I had not fully worked out how best to organize pieces when writing this version.

## engine.py
Here, logic has been divided into threads for agents (robots), clients, and graph nodes. Additionally, physical lab resources have been defined as mutex-like objects, and must be locked/unlocked before use to allow separate graphs to run simultaneously without conflict.

## agent.py
Dummy script for testing. Communicates like a robot, but just sleeps.

## client1.py & client2.py
Graph submission scripts using the nodes.txt & edges.txt files, or with a runtime-defined graph.

## utils.py
Various enums, typedefs, etc.

## nodes.txt & edges.txt
From Version 1. Contains saved output from our gpt1.py & gpt2.py runs.
