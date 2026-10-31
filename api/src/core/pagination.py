from typing import Annotated

from fastapi import Query, Response

TOTAL_COUNT_HEADER = "X-Total-Count"

Offset = Annotated[int, Query(ge=0, description="Rows to skip (newest first).")]


def set_total(response: Response, total: int) -> None:
    """The size of the whole list, so a client can page it; ``limit``/``offset`` pick the window."""
    response.headers[TOTAL_COUNT_HEADER] = str(total)
