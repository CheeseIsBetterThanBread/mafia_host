from typing import Optional

from src.models.either import Either
from src.models.game import Game

from src.connection.event import Query, Response


class Info:
    def __init__(self, query: Query):
        self.query: Query = query
        self.game: Optional[Game] = None
        self.response: Optional[Response] = None


Result = Either[Response, Info]
