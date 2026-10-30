"""Worker process entrypoint. Phase 0: heartbeat + graceful shutdown only."""

import asyncio
import logging
import signal
from contextlib import suppress

from lost_crypto.core.clock import Clock, SystemClock
from lost_crypto.core.config import Settings, get_settings
from lost_crypto.core.logging import configure_logging

logger = logging.getLogger("lost_crypto.worker")


async def run_worker(settings: Settings, stop: asyncio.Event, clock: Clock) -> None:
    logger.info(
        "worker started env=%s live_trading_enabled=%s",
        settings.app_env,
        settings.live_trading_enabled,
    )
    if settings.live_trading_enabled:
        logger.warning("LIVE TRADING FLAG IS ENABLED")
    while not stop.is_set():
        logger.info("heartbeat at %s", clock.now().isoformat())
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=settings.worker_heartbeat_seconds)
    logger.info("worker stopped gracefully")


async def _main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):  # add_signal_handler is unavailable on Windows
            loop.add_signal_handler(sig, stop.set)
    try:
        await run_worker(settings, stop, SystemClock())
    except asyncio.CancelledError:
        stop.set()


def main() -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(_main())


if __name__ == "__main__":
    main()
