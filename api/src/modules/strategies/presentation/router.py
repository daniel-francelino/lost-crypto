from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from container import Container

router = APIRouter(prefix="/strategies", tags=["strategies"])


class ParamOut(BaseModel):
    name: str
    type: str
    default: Any
    minimum: int | None
    description: str


class StrategyOut(BaseModel):
    type_key: str
    name: str
    description: str
    parameters: list[ParamOut]
    parameter_count: int = Field(
        description="Configurable parameters. Chan's rule of thumb: at most 5 (book 1 ch. 3)."
    )
    too_many_parameters: bool


MAX_PARAMETERS = 5


@router.get("", response_model=list[StrategyOut])
async def list_strategies(request: Request) -> list[StrategyOut]:
    """Available strategy types and their configurable parameters."""
    container: Container = request.app.state.container
    return [
        StrategyOut(
            type_key=d.TYPE_KEY,
            name=d.NAME,
            description=d.DESCRIPTION,
            parameters=[
                ParamOut(
                    name=p.name,
                    type=p.type,
                    default=p.default,
                    minimum=p.minimum,
                    description=p.description,
                )
                for p in d.PARAMETERS
            ],
            parameter_count=len(d.PARAMETERS),
            too_many_parameters=len(d.PARAMETERS) > MAX_PARAMETERS,
        )
        for d in container.registry.list()
    ]
