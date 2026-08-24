import asyncio
import logging
import os
import threading

from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticFilesRunserverCommand,
)
from django.utils.autoreload import DJANGO_AUTORELOAD_ENV

from integrations.telegram_runtime import TelegramListenerSupervisor


logger = logging.getLogger(__name__)


class TelegramListenerThread:
    """Run the async Telegram supervisor beside Django's development server."""

    def __init__(self):
        self._loop = None
        self._supervisor = None
        self._stop_requested = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="telegram-listener",
            daemon=True,
        )

    @property
    def is_alive(self):
        return self._thread.is_alive()

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def _run(self):
        try:
            asyncio.run(self._run_supervisor())
        except Exception:
            logger.exception("The automatic Telegram listener stopped unexpectedly")

    async def _run_supervisor(self):
        self._loop = asyncio.get_running_loop()
        self._supervisor = TelegramListenerSupervisor()
        if self._stop_requested.is_set():
            self._supervisor.request_stop()
        await self._supervisor.run()

    def stop(self, timeout=5):
        self._stop_requested.set()
        if (
            self._thread.is_alive()
            and self._loop is not None
            and self._supervisor is not None
        ):
            try:
                self._loop.call_soon_threadsafe(self._supervisor.request_stop)
            except RuntimeError:
                pass
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)


class Command(StaticFilesRunserverCommand):
    help = (
        "Starts Django's development server and the Telegram listener together."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--no-telegram-listener",
            action="store_false",
            dest="use_telegram_listener",
            default=True,
            help="Start the development server without the Telegram listener.",
        )

    def _start_telegram_listener(self):
        listener = getattr(self, "_telegram_listener", None)
        if listener is not None and listener.is_alive:
            return
        listener = TelegramListenerThread()
        listener.start()
        self._telegram_listener = listener
        self.stdout.write(self.style.SUCCESS("Telegram listener started automatically."))

    def _stop_telegram_listener(self):
        listener = getattr(self, "_telegram_listener", None)
        self._telegram_listener = None
        if listener is not None:
            listener.stop()

    def run(self, **options):
        owns_listener = (
            not options.get("use_reloader", True)
            or os.environ.get(DJANGO_AUTORELOAD_ENV) == "true"
        )
        self._use_telegram_listener = (
            options.get("use_telegram_listener", True) and owns_listener
        )
        try:
            return super().run(**options)
        finally:
            self._stop_telegram_listener()

    def on_bind(self, server_port):
        super().on_bind(server_port)
        if getattr(self, "_use_telegram_listener", True):
            self._start_telegram_listener()
