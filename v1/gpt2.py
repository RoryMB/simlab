import os
import openai

openai.api_key = os.environ['OPENAI_API_KEY']

lines = ''
with open('nodes.txt') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if not line[0].isdigit():
            continue
        line = line.replace('.', '')
        idx = line.find('#')
        if idx >= 0:
            line = line[0:idx].strip()
        lines += line + '\n'

system_prompt = """
    For a set of Arms and Stations, we are given this set of actions:
"""
system_prompt += lines

user_prompt = """
    The action ID is the first field in each line.
    We will think of each action as a node in graph represented by its action id.
    Create a set of edges between the nodes that follow these criteria:
        - all actions for a single Arm must remain in order.
    Print just the set of edges with just the two action numbers for an edge on a line, e.g.:
        6   9
"""

gpt_response = openai.ChatCompletion.create(
    model='gpt-4',
    temperature=0.11,
    messages=[
        {'role': 'system',    'content': system_prompt},
        {'role': 'user',      'content': user_prompt}
    ]
)
response = gpt_response['choices'][0]['message']['content']
print(response)
print()


user_prompt = """
    The ID is the first field in each line.
    Consider only lines including "clear BuildStation" or "moveto BuildStation".
    For all "clear BuildStation" lines, find the next "moveto BuildStation" line
    in the list, then print that pair of IDs.
    Print only this set of pairs as lines of the form "1 2".
"""

gpt_response = openai.ChatCompletion.create(
    model='gpt-4',
    temperature=0.11,
    messages=[
        {'role': 'system',    'content': system_prompt},
        {'role': 'user',      'content': user_prompt}
    ]
)
response = gpt_response['choices'][0]['message']['content']
print(response)
