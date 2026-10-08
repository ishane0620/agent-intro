from dataclasses import dataclass


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallStarted:
    id: str
    name: str
    input: dict


@dataclass
class ToolCallFinished:
    id: str
    output: str
    error: bool


@dataclass
class TurnFinished:
    stop_reason: str