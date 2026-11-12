
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from converters import available_targets, convert, output_path, setup_logging, supported_sources


class ConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Konwerter plików")
        self.root.resizable(False, False)

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.format_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Wybierz plik do konwersji.")

        self.results: queue.Queue = queue.Queue()  # wyniki z wątku roboczego
        self.working = False

        self._build_widgets()
        for var in (self.source_var, self.output_var, self.format_var):
            var.trace_add("write", lambda *_: self._update_button())
        self._update_button()

    # ------------------------------------------------------------ układ okna

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.grid()

        ttk.Label(frame, text="Plik wejściowy:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source_var, width=50, state="readonly").grid(row=0, column=1, padx=6)
        ttk.Button(frame, text="Wybierz…", command=self.choose_file).grid(row=0, column=2)

        ttk.Label(frame, text="Format docelowy:").grid(row=1, column=0, sticky="w", pady=4)
        self.format_box = ttk.Combobox(frame, textvariable=self.format_var, state="disabled", width=12)
        self.format_box.grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(frame, text="Katalog zapisu:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_var, width=50, state="readonly").grid(row=2, column=1, padx=6)
        ttk.Button(frame, text="Wybierz…", command=self.choose_dir).grid(row=2, column=2)

        self.convert_button = ttk.Button(frame, text="Konwertuj", command=self.start_conversion)
        self.convert_button.grid(row=3, column=0, columnspan=3, pady=(12, 6))

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=420)
        self.progress.grid(row=4, column=0, columnspan=3, pady=4)

        ttk.Label(frame, textvariable=self.status_var, wraplength=480).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(4, 0))

    # ------------------------------------------------------------ wybór plików

    def choose_file(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in supported_sources())
        path = filedialog.askopenfilename(
            title="Wybierz plik",
            filetypes=[("Obsługiwane pliki", patterns), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return  # użytkownik zamknął okno wyboru

        source = Path(path)
        self.source_var.set(str(source))
        if not self.output_var.get():
            self.output_var.set(str(source.parent))  # domyślnie folder pliku wejściowego

        targets = available_targets(source)
        self.format_box["values"] = targets
        if targets:
            self.format_box.configure(state="readonly")  # tylko wybór z listy, bez wpisywania
            self.format_var.set(targets[0])
            self.status_var.set(f"Dostępne formaty dla {source.suffix}: {', '.join(targets)}")
        else:
            self.format_box.configure(state="disabled")
            self.format_var.set("")
            self.status_var.set(
                f"Pliki {source.suffix or 'bez rozszerzenia'} nie są obsługiwane. "
                f"Wybierz plik: {', '.join(supported_sources())}")

    def choose_dir(self) -> None:
        path = filedialog.askdirectory(title="Wybierz katalog zapisu")
        if path:
            self.output_var.set(path)

    def _update_button(self) -> None:
        """Przycisk aktywny tylko, gdy wszystko wybrano i nic się nie konwertuje."""
        ready = all(v.get() for v in (self.source_var, self.output_var, self.format_var))
        self.convert_button.configure(state="normal" if ready and not self.working else "disabled")

    # ------------------------------------------------------------ konwersja

    def start_conversion(self) -> None:
        source = Path(self.source_var.get())
        fmt = self.format_var.get()
        out_dir = Path(self.output_var.get())

        target = output_path(source, fmt, out_dir)
        if target.exists() and not messagebox.askyesno(
                "Plik już istnieje", f"Plik {target.name} już istnieje w wybranym katalogu.\n\nNadpisać go?"):
            self.status_var.set("Anulowano – istniejący plik nie został zmieniony.")
            return

        self.working = True
        self._update_button()
        self.progress.start(10)
        self.status_var.set(f"Trwa konwersja {source.name} → {fmt}…")

        # Konwersja w osobnym wątku, żeby okno nie „zamarzło” (LibreOffice może działać kilka sekund)
        threading.Thread(target=self._worker, args=(source, fmt, out_dir), daemon=True).start()
        self.root.after(100, self._check_result)

    def _worker(self, source: Path, fmt: str, out_dir: Path) -> None:
        """Działa w wątku roboczym – NIE dotyka widżetów, tylko wkłada wynik do kolejki."""
        try:
            self.results.put(("ok", convert(source, fmt, out_dir)))
        except (ValueError, RuntimeError) as e:
            self.results.put(("error", str(e)))
        except Exception as e:  # nieprzewidziany błąd – pokazujemy go zamiast wywracać program
            self.results.put(("error", f"Nieoczekiwany błąd: {e}. Szczegóły zapisano w pliku konwerter.log."))

    def _check_result(self) -> None:
        """Wątek główny co 100 ms sprawdza, czy wątek roboczy skończył."""
        try:
            status, value = self.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self._check_result)
            return

        self.progress.stop()
        self.progress["value"] = 0  # czyści pasek po zatrzymaniu
        self.working = False
        self._update_button()
        if status == "ok":
            self.status_var.set(f"Gotowe: {value}")
            messagebox.showinfo("Konwersja zakończona", f"Zapisano plik:\n{value}")
        else:
            self.status_var.set(f"Błąd: {value}")
            messagebox.showerror("Błąd konwersji", value)


if __name__ == "__main__":
    setup_logging()
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()
