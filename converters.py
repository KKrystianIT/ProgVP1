
import csv
import json
import shutil
import subprocess
import zipfile
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



@converter(".txt", ".docx")
def txt_to_docx(source: Path, output_dir: Path) -> Path:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("Brak biblioteki python-docx. Zainstaluj ją: pip install python-docx")

    target = output_dir / f"{source.stem}.docx"
    try:
        text = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Plik TXT nie jest zapisany w kodowaniu UTF-8")

    document = Document()
    for paragraph in text.split("\n\n"):
        if paragraph.strip():
            document.add_paragraph(paragraph.strip())
    document.save(target)
    return target


def find_libreoffice() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    for path in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(path).is_file():
            return path
    raise RuntimeError(
        "Nie znaleziono LibreOffice. Zainstaluj go ze strony https://www.libreoffice.org "
        "i uruchom program ponownie."
    )


@converter(".docx", ".pdf")
def docx_to_pdf(source: Path, output_dir: Path) -> Path:
    if not zipfile.is_zipfile(source):
        raise ValueError("Plik DOCX jest uszkodzony lub nie jest dokumentem Word")

    command = [
        find_libreoffice(), "--headless", "--convert-to", "pdf",
        "--outdir", str(output_dir), str(source),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise RuntimeError("LibreOffice nie zakończył konwersji w ciągu 60 sekund")

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Konwersja nie powiodła się")
    target = output_dir / f"{source.stem}.pdf"
    if not target.exists():
        raise RuntimeError("LibreOffice nie utworzył pliku PDF (czy plik DOCX nie jest uszkodzony?)")
    return target
