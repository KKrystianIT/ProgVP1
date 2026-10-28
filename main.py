"""Uruchamianie konwersji bez GUI.

Użycie: python main.py PLIK FORMAT KATALOG
Przykład: python main.py samples/studenci.csv .json wyniki
"""

import sys
from pathlib import Path

from converters import REGISTRY, available_targets


def main() -> int:
    if len(sys.argv) != 4:
        print("Użycie: python main.py PLIK FORMAT KATALOG")
        print("Przykład: python main.py samples/studenci.csv .json wyniki")
        return 1

    source = Path(sys.argv[1])
    fmt = sys.argv[2].lower()
    out = Path(sys.argv[3])

    if not source.is_file():
        print(f"Błąd: nie znaleziono pliku {source}")
        return 1

    key = (source.suffix.lower(), fmt)
    if key not in REGISTRY:
        print(f"Błąd: nieobsługiwana konwersja {key[0]} -> {fmt}")
        print(f"Dostępne formaty dla tego pliku: {available_targets(source)}")
        return 1

    out.mkdir(parents=True, exist_ok=True)

    try:
        result = REGISTRY[key](source, out)
    except ValueError as e:
        print(f"Błąd: {e}")
        return 1

    print(f"Gotowe: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
