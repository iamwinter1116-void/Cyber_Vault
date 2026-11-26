"""Runner entry point: ``python -m services.runner.main`` from the repository root (docs/08 section 3).

Reconciles every second and reaps every 30 s. Polling only: the contract names no NOTIFY channel for env
changes, and a one-second poll is inside the 3 s state-visibility target of 04 section 6.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import docker

from core.abh_core.db import create_pool
from core.abh_core.settings import Settings
from services.runner import storage
from services.runner.objects import DockerOps
from services.runner.reconcile import reap, reconcile_once

REAP_EVERY_SEC = 30
log = logging.getLogger("abh.runner")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    pool = create_pool(settings.db_dsn, max_size=4)
    ops = DockerOps(docker.from_env(), runtime=settings.sandbox_runtime, allow_degraded=settings.allow_degraded,
                    volume_dir=settings.volume_dir, templates_dir=Path(__file__).resolve().parents[2] / "sandbox" /
                    "templates", storage_method=storage.CHOSEN_METHOD)
    log.info("runner started: runtime=%s allow_degraded=%s storage=%s", settings.sandbox_runtime,
             settings.allow_degraded, storage.CHOSEN_METHOD)
    next_reap = 0.0
    while True:
        try:
            reconcile_once(pool, ops)
            if time.monotonic() >= next_reap:
                next_reap = time.monotonic() + REAP_EVERY_SEC
                stale = reap(pool, ops)
                if stale:
                    log.info("reaped %d stale env ids: %s", len(stale), sorted(stale))
        except Exception:
            log.exception("runner pass failed; retrying in 1 s")
        time.sleep(1)


if __name__ == "__main__":
    main()
