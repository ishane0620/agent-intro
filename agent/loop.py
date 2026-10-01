import json

import anthropic

MODEL = 'claude-sonnet-5'


def show_content(step: int, messages: list) -> None:
    print(f'\nSTEP {step}')
    for message in messages:
        print(f'[{message["role"]}]')
        content = message['content']
        if isinstance(content, str):
            print(content)
            continue
        for block in content:
            kind = block['type'] if isinstance(block, dict) else block.type
            if kind == 'text':
                text = block['text'] if isinstance(block, dict) else block.text
                print(text)
            elif kind == 'tool_use':
                name = block['name'] if isinstance(block, dict) else block.name
                tool_input = block['input'] if isinstance(block, dict) else block.input
                print(f'tool_use {name}({json.dumps(tool_input)})')
            elif kind == 'tool_result':
                print(block['content'])
            elif kind == 'thinking':
                thinking = block['thinking'] if isinstance(block, dict) else block.thinking
                print(thinking or '(thinking restored on the server from the signature)')
    print()
    print()


class Agent:
    def __init__(self, tools, tool_funcs, system, client=None, model=MODEL):
        self.messages = []
        self.client = client or anthropic.Anthropic()
        self.tools = tools
        self.tool_funcs = tool_funcs
        self.system = system
        self.model = model

    def reset(self) -> None:
        self.messages.clear()

    def prompt(self, user_text: str) -> str:
        self.messages.append({'role': 'user', 'content': user_text})
        step = 1
        while True:
            show_content(step, self.messages)
            reply = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system,
                tools=self.tools,
                thinking={'type': 'adaptive', 'display': 'summarized'},
                messages=self.messages,
            )
            self.messages.append({'role': 'assistant', 'content': reply.content})
            if reply.stop_reason != 'tool_use':
                return ''.join(b.text for b in reply.content if b.type == 'text')

            results = []
            for block in reply.content:
                if block.type != 'tool_use':
                    continue
                try:
                    output = self.tool_funcs[block.name](**block.input)
                except Exception as exc:
                    output = f'Error: {exc}'
                results.append({
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': output,
                })
            self.messages.append({'role': 'user', 'content': results})
            step += 1