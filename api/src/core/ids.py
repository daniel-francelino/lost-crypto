from typing import Protocol
from uuid import UUID, uuid4


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class UuidGenerator:
    def new_id(self) -> UUID:
        return uuid4()
