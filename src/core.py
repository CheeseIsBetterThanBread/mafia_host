from src.connection.bus import EventBus, BUS
from src.connection.event import Query

from src.routing.router import process_query

from src.models.meta import Result, Response


class Core:
    def __init__(self):
        self.bus: EventBus = BUS

    def register(self):
        @self.bus.on
        async def dispatch(query: Query):
            result: Result = process_query(query)
            if result.is_left:
                response: Response = result.get_left()
                await self.bus.emit(response)
                return

            responses: list[Response] = result.get_right().responses
            for response in responses:
                await self.bus.emit(response)
