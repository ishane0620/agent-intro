""" A minimal file-searching agent. Four parts: tool schemas, tool implementations,
a dispatcher, and the loop

    pip install anthropic 
    export ANTHROPIC_API_KEY=sk-ant-...
    python file_agent.py ./some_project "which file defines the User class?"
"""

import argparse 
import json
import os
import re
from pyexpat.errors import messages
import sys
from pathlib import Path




import anthropic
from prompts import build_system_prompt

MODEL = 'claude-sonnet-5'
ROOT = Path.cwd()

### SCHEMAS ###
# what the model is told it may ask for. Descriptions matter!
# expect: this text is the only thing telling the model when to reach for each tool. 
# Vague descriptions are the most common cause of dumb ass agents!
###

TOOLS = [
    {
        'name': f'grep_files',
        'description': (
            'Search file contents for a Python regular expression. Returns '
            'matching lines as relative/path.py:42: <line text>. '
            'Prefer grep_files over read_file when looking for a '
            'definition or a usage. Pass "." to search the whole project.' 
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'pattern': {
                    'type': 'string',
                    'description': 'Python regular expression to search for.',
                },
                'path': {
                    'type': 'string',
                    'description': 'Relative directory path to search. Defaults to ".".',
                },
                'max_results': {
                    'type': 'number',
                    'description': 'Maximum number of results to return. Defaults to 50.',
                },
            },
            'required': ['pattern'],
        },
    },
    {
        'name': 'list_files',
        'description': (
            'List files and directories under a path, relative to the project '
            'root. Use this to explore the project structure before reading '
            'anything. Pass "." for the root itself.'
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
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'venv', 'dist'}
def _is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:8192]
    except OSError:
        return True
    return b'\0' in chunk
def grep_files(pattern: str, path: str = '.', max_results: int = 50) -> str:
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return str(exc)
    target = safe_path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = []
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
            for name in filenames:
                files.append(Path(dirpath) / name)
    else:
        return f'Not found: {path}'
    matches = []
    extra = 0
    for file in files:
        if _is_binary(file):
            continue
        try:
            text = file.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        relative = file.relative_to(ROOT).as_posix()
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not regex.search(line):
                continue
            if len(matches) < max_results:
                matches.append(f'{relative}:{line_number}: {line}')
            else:
                extra += 1
    if not matches:
        return '(no matches)'
    if extra:
        matches.append(f'... {extra} more matches')
    return '\n'.join(matches)


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

TOOL_FUNCS = {
    'list_files': list_files, 
    'read_file': read_file, 
    'grep_files': grep_files,
}