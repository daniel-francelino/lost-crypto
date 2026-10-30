from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

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


@router.get("", response_model=list[StrategyOut])
async def list_strategies(request: Request) -> list[StrategyOut]:
    """Available strategy types and their configurable parameters."""
    container: Container = request.app.state.container
    return [
        StrategyOut(
            type_key=d.type_key,
            name=d.name,
            description=d.description,
            parameters=[
                ParamOut(
                    name=p.name,
                    type=p.type,
                    default=p.default,
                    minimum=p.minimum,
                    description=p.description,
                )
                for p in d.parameters
            ],
        )
        for d in container.registry.list()
    ]
