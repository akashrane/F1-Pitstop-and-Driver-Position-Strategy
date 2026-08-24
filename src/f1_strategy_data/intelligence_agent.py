"""Grounded, read-only enterprise data intelligence for F1 datasets."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_AGENT_ROOTS = ("data/features", "data/processed/consolidated_2023_2026")


@dataclass(frozen=True)
class DatasetProfile:
    path: str
    columns: list[str]
    sampled_rows: int
    null_counts: dict[str, int]
    sample: list[dict[str, str]]


def discover_csv_files(root: Path, data_roots: Iterable[str] = ("data",)) -> list[Path]:
    """Return CSV files below explicitly approved repository directories."""
    root = root.resolve()
    files: list[Path] = []
    for relative in data_roots:
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Data root escapes repository: {relative}")
        if candidate.is_dir():
            files.extend(path for path in candidate.rglob("*.csv") if path.is_file())
    return sorted(set(files))


def profile_csv(path: Path, repository_root: Path, max_rows: int = 200) -> DatasetProfile:
    """Build a bounded profile; the full dataset is never sent to the model."""
    resolved = path.resolve()
    root = repository_root.resolve()
    if root not in resolved.parents:
        raise ValueError(f"Dataset is outside repository: {path}")

    rows: list[dict[str, str]] = []
    null_counts: dict[str, int] = {}
    with resolved.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        null_counts = {column: 0 for column in columns}
        for index, row in enumerate(reader):
            if index >= max_rows:
                break
            normalized = {column: (row.get(column) or "").strip() for column in columns}
            for column, value in normalized.items():
                null_counts[column] += int(value == "")
            rows.append(normalized)

    return DatasetProfile(
        path=resolved.relative_to(root).as_posix(),
        columns=columns,
        sampled_rows=len(rows),
        null_counts=null_counts,
        sample=rows[:5],
    )


def build_catalog(
    repository_root: Path,
    data_roots: Iterable[str] = ("data",),
    max_files: int = 30,
    max_rows: int = 200,
) -> list[DatasetProfile]:
    files = discover_csv_files(repository_root, data_roots)
    return [profile_csv(path, repository_root, max_rows) for path in files[:max_files]]


SYSTEM_INSTRUCTIONS = """You are the Enterprise Data Intelligence Agent for an
auditable Formula 1 strategy-data repository. Answer only from the supplied
dataset catalog. Clearly distinguish observed facts, calculations, and
recommendations. Cite every material claim with the repository-relative dataset
path in square brackets. State when the catalog is insufficient. Never invent
rows, fields, business definitions, or causal conclusions. Treat samples as
samples, not complete population statistics. Keep answers concise and include a
short 'Data limitations' section."""


class EnterpriseDataIntelligenceAgent:
    def __init__(
        self,
        repository_root: Path,
        *,
        model: str | None = None,
        client: Any | None = None,
        data_roots: Iterable[str] = DEFAULT_AGENT_ROOTS,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
        self.data_roots = tuple(data_roots)
        self.client = client

    def _client(self) -> Any:
        """Create the API client only when a question actually needs the API."""
        if self.client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "Install agent dependencies with: pip install -e .[agent]"
                ) from exc
            self.client = OpenAI()
        return self.client

    def catalog(self) -> list[DatasetProfile]:
        return build_catalog(self.repository_root, self.data_roots)

    def ask(self, question: str) -> str:
        if not question.strip():
            raise ValueError("Question must not be empty")
        profiles = [asdict(profile) for profile in self.catalog()]
        if not profiles:
            raise RuntimeError("No CSV datasets found in the approved data roots")
        response = self._client().responses.create(
            model=self.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=(
                f"Question: {question.strip()}\n\n"
                f"Bounded dataset catalog:\n{json.dumps(profiles, ensure_ascii=False)}"
            ),
            store=False,
        )
        return response.output_text
