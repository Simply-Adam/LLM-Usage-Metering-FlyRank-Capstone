from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_TOKEN_COUNT = 1_000_000_000


class GenerateRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    input_tokens: int = Field(ge=0, le=MAX_TOKEN_COUNT)
    cached_input_tokens: int = Field(
        default=0,
        ge=0,
        le=MAX_TOKEN_COUNT,
    )

    output_tokens: int = Field(ge=0, le=MAX_TOKEN_COUNT)
    reasoning_tokens: int = Field(
        default=0,
        ge=0,
        le=MAX_TOKEN_COUNT,
    )

    @model_validator(mode="after")
    def validate_token_categories(self):
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError(
                "cached_input_tokens cannot exceed input_tokens"
            )

        if self.reasoning_tokens > self.output_tokens:
            raise ValueError(
                "reasoning_tokens cannot exceed output_tokens"
            )

        return self