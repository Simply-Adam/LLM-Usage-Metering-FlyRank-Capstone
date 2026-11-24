from app import pricing_config as prices


def format_usd(amount_micros):
    if type(amount_micros) is not int or amount_micros < 0:
        raise ValueError(
            "Money must be a non-negative integer in microdollars."
        )

    dollars, remainder = divmod(
        amount_micros,
        prices.MICROS_PER_USD,
    )

    return f"{dollars}.{remainder:06d}"


def calculate_cost(
    api_calls,
    input_tokens,
    cached_input_tokens,
    output_tokens,
    reasoning_tokens,
):
    counts = {
        "api_calls": api_calls,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
    }

    for name, value in counts.items():
        if type(value) is not int or value < 0:
            raise ValueError(
                f"{name} must be a non-negative integer."
            )

    if cached_input_tokens > input_tokens:
        raise ValueError(
            "cached_input_tokens cannot exceed input_tokens"
        )

    if reasoning_tokens > output_tokens:
        raise ValueError(
            "reasoning_tokens cannot exceed output_tokens"
        )

    fresh_input_tokens = input_tokens - cached_input_tokens

    breakdown = {
        "api_calls": api_calls * prices.API_CALL_MICROS,
        "fresh_input_tokens": (
            fresh_input_tokens * prices.FRESH_INPUT_TOKEN_MICROS
        ),
        "cached_input_tokens": (
            cached_input_tokens * prices.CACHED_INPUT_TOKEN_MICROS
        ),
        "output_tokens": (
            output_tokens * prices.OUTPUT_TOKEN_MICROS
        ),
    }

    total_micros = sum(breakdown.values())

    return {
        "kind": "usage_estimate",
        "currency": prices.CURRENCY,
        "pricing_version": prices.PRICING_VERSION,
        "breakdown_micros": breakdown,
        "total_micros": total_micros,
        "total_usd": format_usd(total_micros),
    }