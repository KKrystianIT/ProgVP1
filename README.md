# Uniwersalny konwerter plików

Projekt 1 z przedmiotu Programowanie V.

## Cel

Aplikacja okienkowa (Tkinter) do konwersji plików między wybranymi formatami: danymi
strukturalnymi (CSV, JSON), tekstem i dokumentami (TXT, DOCX, ODT, PDF). Program pokazuje tylko te
formaty docelowe, które są obsługiwane dla wybranego pliku. Konwersje można też uruchamiać z linii poleceń.

## Obsługiwane konwersje

| Grupa | Konwersja | Narzędzie | Znane ograniczenia |
|---|---|---|---|
| A – dane strukturalne | CSV → JSON | biblioteka standardowa (`csv`, `json`) | wszystkie wartości trafiają do JSON jako tekst (CSV nie przechowuje typów); separator tylko przecinek |
| A – dane strukturalne | JSON → CSV | biblioteka standardowa (`csv`, `json`) | tylko tablica płaskich obiektów; zagnieżdżone obiekty i listy są odrzucane z komunikatem |
| B – tekst i dokumenty | TXT → DOCX | python-docx | brak formatowania (nagłówki, pogrubienia) – tylko akapity |
| B – tekst i dokumenty | DOCX → TXT | python-docx | pomijane są tabele, obrazy, przypisy, nagłówki/stopki stron; formatowanie jest tracone |
| C – formaty biurowe | DOCX → PDF | LibreOffice (tryb headless) | układ stron może się nieznacznie różnić od Worda (inne czcionki) |
| C – formaty biurowe | ODT → PDF | LibreOffice (tryb headless) | wymaga zainstalowanego LibreOffice |

Inne pary nie są obsługiwane – w oknie programu nie da się ich wybrać.

## Wymagania

- **Python 3.10 lub nowszy** z Tkinter. Na Windows i macOS Tkinter jest częścią instalatora
  z python.org; na Linuksie: `sudo apt install python3-tk`.
- **python-docx** (instalowany z `requirements.txt`) – konwersje TXT ↔ DOCX.
- **LibreOffice** (zależność systemowa) – konwersje do PDF. Pobierz z https://www.libreoffice.org.
  Program szuka LibreOffice w PATH (`soffice`/`libreoffice`) oraz w domyślnych folderach instalacji:
  - `C:\Program Files\LibreOffice\program\soffice.exe`
  - `C:\Program Files (x86)\LibreOffice\program\soffice.exe`
  - `/Applications/LibreOffice.app/Contents/MacOS/soffice`

  Bez LibreOffice pozostałe konwersje działają normalnie, a próba utworzenia PDF kończy się
  komunikatem z instrukcją instalacji.

