from typing import Optional

from src.models.either import Either
from src.models.game import Game

from src.connection.event import Query, Response


class Meta:
    def __init__(self, query: Query):
        self.query: Query = query
        self.game: Optional[Game] = None
        self.responses: Optional[list[Response]] = None

    def add_response(self, response: Response):
        if self.responses is None:
            self.responses = []

        self.responses.append(response)


Result = Either[Response, Meta]
