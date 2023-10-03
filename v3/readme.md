# Version 3
This version focused on organizing the Engine and scaling to larger simulations with many more robots.

Developed between July 6th 2023 - July 28th, 2023.

Video of results here:
https://people.cs.uchicago.edu/~rorymb/videos/sandwich3.mp4

WARNING: THESE SCRIPTS UNPICKLE DATA FROM CONNECTED SOCKETS! THERE ARE **NO** SECURITY CHECKS! ONLY RUN ON TRUSTED NETWORKS!

## engine.py
Centralized laboratory control logic. Delegates responsibility to threads handling: graph nodes, agents, lab connections, clients, dashboard streams, etc. Includes logic to handle adding and removing resources & agents on the fly. Improves logging for debugging.

Note: Around line 50 you can define how many robot groups your lab contains. Support for more complex resource requests is planned for a future version, which will eliminate the need for hardcoding these values.

## robot.py
Robot control script used in Omniverse. Attach with a Python Scripting property.

## client.py
Submits a graph to run a collection of robots through simple motions. For the video above this script was run several times as the video played, and the engine routed each submission to a different collection of robots in the lab.

## client_sandwich.py
Submits a graph to run the sandwich experiment from Version 1.

## Streamlit.py
Streamlit dashboard as shown in the video above. Shows the overall graph state, each job's graph state, and all resources.

## utils.py
Common data structures for the sake of pickling.

# Notes
The files are much larger for these scenes. I am investigating file hosting solutions, but it is not currently a priority.

You may need to increase your file descriptor limit to run this example at scale.

On macOS, I found success with `sudo launchctl limit maxfiles unlimited`

Strangely, values lower than `unlimited` make macOS whine about System Integrity Protection.
