from src.models.either import Either
from src.models.game import Game
from src.models.maybe import Maybe, maybe

from src.connection.event import Query, Response


class Meta:
    def __init__(self, query: Query):
        self.query: Query = query
        self.game: Maybe[Game] = maybe()
        self.response: Maybe[Response] = maybe()


Result = Either[Response, Meta]
