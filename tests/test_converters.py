"""Testy automatyczne. Uruchomienie: python -m pytest -v"""

import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import converters  # noqa: E402
from converters import available_targets, convert, validate  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
HAS_LIBREOFFICE = shutil.which("soffice") or shutil.which("libreoffice") or any(
    Path(p).is_file() for p in converters.LIBREOFFICE_PATHS)
needs_libreoffice = pytest.mark.skipif(not HAS_LIBREOFFICE, reason="LibreOffice nie jest zainstalowany")


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


# ---------------------------------------------------------------- rejestr i walidacja

def test_available_targets_depend_on_extension():
    assert available_targets(Path("a.csv")) == [".json"]
    assert available_targets(Path("a.DOCX")) == [".pdf", ".txt"]  # wielkość liter bez znaczenia
    assert available_targets(Path("a.mp3")) == []


def test_validate_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Nie znaleziono pliku"):
        validate(tmp_path / "brak.csv", ".json", tmp_path)


def test_validate_unsupported_pair(tmp_path):
    with pytest.raises(ValueError, match="Nieobsługiwana konwersja"):
        validate(SAMPLES / "studenci.csv", ".pdf", tmp_path)


def test_validate_missing_output_dir(tmp_path):
    with pytest.raises(ValueError, match="katalogu docelowego"):
        validate(SAMPLES / "studenci.csv", ".json", tmp_path / "nie_ma")


def test_validate_empty_choice(tmp_path):
    with pytest.raises(ValueError, match="Nie wybrano"):
        validate(SAMPLES / "studenci.csv", "", tmp_path)


# ---------------------------------------------------------------- grupa A: CSV <-> JSON

def test_csv_to_json_polish_chars_headers_and_empty_values(tmp_path):
    data = json.loads(convert(SAMPLES / "studenci.csv", ".json", tmp_path).read_text(encoding="utf-8"))
    assert list(data[0]) == ["nr_albumu", "imię", "nazwisko", "miasto"]  # kolejność nagłówków
    assert data[0]["nazwisko"] == "Żółkiewska"
    assert data[1]["miasto"] == ""  # pusta komórka


def test_csv_json_csv_round_trip(tmp_path):
    json_file = convert(SAMPLES / "studenci.csv", ".json", tmp_path)
    back_dir = tmp_path / "powrot"
    back_dir.mkdir()
    assert read_csv(convert(json_file, ".csv", back_dir)) == read_csv(SAMPLES / "studenci.csv")


def test_json_to_csv(tmp_path):
    rows = read_csv(convert(SAMPLES / "studenci.json", ".csv", tmp_path))
    assert rows[0] == ["nr_albumu", "imię", "nazwisko", "miasto"]
    assert rows[1][1] == "Świętosław"


def test_invalid_json_gives_message_without_output(tmp_path):
    with pytest.raises(ValueError, match="Niepoprawny JSON"):
        convert(SAMPLES / "bledny.json", ".csv", tmp_path)
    assert list(tmp_path.iterdir()) == []  # nie powstał żaden plik


@pytest.mark.parametrize("content", ['{"a": 1}', "[1, 2]", "[]", '[{"a": {"b": 1}}]'])
def test_json_wrong_structure(tmp_path, content):
    src = tmp_path / "x.json"
    src.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        convert(src, ".csv", tmp_path)


def test_csv_wrong_number_of_fields(tmp_path):
    with pytest.raises(ValueError, match="Wiersz 2"):
        convert(SAMPLES / "zla_liczba_pol.csv", ".json", tmp_path)


def test_csv_not_utf8(tmp_path):
    src = tmp_path / "cp1250.csv"
    src.write_bytes("imię\nŁucja\n".encode("cp1250"))
    with pytest.raises(ValueError, match="UTF-8"):
        convert(src, ".json", tmp_path)


# ---------------------------------------------------------------- grupa B: TXT <-> DOCX

def test_txt_docx_txt_keeps_paragraphs_and_polish_chars(tmp_path):
    docx_file = convert(SAMPLES / "notatka.txt", ".docx", tmp_path)
    back_dir = tmp_path / "powrot"
    back_dir.mkdir()
    text = convert(docx_file, ".txt", back_dir).read_text(encoding="utf-8")
    paragraphs = text.strip().split("\n\n")
    assert len(paragraphs) == 3
    assert "zażółć gęślą jaźń" in paragraphs[1]


def test_corrupted_docx_to_txt(tmp_path):
    with pytest.raises(ValueError, match="uszkodzony"):
        convert(SAMPLES / "uszkodzony.docx", ".txt", tmp_path)


# ---------------------------------------------------------------- grupa C: DOCX/ODT -> PDF

@needs_libreoffice
@pytest.mark.parametrize("name", ["notatka.docx", "dokument.odt"])
def test_document_to_pdf(tmp_path, name):
    pdf = convert(SAMPLES / name, ".pdf", tmp_path)
    assert pdf.read_bytes().startswith(b"%PDF")


def test_corrupted_docx_to_pdf(tmp_path):
    with pytest.raises(ValueError, match="uszkodzony"):
        convert(SAMPLES / "uszkodzony.docx", ".pdf", tmp_path)


def test_missing_libreoffice(tmp_path, monkeypatch):
    """„Test przez zmianę konfiguracji”: pusty PATH i brak domyślnych ścieżek instalacji."""
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(converters, "LIBREOFFICE_PATHS", [])
    with pytest.raises(RuntimeError, match="Nie znaleziono LibreOffice.*Zainstaluj"):
        convert(SAMPLES / "notatka.docx", ".pdf", tmp_path)
