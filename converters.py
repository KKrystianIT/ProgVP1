"""Rejestr konwerterów i konwersje CSV <-> JSON (Lab 2)."""

import csv
import json
from collections.abc import Callable
from pathlib import Path

# Typ konwertera: funkcja (plik wejściowy, katalog wyjściowy) -> ścieżka wyniku
Converter = Callable[[Path, Path], Path]

# Rejestr: klucz (rozszerzenie źródła, rozszerzenie celu) -> funkcja konwertująca
REGISTRY: dict[tuple[str, str], Converter] = {}


def converter(source: str, target: str):
    """Dekorator: dopisuje funkcję do REGISTRY pod kluczem (source, target)."""
    def register(func: Converter) -> Converter:
        REGISTRY[(source, target)] = func
        return func
    return register


def available_targets(source: Path) -> list[str]:
    """Formaty, na które można przekonwertować dany plik."""
    return sorted(t for (s, t) in REGISTRY if s == source.suffix.lower())


@converter(".csv", ".json")
def csv_to_json(source: Path, output_dir: Path) -> Path:
    target = output_dir / f"{source.stem}.json"
    with source.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    with target.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return target


@converter(".json", ".csv")
def json_to_csv(source: Path, output_dir: Path) -> Path:
    target = output_dir / f"{source.stem}.csv"
    with source.open(encoding="utf-8-sig") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Niepoprawny JSON: {e.msg} (wiersz {e.lineno})") from e

    if not data or not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ValueError("JSON musi być niepustą tablicą obiektów: [{...}, {...}]")

    headers = list(data[0].keys())
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    return target
