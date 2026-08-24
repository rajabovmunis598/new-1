import asyncio
import signal

from django.core.management.base import BaseCommand

from integrations.telegram_runtime import TelegramListenerSupervisor


class Command(BaseCommand):
    help = "Run long-lived Telegram MTProto listeners for active integrations."

    def add_arguments(self, parser):
        parser.add_argument("--reconcile-interval", type=float, default=10.0)
        parser.add_argument("--reconnect-delay", type=float, default=5.0)

    def handle(self, *args, **options):
        supervisor = TelegramListenerSupervisor(
            reconcile_interval=max(options["reconcile_interval"], 1.0),
            reconnect_delay=max(options["reconnect_delay"], 1.0),
        )

        async def run():
            loop = asyncio.get_running_loop()
            for signum in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(signum, supervisor.request_stop)
                except (NotImplementedError, RuntimeError):
                    pass
            await supervisor.run()

        self.stdout.write("Starting Telegram listener supervisor")
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            self.stdout.write("Stopping Telegram listener supervisor")
