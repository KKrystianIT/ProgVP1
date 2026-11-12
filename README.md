# Uniwersalny konwerter plików – Projekt 1

## Wymagania

- Python 3.10+
- biblioteka python-docx: `pip install -r requirements.txt`
- LibreOffice (do konwersji DOCX → PDF): https://www.libreoffice.org
  Program szuka go w PATH (`soffice`/`libreoffice`) oraz w domyślnych folderach instalacji
  na Windows i macOS. Gdy go nie znajdzie, wyświetla komunikat z instrukcją instalacji.

## Uruchomienie

```bash
python main.py samples/studenci.csv .json wyniki
python main.py samples/studenci.json .csv wyniki
python main.py samples/bledny.json .csv wyniki    # pokazuje komunikat o błędnym JSON
python main.py samples/notatka.txt .docx wyniki
python main.py wyniki/notatka.docx .pdf wyniki
```

## Format danych

- Pliki w kodowaniu **UTF-8** (CSV może mieć BOM, np. z Excela).
- **CSV:** pierwszy wiersz to nagłówki, separator: przecinek.
- **JSON:** tablica obiektów, np. `[{"imię": "Łucja", "miasto": "Łódź"}]`.
  Kolejność kolumn w CSV jest brana z kluczy pierwszego obiektu.
- Pusta komórka CSV ↔ pusty tekst `""` w JSON. Wszystkie wartości z CSV trafiają do JSON jako tekst.
- **TXT → DOCX:** plik UTF-8; pusta linia oddziela akapity, każdy akapit staje się akapitem w DOCX.

## Planowana macierz konwersji

| Grupa | Konwersja | Stan |
|---|---|---|
| A – dane strukturalne | CSV → JSON | gotowe (Lab 2) |
| A – dane strukturalne | JSON → CSV | gotowe (Lab 2) |
| B – tekst/dokument | TXT → DOCX | gotowe (Lab 3, python-docx) |
| B – tekst/dokument | DOCX → TXT | Lab 5 |
| C – dokument/PDF | DOCX → PDF | gotowe (Lab 3, LibreOffice) |
| C – dokument/PDF | ODT → PDF | Lab 5 |

## Autor

<Krystian Kulczycki>
