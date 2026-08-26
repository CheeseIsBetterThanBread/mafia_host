import asyncio
from typing import Dict, Callable, Optional
from dataclasses import dataclass

from src.services.logger import LOGGER


@dataclass
class TimerConfig:
    interval: float
    callback: Callable
    args: tuple = ()
    kwargs: dict = None
    task: Optional[asyncio.Task] = None
    cancelled: bool = False
    is_running: bool = False


class TimerManager:
    def __init__(self):
        self._timers: Dict[str, TimerConfig] = {}

    def add_timer(
        self, name: str, interval: float, callback: Callable, *args, **kwargs
    ):
        self._timers[name] = TimerConfig(
            interval=interval, callback=callback, args=args, kwargs=kwargs
        )
        return self

    async def _run_timer(self, name: str):
        config = self._timers[name]
        try:
            await asyncio.sleep(config.interval)
            if not config.cancelled:
                if asyncio.iscoroutinefunction(config.callback):
                    await config.callback(*config.args, **config.kwargs)
                else:
                    config.callback(*config.args, **config.kwargs)
        except asyncio.CancelledError:
            LOGGER.verbose_debug(f"Timer with name {name} is canceled")
        finally:
            config.is_running = False
            config.task = None

    def start_timer(self, name: str):
        if name not in self._timers:
            raise KeyError(f"Таймер {name} не найден")

        config = self._timers[name]

        if config.is_running:
            self.stop_timer(name)

        config.cancelled = False
        config.is_running = True
        config.task = asyncio.create_task(self._run_timer(name))

    def stop_timer(self, name: str):
        config = self._timers.get(name)
        if config and config.task and not config.task.done():
            config.cancelled = True
            config.task.cancel()
            config.is_running = False

    def restart_timer(self, name: str, interval: Optional[float] = None):
        config = self._timers.get(name)
        if config and interval is not None:
            config.interval = interval
        self.start_timer(name)

    def update_timer(self, name: str, **kwargs):
        config = self._timers.get(name)
        if config:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)

    def is_running(self, name: str) -> bool:
        config = self._timers.get(name)
        return config.is_running if config else False