## Instalacja

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
```

## Uruchomienie

### Okno programu

```bash
python gui.py
```

1. **Wybierz…** przy „Plik wejściowy” – lista „Format docelowy” pokaże tylko konwersje dostępne dla tego pliku.
2. Wybierz format z listy (nie da się wpisać własnego).
3. Katalog zapisu domyślnie to folder pliku wejściowego; przycisk **Wybierz…** pozwala go zmienić.
4. **Konwertuj** – przycisk jest aktywny dopiero, gdy wszystko jest wybrane. Jeśli plik wynikowy
   już istnieje, program zapyta, czy go nadpisać. Konwersja działa w tle (okno się nie zawiesza);
   postęp widać na pasku, a wynik w linii statusu i w oknie komunikatu.

### Linia poleceń

```bash
python main.py PLIK FORMAT KATALOG
```

`PLIK` – plik wejściowy, `FORMAT` – rozszerzenie docelowe z kropką, `KATALOG` – folder zapisu
(tworzony automatycznie). Uwaga: w trybie linii poleceń istniejący plik wynikowy jest nadpisywany.

```bash
python main.py samples/studenci.csv .json wyniki
python main.py samples/studenci.json .csv wyniki
python main.py samples/notatka.txt .docx wyniki
python main.py samples/notatka.docx .txt wyniki
python main.py samples/notatka.docx .pdf wyniki
python main.py samples/dokument.odt .pdf wyniki
```

### Testy

```bash
python -m pytest -v
```

Testy PDF są pomijane (`skipped`), jeśli LibreOffice nie jest zainstalowany. Raport: [TESTY.md](TESTY.md).

## Semantyka konwersji

**CSV ↔ JSON**
- Pliki w kodowaniu **UTF-8** (CSV może mieć BOM, np. z Excela). Plik w innym kodowaniu daje komunikat.
- CSV: pierwszy wiersz to nagłówki, separator: przecinek, wartości z przecinkiem w cudzysłowach `"..."`.
  Każdy wiersz musi mieć tyle pól, ile nagłówek.
- JSON: niepusta tablica płaskich obiektów, np. `[{"imię": "Łucja", "miasto": "Łódź"}]`.
  Wartości: tekst, liczba, `true`/`false` albo `null`.
- Kolejność kolumn w CSV = kolejność kluczy pierwszego obiektu JSON; brakujący klucz → pusta komórka.
- Pusta komórka CSV → `""` w JSON; `null` w JSON → pusta komórka w CSV.
- CSV → JSON → CSV odtwarza dane wejściowe (sprawdzane testem).

**TXT ↔ DOCX**
- TXT w kodowaniu UTF-8. **Pusta linia oddziela akapity**: każdy blok tekstu staje się akapitem DOCX;
  pojedynczy znak nowej linii w bloku zostaje złamaniem wiersza w tym samym akapicie.
- DOCX → TXT: każdy niepusty akapit dokumentu zapisywany jest jako blok tekstu, akapity rozdziela pusta linia.

**DOCX/ODT → PDF** – konwersja wykonywana przez LibreOffice uruchamiany w tle
(`soffice --headless --convert-to pdf`) z tymczasowym profilem użytkownika, dzięki czemu działa
również przy otwartym oknie LibreOffice. Limit czasu: 120 s.

## Walidacja i obsługa błędów

Przed konwersją program sprawdza: niepuste wybory, istnienie pliku, obsługiwaną parę formatów,
istnienie katalogu docelowego i prawo zapisu. GUI dodatkowo pyta przed nadpisaniem istniejącego pliku.
Każdy komunikat błędu zawiera przyczynę i podpowiedź, co zrobić. Przebieg konwersji i błędy są
zapisywane w pliku `konwerter.log` (obok programu).

## Architektura

```
converters.py   rejestr konwerterów (dekorator @converter), walidacja, wszystkie konwertery
gui.py          okno programu (Tkinter/ttk) – bez logiki konwersji
main.py         uruchamianie z linii poleceń
tests/          testy automatyczne (pytest)
samples/        dane testowe
```

- `REGISTRY` to słownik `(rozszerzenie źródła, rozszerzenie celu) → funkcja`. Nowa konwersja to
  nowa funkcja z dekoratorem `@converter(".a", ".b")` – GUI i CLI pobierają formaty z rejestru,
  więc nie wymagają zmian.
- GUI i CLI wywołują tę samą funkcję `convert()`, która waliduje dane i uruchamia konwerter.
- GUI uruchamia konwersję w wątku roboczym; wynik wraca do wątku głównego przez kolejkę
  (`queue.Queue` + `root.after`), bo widżetów Tkinter nie wolno zmieniać z innego wątku.
- LibreOffice uruchamiany jest przez `subprocess.run` z listą argumentów (bez `shell=True`),
  z limitem czasu i sprawdzeniem kodu zakończenia oraz istnienia pliku wynikowego.

## Dane testowe (`samples/`)

| Plik | Co sprawdza | Oczekiwany wynik |
|---|---|---|
| `studenci.csv` | polskie znaki, pusta komórka | JSON z tymi samymi nagłówkami w tej samej kolejności, pusta komórka jako `""` |
| `studenci.json` | konwersja JSON → CSV | CSV z nagłówkami z kluczy obiektów, poprawne polskie znaki |
| `bledny.json` | brakujący przecinek | komunikat „Niepoprawny JSON… (wiersz 3…)”, brak pliku wynikowego |
| `zla_liczba_pol.csv` | nadmiarowe pole w wierszu | komunikat „Wiersz 2 ma inną liczbę pól…” |
| `notatka.txt` | 3 akapity, polskie znaki, złamanie wiersza | DOCX z 3 akapitami |
| `notatka.docx` | dokument Word | TXT z 3 akapitami; PDF otwierający się w przeglądarce PDF |
| `dokument.odt` | dokument OpenDocument | PDF otwierający się w przeglądarce PDF |
| `uszkodzony.docx` | plik tekstowy z rozszerzeniem .docx | komunikat „…jest uszkodzony lub nie jest dokumentem Word…” |

## Znane ograniczenia

- Nie jest zachowywane złożone formatowanie, tabele, obrazy, przypisy ani makra (zgodnie z zakresem projektu).
- CSV musi używać przecinka jako separatora (pliki ze średnikiem dadzą jedną kolumnę lub błąd liczby pól).
- Typy liczbowe z JSON są w CSV zapisywane jako tekst; przy powrocie do JSON pozostają tekstem.
- W trybie linii poleceń istniejący plik wynikowy jest nadpisywany bez pytania (w GUI – z pytaniem).
- Konwersje do PDF wymagają zainstalowanego LibreOffice.

## Źródła, biblioteki i narzędzia AI

- Dokumentacja Pythona: [csv](https://docs.python.org/3/library/csv.html),
  [json](https://docs.python.org/3/library/json.html),
  [tkinter.filedialog](https://docs.python.org/3/library/dialog.html),
  [subprocess](https://docs.python.org/3/library/subprocess.html),
  [threading](https://docs.python.org/3/library/threading.html)
- [python-docx](https://python-docx.readthedocs.io/) – tworzenie i odczyt plików DOCX
- [LibreOffice – parametry wiersza poleceń](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)
- [pytest](https://docs.pytest.org/) – testy automatyczne
- Wzorzec rejestru konwerterów z instrukcji projektowej
- **Narzędzia AI:** przy tworzeniu projektu korzystano z asystenta Claude
  wspomagał między innymi przy propozycjach kodu konwerterów i GUI, przygotowaniu testów i dokumentacji. 
## Autor

<Krystian Kulczycki, 105499>
