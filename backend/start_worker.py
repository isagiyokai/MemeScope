#!/usr/bin/env python3
"""Worker process entrypoint for Render (and local dev).

Usage:
    python start_worker.py parser
    python start_worker.py signal
    python start_worker.py holder
    python start_worker.py pumpfun
"""
import asyncio
import importlib
import sys

WORKERS = {
    "parser":  ("workers.parser_worker",  "run_parser_worker"),
    "signal":  ("workers.signal_worker",  "run_signal_worker"),
    "holder":  ("workers.holder_worker",  "run_holder_worker"),
    "pumpfun": ("workers.pumpfun_worker", "run_pumpfun_worker"),
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in WORKERS:
        print(f"Usage: python start_worker.py <{'|'.join(WORKERS)}>")
        sys.exit(1)

    module_path, func_name = WORKERS[sys.argv[1]]
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    asyncio.run(func())


if __name__ == "__main__":
    main()
