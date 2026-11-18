import argparse
import logging
import time
from pathlib import Path

import httpx

from gighunter.adapters.registry import build_adapters
from gighunter.config import load_config
from gighunter.health import SourceHealth
from gighunter.notifier import TelegramNotifier
from gighunter.runner import run_once
from gighunter.settings import TelegramSettings
from gighunter.store import SeenStore

log = logging.getLogger("gighunter")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gighunter")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--once", action="store_true", help="single run, then exit")
    return parser.parse_args()


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs full request URLs at INFO; Telegram's URL contains the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    args = _parse_args()
    _setup_logging()
    cfg = load_config(args.config)
    tg = TelegramSettings.from_env()
    proxy = tg.proxy.get_secret_value() if tg.proxy else None
    store, health = SeenStore(cfg.db_path), SourceHealth()
    adapters = build_adapters(cfg)
    try:
        with httpx.Client() as src_client, httpx.Client(proxy=proxy) as tg_client:
            notifier = TelegramNotifier(tg, tg_client)
            while True:
                stats = run_once(cfg, adapters, notifier, store, src_client, health)
                log.info("run: %s", stats)
                if args.once:
                    break
                time.sleep(cfg.poll_interval_s)
    except KeyboardInterrupt:
        log.info("stopped")
    finally:
        store.close()


if __name__ == "__main__":
    main()
