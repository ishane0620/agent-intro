""" A minimal file-searching agent. Four parts: tool schemas, tool implementations,
a dispatcher, and the loop

    pip install anthropic 
    export ANTHROPIC_API_KEY=sk-ant-...
    python file_agent.py ./some_project "which file defines the User class?"
"""

import json
from pyexpat.errors import messages
import sys
from pathlib import Path

import anthropic

MODEL = 'claude-sonnet-5'
ROOT = Path.cwd()

### SCHEMAS ###
# what the model is told it may ask for. Descriptions matter!
# expect: this text is the only thing telling the model when to reach for each tool. 
# Vague descriptions are the most common cause of dumb ass agents!
###

TOOLS = [
    {
        'name': 'list_files',
        'description': (
            'List files and directories under a path, relative to the project '
            'root. Use this to explore the project structure before reading '
            'anything. Pass "." for teh root itself.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string', 'description': 'Relative directory path.'}
            },
            'required': ['path'],
        },
    },

    {
        'name': 'read_file',
        'description': (
            'Read the full text contents of a single file, relative to the '
            'project root. Use after list_files to inspect a specific file.'
        ),
        'input_schema':{
            'type': 'object',
            'properties': {
                'path': {'type': 'string', 'description': 'Relative file path.'}
            },
            'required': ['path']
        },
    },
]


### IMPLEMENTATIONS ###
# Plain functions. Nothing about it knows an LLM is going to cal it.
# Each returns a string, as a string is what goes back into the conversation the LLM can read
###


def safe_path(path: str) -> Path:
    """Refuse anything that escapes ROOT for security"""
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f'path escapes project root: {path}')
    return resolved

def list_files(path: str='.') -> str:
    target = safe_path(path)
    if not target.is_dir():
        return f'Not a directory: {path}'
    entries = sorted(
        f'{p.name}/' if p.is_dir() else p.name
        for p in target.iterdir()
        if not p.name.startswith('.')
    )
    return '\n'.join(entries) or '(empty)'

def read_file(path: str) -> str:
    target = safe_path(path)
    if not target.is_file():
        return f'Not a file: {path}'
    text = target.read_text(errors='replace')
    return text[:20_000]



### DISPATCHER

TOOL_FUNCS = {'list_files': list_files, 'read_file': read_file}

### LOOPS
def run_agent(question: str) -> str:
    client = anthropic.Anthropic()
    messages = [{'role': 'user', 'content': question}]
    while True:
        reply = client.messages.create(
            model=MODEL, max_tokens=2048, tools=TOOLS, messages=messages
        )
        messages.append({'role': 'assistant', 'content': reply.content})
        if reply.stop_reason != 'tool_use':
            return ''.join(b.text for b in reply.content if b.type=='text')
        
        results = []
        
        for block in reply.content:
            if block.type != 'tool_use':
                continue
            print(f'  -> {block.name}({json.dumps(block.input)})')
            try: 
                output = TOOL_FUNCS[block.name](**block.input)
            except Exception as exc:
                output = f'Error: {exc}'
            results.append(
                {
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': output, 
                }
            )
            
        messages.append({'role': 'user', 'content': results})
        


if __name__ == '__main__':
    ROOT = Path(sys.argv[1]).resolve()
    print(run_agent(sys.argv[2]))

