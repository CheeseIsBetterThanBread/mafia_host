import asyncio
from collections import defaultdict
from typing import Type

from src.connection.middleware import logging_middleware, error_middleware


def prepare_bus():
    bus = EventBus()
    bus.add_middleware(error_middleware)
    bus.add_middleware(logging_middleware)
    return bus


class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.middlewares = []

    def subscribe(self, event_type: Type, handler):
        self.subscribers[event_type].append(handler)

    def on(self, event_type: Type):
        def wrapper(func):
            self.subscribe(event_type, func)
            return func

        return wrapper

    def add_middleware(self, middleware):
        self.middlewares.append(middleware)

    async def emit(self, event):
        handlers = []

        for subscribed_type, subs in self.subscribers.items():
            if issubclass(type(event), subscribed_type):
                handlers.extend(subs)

        async def call_handlers(evt):
            tasks = [asyncio.create_task(h(evt)) for h in handlers]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        handler_chain = call_handlers

        for middleware in reversed(self.middlewares):
            next_handler = handler_chain

            async def wrapper(evt, mw=middleware, nxt=next_handler):
                await mw(evt, nxt)

            handler_chain = wrapper

        await handler_chain(event)


BUS = prepare_bus()


async def send_async_response(response):
    await BUS.emit(response)
