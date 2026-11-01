from typing import Annotated

from pydantic import BaseModel, StringConstraints

NOTE_MAX_LENGTH = 2000


class NoteIn(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NOTE_MAX_LENGTH)
    ]


class NoteOut(BaseModel):
    actor: str
    text: str
