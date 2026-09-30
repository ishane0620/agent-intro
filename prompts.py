from datetime import date
from pathlib import Path

SYSTEM_PROMPT = """\
You are a read-only code exploration assistant. You may list and read files. You may not write, edit, or delete anything.
Project root: {root}
Today's date: {date}
How to work:
- Call list_files before guessing at any path. Do not invent paths.
- Prefer many small tool calls over one broad one. List a directory, then read only the files you need.
- Answer concisely. Cite evidence as file:line references, for example src/user.py:42.
"""


def build_system_prompt(root: Path, extra: str | None = None) -> str:
    """Fill the root path and today's date into SYSTEM_PROMPT, then append extra text."""
    prompt = SYSTEM_PROMPT.format(root=root, date=date.today().isoformat())
    if extra:
        prompt = f'{prompt}\n\n{extra.strip()}'
    return prompt