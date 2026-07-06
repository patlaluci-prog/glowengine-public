from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator
)


class TrainPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    features_list: list[float] = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Must contain exactly 6 elements between 0.0 and 1.0"
    )

    ai_score: float = Field(
        ...,
        ge=1.0,
        le=10.0
    )

    human_score: float = Field(
        ...,
        ge=1.0,
        le=10.0
    )

    # 🔥 OPRAVA: Validace hodnot uvnitř face vektoru přímo na vstupu
    @field_validator("features_list")
    @classmethod
    def validate_vector_bounds(cls, v: list[float]) -> list[float]:
        if any(x < 0.0 or x > 1.0 for x in v):
            raise ValueError("All features must be bounded between 0.0 and 1.0 inclusive")
        return v
