# Version 1
This version focuses on laying the groundwork.

Developed between June 2nd 2023 - June 7th 2023.

Videos of results here:
https://people.cs.uchicago.edu/~rorymb/videos/sandwich1.mp4
https://people.cs.uchicago.edu/~rorymb/videos/sandwich1_gpt.mp4
https://people.cs.uchicago.edu/~rorymb/videos/sandwich1_gpt_vo.mp4

## server.py
This script controls the main logic. It defines network connections to the 3 simulated arms, loads an experiment graph from disk (nodes.txt, edges.txt), and executes the graph.

## robot.py
Robot control script used in Omniverse. Attach with a Python Scripting property.

## robot_dummy.py
Dummy script for testing. Communicates like a robot, but just sleeps for 5 seconds.

## gpt1.py & gpt2.py
Scripts we used to generate actions and action relationships with GPT-4.

## nodes.txt & edges.txt
Contains saved output from our gpt1.py & gpt2.py runs.

## setup.usda & ur5e_suction.usda
The setup.usda file defines the scene with robots and sandwich materials. It references ur5e_suction.usda, which might not work out-of-the-box. Simply edit setup.usda with a text editor, and change all instances of `@file:./ur5e_suction.usda@` to `@file:/home/username/simlab/v1/ur5e_suction.usda@` or wherever you put this repo. You may also need to change `@./robot.py@`.

# Notes
While working with GPT, we found that trying to find triplets of actions that were related was too hard a task.

We ended up creating an intermediate step where GPT found pairs of actions that were related first, and created a single no-op action to represent this information.

Then, GPT was able to create a pair between the no-op action and the third related action, and complete the task successfully.
