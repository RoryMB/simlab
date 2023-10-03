import os
import openai

openai.api_key = os.environ['OPENAI_API_KEY']

system_prompt = """
Assume you have a plate and bread and cheese and ham, but no other ingredients.
They are all in stacks at a station for each, e.g. HamStation.
There is a BuildStation on which you can build the sandwich.
You have one robot (Arm1) that can retrieve the plate and ham from two stations,
and a second robot (Arm2) that can retrieve the bread and cheese from the two other stations.
A third robot (Arm3) can move the plate from the BuildStatation to a CustomerStation.
"""

user_prompt = """
What sequence of actions by the three robots will result in a ham-and-cheese sandwich
being built on the BuildStation and then moved to the CustomerStation?
Do not describe any extra steps.  Make each step atomic, so for example retrieving a
piece of ham and moving it to the plate might take six steps:
    - moveto HamStation,
    - grab  # ham,
    - moveto BuildStation,
    - release  # ham.
    - moveto HomeStation
    - clear BuildStation
Using atomic actions makes it easier to provide commands to the robots.
Any grab or release action for ArmX that is not immediately followed by "ArmX moveto"
action should have a "ArmX moveto HomeStation" placed after it, and then
"Armx clear BuildStation" if Buildstation is the current station being moved away
from.  We do not need to clear any Stations other than BuildStation.
This keeps robots from arriving simultaneously at BuildStation.
Please give the sequence of actions in this format without a dot after action number:
    11 Arm1 moveto BreadStation
"""


gpt_response = openai.ChatCompletion.create(
    model='gpt-4',
    messages=[
        {'role': 'system', 'content': system_prompt},
        {'role': 'user',   'content': user_prompt}
    ],
    stream=True,
)

full_response = ''
for response in gpt_response:
    delta = response.choices[0].delta.get('content', '')
    print(delta, end='', flush=True)
    full_response += delta
print()

with open('nodes.txt', 'w') as f:
    print(full_response, file=f)
