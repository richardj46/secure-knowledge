from dataclasses import dataclass

from secure_knowledge_core.llm.interface import ModelUsage


@dataclass(frozen=True)
class ModelPrice:
    input_microusd_per_million_tokens: int
    output_microusd_per_million_tokens: int


class UnknownModelPriceError(Exception):
    pass


class CostCalculator:
    def __init__(
        self,
        prices: dict[str, ModelPrice],
    ) -> None:
        self.prices = prices

    def calculate_microusd(
        self,
        *,
        model: str,
        usage: ModelUsage,
    ) -> int | None:
        price = self.prices.get(model)

        if price is None:
            return None

        input_cost = (
            usage.input_tokens
            * price.input_microusd_per_million_tokens
            // 1_000_000
        )

        output_cost = (
            usage.output_tokens
            * price.output_microusd_per_million_tokens
            // 1_000_000
        )

        return input_cost + output_cost