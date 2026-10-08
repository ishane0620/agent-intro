from dataclasses import dataclass

# Dollars per million tokens: (input, output). Replace these with the
# current rates for the model you actually call.
PRICING: dict[str, tuple[float, float]] = {
    'claude-sonnet-5': (3.0, 15.0),
}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __add__(self, other: 'Usage') -> 'Usage':
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens,
        )

    def cost(self, model: str) -> float:
        input_price, output_price = PRICING[model]
        return (
            self.input_tokens * input_price + self.output_tokens * output_price
        ) / 1_000_000

    @classmethod
    def from_api(cls, usage) -> 'Usage':
        return cls(
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            cache_read_tokens=getattr(usage, 'cache_read_input_tokens', 0) or 0,
            cache_write_tokens=getattr(usage, 'cache_creation_input_tokens', 0) or 0,
        )