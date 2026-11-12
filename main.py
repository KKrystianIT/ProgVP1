"""Uruchamianie konwersji bez GUI.

Użycie: python main.py PLIK FORMAT KATALOG
Przykład: python main.py samples/studenci.csv .json wyniki
"""

import sys
from pathlib import Path

from converters import convert, setup_logging


def main() -> int:
    setup_logging()
    if len(sys.argv) != 4:
        print("Użycie: python main.py PLIK FORMAT KATALOG")
        print("Przykład: python main.py samples/studenci.csv .json wyniki")
        return 1

    source = Path(sys.argv[1])
    fmt = sys.argv[2].lower()
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)

    try:
        result = convert(source, fmt, out)
    except (ValueError, RuntimeError) as e:
        print(f"Błąd: {e}")
        return 1
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}. Szczegóły zapisano w pliku konwerter.log.")
        return 1

    print(f"Gotowe: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
