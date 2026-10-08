from collections.abc import Iterator

import anthropic

from agent.events import TextDelta, ToolCallFinished, ToolCallStarted, TurnFinished

MODEL = 'claude-sonnet-5'


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

    def prompt(self, user_text: str) -> Iterator[TextDelta | ToolCallStarted | ToolCallFinished | TurnFinished]:
        self.messages.append({'role': 'user', 'content': user_text})
        while True:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=self.system,
                tools=self.tools,
                thinking={'type': 'adaptive', 'display': 'summarized'},
                messages=self.messages,
            ) as stream:
                for event in stream:
                    if event.type == 'content_block_delta' and event.delta.type == 'text_delta':
                        yield TextDelta(event.delta.text)
                reply = stream.get_final_message()

            self.messages.append({'role': 'assistant', 'content': reply.content})
            if reply.stop_reason != 'tool_use':
                yield TurnFinished(reply.stop_reason)
                return

            results = []
            for block in reply.content:
                if block.type != 'tool_use':
                    continue
                yield ToolCallStarted(block.id, block.name, block.input)
                error = False
                try:
                    output = self.tool_funcs[block.name](**block.input)
                except Exception as exc:
                    output = f'Error: {exc}'
                    error = True
                yield ToolCallFinished(block.id, output, error)
                results.append({
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': output,
                })
            self.messages.append({'role': 'user', 'content': results})

    def prompt_sync(self, user_text: str) -> str:
        parts = []
        for event in self.prompt(user_text):
            if isinstance(event, TextDelta):
                parts.append(event.text)
        return ''.join(parts)