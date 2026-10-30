"""Worker process: heartbeat, graceful shutdown and the DB-backed job queues."""

import asyncio
import logging
import signal
import time
from contextlib import suppress

from container import JobRunner, build_container, build_job_runner
from core.clock import Clock
from core.config import Settings, get_settings
from core.logging import configure_logging

logger = logging.getLogger("worker")


async def run_worker(
    settings: Settings, stop: asyncio.Event, clock: Clock, jobs: JobRunner | None = None
) -> None:
    logger.info(
        "worker started env=%s live_trading_enabled=%s",
        settings.app_env,
        settings.live_trading_enabled,
    )
    if settings.live_trading_enabled:
        logger.warning("LIVE TRADING FLAG IS ENABLED")
    if jobs is not None:
        recovered = await jobs.recover()
        if recovered:
            logger.info("re-queued %d interrupted job(s)", recovered)

    last_heartbeat = float("-inf")
    idle_wait = (
        settings.worker_poll_seconds if jobs is not None else settings.worker_heartbeat_seconds
    )
    while not stop.is_set():
        did_work = False
        if jobs is not None:
            try:
                did_work = await jobs.run_once()
            except Exception:
                logger.exception("job runner error")
        if time.monotonic() - last_heartbeat >= settings.worker_heartbeat_seconds:
            logger.info("heartbeat at %s", clock.now().isoformat())
            last_heartbeat = time.monotonic()
        if not did_work:
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=idle_wait)
    logger.info("worker stopped gracefully")


async def _main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    container = build_container(settings)
    jobs = build_job_runner(container)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):  # add_signal_handler is unavailable on Windows
            loop.add_signal_handler(sig, stop.set)
    try:
        await run_worker(settings, stop, container.clock, jobs)
    except asyncio.CancelledError:
        stop.set()
    finally:
        await container.exchanges.aclose()
        await container.engine.dispose()


def main() -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(_main())


if __name__ == "__main__":
    main()
