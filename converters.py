"""Rejestr konwerterów i wszystkie konwersje programu.

Grupa A – dane strukturalne:  CSV -> JSON, JSON -> CSV
Grupa B – tekst i dokumenty:  TXT -> DOCX, DOCX -> TXT
Grupa C – formaty biurowe:    DOCX -> PDF, ODT -> PDF  (LibreOffice)

Każdy błąd zgłaszany użytkownikowi zawiera przyczynę i podpowiedź, co zrobić dalej:
  ValueError   – problem z danymi użytkownika (plik, format, katalog),
  RuntimeError – problem ze środowiskiem (brak biblioteki lub LibreOffice).
"""

import csv
import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger("konwerter")

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


def supported_sources() -> list[str]:
    """Rozszerzenia plików, które program potrafi otworzyć (do filtra w oknie wyboru)."""
    return sorted({s for (s, _) in REGISTRY})


def output_path(source: Path, target_format: str, output_dir: Path) -> Path:
    """Ścieżka, pod którą konwerter zapisze wynik (ta sama nazwa, nowe rozszerzenie)."""
    return output_dir / f"{source.stem}{target_format.lower()}"


def setup_logging() -> None:
    """Zapisuje przebieg konwersji i błędy do pliku konwerter.log obok programu."""
    logging.basicConfig(
        filename=Path(__file__).with_name("konwerter.log"),
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def validate(source: Path, target_format: str, output_dir: Path) -> None:
    """Sprawdza dane wejściowe przed konwersją. Przy problemie rzuca ValueError."""
    if not str(source).strip() or not target_format.strip() or not str(output_dir).strip():
        raise ValueError("Nie wybrano pliku, formatu lub katalogu. Uzupełnij wszystkie pola.")
    if not source.is_file():
        raise ValueError(f"Nie znaleziono pliku wejściowego: {source}. Sprawdź ścieżkę i wybierz plik ponownie.")
    key = (source.suffix.lower(), target_format.lower())
    if key not in REGISTRY:
        dostepne = ", ".join(available_targets(source)) or "brak"
        raise ValueError(
            f"Nieobsługiwana konwersja {key[0] or '(brak rozszerzenia)'} -> {key[1]}. "
            f"Dostępne formaty dla tego pliku: {dostepne}."
        )
    if not output_dir.is_dir():
        raise ValueError(f"Nie znaleziono katalogu docelowego: {output_dir}. Wybierz istniejący katalog.")
    if not os.access(output_dir, os.W_OK):
        raise ValueError(f"Brak uprawnień do zapisu w katalogu {output_dir}. Wybierz inny katalog.")


def convert(source: Path, target_format: str, output_dir: Path) -> Path:
    """Waliduje dane, uruchamia właściwy konwerter i zapisuje przebieg w logu.

    Wspólny punkt wejścia dla CLI (main.py) i GUI (gui.py).
    """
    log.info("Start: %s -> %s (katalog: %s)", source, target_format, output_dir)
    try:
        validate(source, target_format, output_dir)
        result = REGISTRY[(source.suffix.lower(), target_format.lower())](source, output_dir)
    except (ValueError, RuntimeError) as e:
        log.error("Błąd: %s", e)
        raise
    except Exception:
        log.exception("Nieoczekiwany błąd")  # pełny traceback w logu do diagnozy
        raise
    log.info("Gotowe: %s", result)
    return result


def _read_text(source: Path) -> str:
    """Czyta plik tekstowy UTF-8 (z BOM lub bez)."""
    try:
        return source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(
            f"Plik {source.name} nie jest zapisany w kodowaniu UTF-8. "
            "Zapisz go ponownie jako UTF-8 (np. w Notatniku: Zapisz jako → Kodowanie: UTF-8)."
        )


# ================================================================ Grupa A: CSV <-> JSON

@converter(".csv", ".json")
def csv_to_json(source: Path, output_dir: Path) -> Path:
    text = _read_text(source)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError(f"Plik {source.name} jest pusty. Pierwszy wiersz musi zawierać nagłówki kolumn.")

    rows = []
    for row in reader:
        if None in row or None in row.values():  # za dużo lub za mało pól w wierszu
            raise ValueError(
                f"Wiersz {reader.line_num} ma inną liczbę pól niż nagłówek ({len(reader.fieldnames)}). "
                "Sprawdź przecinki i cudzysłowy w tym wierszu."
            )
        rows.append(row)

    target = output_path(source, ".json", output_dir)
    with target.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return target


@converter(".json", ".csv")
def json_to_csv(source: Path, output_dir: Path) -> Path:
    try:
        data = json.loads(_read_text(source))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Niepoprawny JSON: {e.msg} (wiersz {e.lineno}, kolumna {e.colno}). "
            "Popraw składnię pliku, np. brakujący przecinek lub cudzysłów."
        ) from e

    if not data or not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ValueError('JSON musi być niepustą tablicą obiektów, np. [{"imię": "Anna"}]. Popraw strukturę pliku.')
    for i, record in enumerate(data, start=1):
        for key, value in record.items():
            if isinstance(value, (dict, list)):
                raise ValueError(
                    f"Obiekt nr {i}, pole „{key}”: zagnieżdżone dane nie są obsługiwane. "
                    "Każda wartość musi być tekstem, liczbą, true/false albo null."
                )

    headers = list(data[0].keys())
    target = output_path(source, ".csv", output_dir)
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    return target


