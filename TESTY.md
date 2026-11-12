# Raport testów

Środowisko: <Windows 11, wersja Pythona 3.12.10>
Polecenie: `python -m pytest -v` → **21 passed** (testy w `tests/test_converters.py`).

## Minimalna macierz testów z instrukcji

| # | Przypadek | Oczekiwany rezultat | Jak sprawdzono | Wynik |
|---|---|---|---|---|
| 1 | Poprawny plik – grupa A (CSV ↔ JSON) | otwieralny plik o właściwej treści | `test_csv_to_json_polish_chars_headers_and_empty_values`, `test_json_to_csv`, `test_csv_json_csv_round_trip`; pliki `studenci.csv`, `studenci.json` | OK |
| 2 | Poprawny plik – grupa B (TXT ↔ DOCX) | DOCX/TXT z tymi samymi akapitami | `test_txt_docx_txt_keeps_paragraphs_and_polish_chars`; plik `notatka.txt` | OK |
| 3 | Poprawny plik – grupa C (DOCX/ODT → PDF) | PDF otwierający się w przeglądarce | `test_document_to_pdf` (DOCX i ODT); pliki `notatka.docx`, `dokument.odt` | OK |
| 4 | Błędny lub uszkodzony plik | brak awarii, jednoznaczny komunikat | `test_invalid_json_gives_message_without_output`, `test_json_wrong_structure` (4 warianty), `test_csv_wrong_number_of_fields`, `test_csv_not_utf8`, `test_corrupted_docx_to_txt`, `test_corrupted_docx_to_pdf`; w GUI: `bledny.json` → okno błędu | OK |
| 5 | Nieobsługiwana para | opcja niewidoczna/zablokowana | `test_available_targets_depend_on_extension`, `test_validate_unsupported_pair`; w GUI: plik `.md` → lista formatów i przycisk zablokowane | OK |
| 6 | Brak LibreOffice/biblioteki | kontrolowany błąd z instrukcją | `test_missing_libreoffice` – zmiana konfiguracji: pusty PATH i pusta lista ścieżek instalacji → „Nie znaleziono LibreOffice… Zainstaluj go…” | OK |
| 7 | Plik docelowy już istnieje | pytanie o nadpisanie | GUI: drugi raz ta sama konwersja → okno „Plik już istnieje. Nadpisać?”; „Nie” – plik bez zmian, „Tak” – nadpisany | OK |
| 8 | Polskie znaki i puste wartości | znaki i struktura bez zmian | `test_csv_to_json_polish_chars_headers_and_empty_values`, `test_txt_docx_txt_keeps_paragraphs_and_polish_chars` | OK |

## Walidacja wejścia

| Przypadek | Test | Wynik |
|---|---|---|
| Brak pliku wejściowego | `test_validate_missing_file` | OK |
| Brak katalogu docelowego | `test_validate_missing_output_dir` | OK |
| Pusty wybór formatu | `test_validate_empty_choice` | OK |

## Przykładowe komunikaty

```
$ python main.py samples/bledny.json .csv wyniki
Błąd: Niepoprawny JSON: Expecting ',' delimiter (wiersz 3, kolumna 3). Popraw składnię pliku, np. brakujący przecinek lub cudzysłów.

$ python main.py samples/studenci.csv .pdf wyniki
Błąd: Nieobsługiwana konwersja .csv -> .pdf. Dostępne formaty dla tego pliku: .json.

$ python main.py samples/uszkodzony.docx .txt wyniki
Błąd: Nie można odczytać pliku uszkodzony.docx – jest uszkodzony lub nie jest dokumentem Word. Otwórz go w Wordzie/LibreOffice i zapisz ponownie jako .docx.
```
