"""Ask the OpenAI-powered Enterprise Data Intelligence Agent a question."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from f1_strategy_data.intelligence_agent import (
    DEFAULT_AGENT_ROOTS,
    EnterpriseDataIntelligenceAgent,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", help="Business or data question")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--model", help="OpenAI model ID (or set OPENAI_MODEL)")
    parser.add_argument(
        "--data-root", action="append", default=[],
        help="Approved repository-relative dataset directory; repeatable",
    )
    parser.add_argument("--catalog", action="store_true", help="Print the local catalog only")
    args = parser.parse_args()

    agent = EnterpriseDataIntelligenceAgent(
        args.root,
        model=args.model,
        data_roots=args.data_root or DEFAULT_AGENT_ROOTS,
    )
    if args.catalog:
        print(json.dumps([asdict(item) for item in agent.catalog()], indent=2))
        return
    if not args.question:
        parser.error("question is required unless --catalog is used")
    print(agent.ask(args.question))


if __name__ == "__main__":
    main()
