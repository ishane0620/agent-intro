import argparse
import json
from pathlib import Path

import file_agent
from agent.loop import Agent
from prompts import build_system_prompt


def plain(value):
    """Turn SDK content blocks into plain data so the message list can be printed."""
    if hasattr(value, 'model_dump'):
        return plain(value.model_dump())
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description='Read-only file searching agent.')
    parser.add_argument('root', type=Path, help='Project directory to search.')
    parser.add_argument('--system-extra', default=None, help='Extra system prompt text.')
    args = parser.parse_args()

    file_agent.ROOT = args.root.resolve()
    agent = Agent(
        tools=file_agent.TOOLS,
        tool_funcs=file_agent.TOOL_FUNCS,
        system=build_system_prompt(file_agent.ROOT, args.system_extra),
    )

    print('Ask a question. /reset clears history, /messages prints it, /exit quits.')
    while True:
        try:
            line = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line == '/exit':
            break
        if line == '/reset':
            agent.reset()
            print('messages cleared')
            continue
        if line == '/messages':
            print(json.dumps(plain(agent.messages), indent=2))
            continue
        print(agent.prompt(line))


if __name__ == '__main__':
    main()