# ================================================================ Grupa B: TXT <-> DOCX

def _docx_module():
    """Importuje python-docx dopiero, gdy jest potrzebny – brak biblioteki nie psuje reszty programu."""
    try:
        import docx
    except ImportError:
        raise RuntimeError("Brak biblioteki python-docx. Zainstaluj ją poleceniem: pip install -r requirements.txt")
    return docx


@converter(".txt", ".docx")
def txt_to_docx(source: Path, output_dir: Path) -> Path:
    docx = _docx_module()
    text = _read_text(source)

    document = docx.Document()
    for paragraph in text.split("\n\n"):  # pusta linia = granica akapitu
        if paragraph.strip():
            document.add_paragraph(paragraph.strip())

    target = output_path(source, ".docx", output_dir)
    document.save(target)
    return target


@converter(".docx", ".txt")
def docx_to_txt(source: Path, output_dir: Path) -> Path:
    docx = _docx_module()
    try:
        document = docx.Document(source)
    except Exception as e:  # python-docx zgłasza różne wyjątki dla uszkodzonych plików
        raise ValueError(
            f"Nie można odczytać pliku {source.name} – jest uszkodzony lub nie jest dokumentem Word. "
            "Otwórz go w Wordzie/LibreOffice i zapisz ponownie jako .docx."
        ) from e

    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    target = output_path(source, ".txt", output_dir)
    target.write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8")
    return target


# ================================================================ Grupa C: DOCX/ODT -> PDF

# Typowe miejsca instalacji LibreOffice, gdy nie ma go w PATH (Windows i macOS)
LIBREOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_libreoffice() -> str:
    """Zwraca ścieżkę do programu LibreOffice albo rzuca RuntimeError z instrukcją."""
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    for path in LIBREOFFICE_PATHS:
        if Path(path).is_file():
            return path
    raise RuntimeError(
        "Nie znaleziono LibreOffice, który jest potrzebny do tworzenia PDF. "
        "Zainstaluj go ze strony https://www.libreoffice.org i uruchom program ponownie."
    )


def _libreoffice_to_pdf(source: Path, output_dir: Path, kind: str) -> Path:
    # DOCX i ODT to w środku archiwa ZIP – inaczej LibreOffice potraktowałby plik jak zwykły tekst
    if not zipfile.is_zipfile(source):
        raise ValueError(
            f"Plik {source.name} jest uszkodzony lub nie jest dokumentem {kind}. "
            "Otwórz go w edytorze i zapisz ponownie."
        )

    with tempfile.TemporaryDirectory() as profile_dir:
        command = [
            find_libreoffice(),
            # osobny, tymczasowy profil – konwersja działa nawet przy otwartym oknie LibreOffice
            f"-env:UserInstallation={Path(profile_dir).as_uri()}",
            "--headless", "--convert-to", "pdf",
            "--outdir", str(output_dir), str(source),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice nie zakończył konwersji w ciągu 120 sekund. Spróbuj ponownie.")

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice zakończył się błędem (kod {result.returncode}): "
            f"{result.stderr.strip() or 'brak opisu'}. Sprawdź, czy plik otwiera się w LibreOffice."
        )
    target = output_path(source, ".pdf", output_dir)
    if not target.exists():
        raise RuntimeError("LibreOffice nie utworzył pliku PDF. Sprawdź, czy plik otwiera się w LibreOffice.")
    return target


@converter(".docx", ".pdf")
def docx_to_pdf(source: Path, output_dir: Path) -> Path:
    return _libreoffice_to_pdf(source, output_dir, "Word (DOCX)")


@converter(".odt", ".pdf")
def odt_to_pdf(source: Path, output_dir: Path) -> Path:
    return _libreoffice_to_pdf(source, output_dir, "OpenDocument (ODT)")
