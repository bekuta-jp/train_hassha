from __future__ import annotations

from datetime import datetime, timedelta
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .config import DEFAULT_LINE
from .metadata import load_app_metadata
from .settings import load_app_settings
from .storage import get_line_data_path, load_line_data
from .timetable import (
    DAY_TYPE_LABELS,
    current_day_type,
    fetch_and_save_line,
    get_direction_names,
    get_next_departures,
    get_station_names,
)


CARD_TITLES = ["先発", "次発", "次々発"]
CARD_BACKGROUND = "#fffaf1"
CARD_ALERT_BACKGROUND = "#fff1ef"
CARD_TIME_NORMAL = "#d96c06"
CARD_TIME_ALERT = "#d64541"
CARD_DEST_NORMAL = "#17313b"
CARD_DEST_ALERT = "#d64541"
CARD_META_NORMAL = "#5b7078"


class TrainHasshaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.metadata = load_app_metadata()
        self.root.title(f"トレイン発車 ver{self.metadata.version}")
        self.root.geometry("980x740")
        self.root.minsize(900, 640)

        self.data: dict | None = None
        self.settings = load_app_settings()
        self.fetch_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self.station_var = tk.StringVar()
        self.direction_var = tk.StringVar()
        self.clock_var = tk.StringVar()
        self.clock_mode_var = tk.StringVar(value="実時間")
        self.day_type_var = tk.StringVar()
        self.status_var = tk.StringVar(value="保存済み時刻表を読み込み中です。")
        self.fetch_info_var = tk.StringVar(value="未取得")
        self.path_var = tk.StringVar(value=str(get_line_data_path(DEFAULT_LINE.line_id)))
        self.debug_mode_var = tk.BooleanVar(value=False)
        self.debug_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        self.card_vars: list[dict[str, tk.StringVar]] = []
        self.card_widgets: list[dict[str, tk.Widget]] = []
        self._blink_on = False

        self._configure_style()
        self._build_ui()
        self._load_saved_data()
        self._tick()
        self._poll_fetch_queue()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        self.root.configure(bg="#f7f1e3")

        style.configure("App.TFrame", background="#f7f1e3")
        style.configure("Panel.TFrame", background="#fffaf1")
        style.configure("Header.TLabel", background="#f7f1e3", foreground="#114b5f", font=("Helvetica", 20, "bold"))
        style.configure("SubHeader.TLabel", background="#f7f1e3", foreground="#44646f", font=("Helvetica", 11))
        style.configure(
            "Version.TLabel",
            background="#f7f1e3",
            foreground="#114b5f",
            font=("Helvetica", 11, "bold"),
            padding=(12, 6),
        )
        style.configure("Label.TLabel", background="#fffaf1", foreground="#17313b", font=("Helvetica", 11))
        style.configure("Value.TLabel", background="#fffaf1", foreground="#114b5f", font=("Helvetica", 12, "bold"))
        style.configure("ClockMode.TLabel", background="#fffaf1", foreground="#44646f", font=("Helvetica", 11, "bold"))
        style.configure("Status.TLabel", background="#114b5f", foreground="#ffffff", padding=10, font=("Helvetica", 10))
        style.configure("Card.TLabelframe", background="#fffaf1", bordercolor="#7cc6b6", borderwidth=2, relief="solid")
        style.configure("Card.TLabelframe.Label", background="#fffaf1", foreground="#114b5f", font=("Helvetica", 12, "bold"))
        style.configure("Action.TButton", font=("Helvetica", 11, "bold"))
        style.configure("Debug.TCheckbutton", background="#fffaf1", foreground="#17313b", font=("Helvetica", 11, "bold"))

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=20, style="App.TFrame")
        root_frame.pack(fill="both", expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(2, weight=1)

        header_frame = ttk.Frame(root_frame, style="App.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(header_frame, text="トレイン発車", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header_frame, text=f"ver{self.metadata.version}", style="Version.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(
            header_frame,
            text="神戸新交通ポートアイランド線の保存済み時刻表から、先発・次発・次々発を表示します。",
            style="SubHeader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        control_panel = ttk.Frame(root_frame, padding=18, style="Panel.TFrame")
        control_panel.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        control_panel.columnconfigure(1, weight=1)
        control_panel.columnconfigure(3, weight=1)
        control_panel.columnconfigure(5, weight=1)

        ttk.Label(control_panel, text="駅名", style="Label.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        station_combo = ttk.Combobox(control_panel, textvariable=self.station_var, state="readonly")
        station_combo.grid(row=0, column=1, sticky="ew", pady=6)
        station_combo.bind("<<ComboboxSelected>>", self._on_station_changed)
        self.station_combo = station_combo

        ttk.Label(control_panel, text="方面", style="Label.TLabel").grid(row=0, column=2, sticky="w", padx=(18, 10), pady=6)
        direction_combo = ttk.Combobox(control_panel, textvariable=self.direction_var, state="readonly")
        direction_combo.grid(row=0, column=3, sticky="ew", pady=6)
        direction_combo.bind("<<ComboboxSelected>>", self._refresh_departures)
        self.direction_combo = direction_combo

        fetch_button = ttk.Button(control_panel, text="時刻表を取得して保存", style="Action.TButton", command=self._start_fetch)
        fetch_button.grid(row=0, column=4, sticky="e", padx=(18, 0), pady=6)
        self.fetch_button = fetch_button

        ttk.Label(control_panel, text="現在時刻", style="Label.TLabel").grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=(10, 6))
        clock_panel = ttk.Frame(control_panel, style="Panel.TFrame")
        clock_panel.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(8, 6))
        clock_panel.columnconfigure(0, weight=1)

        ttk.Label(clock_panel, textvariable=self.clock_mode_var, style="ClockMode.TLabel").grid(row=0, column=0, sticky="w")
        self.clock_label = tk.Label(
            clock_panel,
            textvariable=self.clock_var,
            bg="#fffaf1",
            fg="#114b5f",
            font=("Helvetica", 34, "bold"),
            anchor="w",
            justify="left",
        )
        self.clock_label.grid(row=1, column=0, sticky="w", pady=(2, 4))
        ttk.Label(clock_panel, text="適用ダイヤ", style="Label.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Label(clock_panel, textvariable=self.day_type_var, style="Value.TLabel").grid(row=3, column=0, sticky="w")

        debug_panel = ttk.Frame(control_panel, style="Panel.TFrame")
        debug_panel.grid(row=1, column=4, columnspan=2, sticky="e", padx=(18, 0), pady=(8, 6))

        debug_toggle = ttk.Checkbutton(
            debug_panel,
            text="デバッグ時刻を使う",
            variable=self.debug_mode_var,
            command=self._on_debug_mode_toggled,
            style="Debug.TCheckbutton",
        )
        debug_toggle.grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 6))

        ttk.Label(debug_panel, text="日時", style="Label.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8))
        debug_entry = ttk.Entry(debug_panel, textvariable=self.debug_time_var, width=22)
        debug_entry.grid(row=1, column=1, columnspan=2, sticky="ew")
        self.debug_entry = debug_entry

        ttk.Button(debug_panel, text="反映", command=self._apply_debug_time).grid(row=1, column=3, sticky="ew", padx=(8, 0))
        ttk.Button(debug_panel, text="現在", command=self._set_debug_now).grid(row=1, column=4, sticky="ew", padx=(8, 0))
        ttk.Button(debug_panel, text="-1分", command=lambda: self._shift_debug_time(-1)).grid(row=2, column=1, sticky="ew", pady=(8, 0))
        ttk.Button(debug_panel, text="+1分", command=lambda: self._shift_debug_time(1)).grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Button(debug_panel, text="-10分", command=lambda: self._shift_debug_time(-10)).grid(row=2, column=3, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Button(debug_panel, text="+10分", command=lambda: self._shift_debug_time(10)).grid(row=2, column=4, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Label(control_panel, text="最終取得", style="Label.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Label(control_panel, textvariable=self.fetch_info_var, style="Value.TLabel").grid(row=2, column=1, columnspan=5, sticky="w", pady=6)

        ttk.Label(control_panel, text="保存先", style="Label.TLabel").grid(row=3, column=0, sticky="nw", padx=(0, 10), pady=6)
        ttk.Label(control_panel, textvariable=self.path_var, style="Label.TLabel", wraplength=760).grid(
            row=3,
            column=1,
            columnspan=5,
            sticky="w",
            pady=6,
        )

        card_area = ttk.Frame(root_frame, style="App.TFrame")
        card_area.grid(row=2, column=0, sticky="nsew")
        for index in range(3):
            card_area.columnconfigure(index, weight=1)

        for index, title in enumerate(CARD_TITLES):
            card = ttk.LabelFrame(card_area, text=title, padding=18, style="Card.TLabelframe")
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0), pady=(0, 16))
            card.columnconfigure(0, weight=1)

            time_var = tk.StringVar(value="--:--")
            dest_var = tk.StringVar(value="保存済み時刻表がありません")
            meta_var = tk.StringVar(value="")

            time_label = tk.Label(
                card,
                textvariable=time_var,
                bg=CARD_BACKGROUND,
                fg=CARD_TIME_NORMAL,
                font=("Helvetica", 28, "bold"),
                anchor="w",
                justify="left",
            )
            time_label.grid(row=0, column=0, sticky="w")
            dest_label = tk.Label(
                card,
                textvariable=dest_var,
                bg=CARD_BACKGROUND,
                fg=CARD_DEST_NORMAL,
                font=("Helvetica", 14, "bold"),
                wraplength=240,
                anchor="w",
                justify="left",
            )
            dest_label.grid(row=1, column=0, sticky="w", pady=(16, 8))
            meta_label = tk.Label(
                card,
                textvariable=meta_var,
                bg=CARD_BACKGROUND,
                fg=CARD_META_NORMAL,
                font=("Helvetica", 10),
                wraplength=240,
                anchor="w",
                justify="left",
            )
            meta_label.grid(row=2, column=0, sticky="w")

            self.card_vars.append({"time": time_var, "destination": dest_var, "meta": meta_var})
            self.card_widgets.append({"frame": card, "time": time_label, "destination": dest_label, "meta": meta_label})

        status_label = ttk.Label(root_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        status_label.grid(row=3, column=0, sticky="ew")

    def _load_saved_data(self) -> None:
        try:
            self.data = load_line_data(DEFAULT_LINE.line_id)
        except FileNotFoundError:
            self.data = None
            self.status_var.set("保存済み時刻表がまだありません。「時刻表を取得して保存」を押してください。")
            self.fetch_info_var.set("未取得")
            self._set_empty_cards("保存済み時刻表がありません", "先に取得ボタンで保存してください。")
            return

        self.fetch_info_var.set(self.data.get("fetched_at", "不明"))
        self._populate_station_choices()
        self.status_var.set("保存済み時刻表を読み込みました。")

    def _populate_station_choices(self) -> None:
        if not self.data:
            return

        station_names = get_station_names(self.data)
        self.station_combo["values"] = station_names

        preferred_station = self.settings.default_station_name
        if station_names and self.station_var.get() not in station_names:
            self.station_var.set(preferred_station if preferred_station in station_names else station_names[0])

        self._populate_direction_choices()

    def _populate_direction_choices(self) -> None:
        if not self.data or not self.station_var.get():
            self.direction_combo["values"] = []
            self.direction_var.set("")
            self._set_empty_cards("方面が選択されていません", "")
            return

        direction_names = get_direction_names(self.data, self.station_var.get())
        self.direction_combo["values"] = direction_names

        preferred_direction = self.settings.default_direction_name
        if direction_names and self.direction_var.get() not in direction_names:
            self.direction_var.set(preferred_direction if preferred_direction in direction_names else direction_names[0])

        self._refresh_departures()

    def _set_empty_cards(self, message: str, detail: str) -> None:
        for index, card in enumerate(self.card_vars):
            card["time"].set("--:--")
            card["destination"].set(message)
            card["meta"].set(detail)
            self._set_card_alert(index, False)

    def _parse_debug_time(self) -> datetime | None:
        raw = self.debug_time_var.get().strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(raw, fmt)
                if fmt == "%Y-%m-%d %H:%M":
                    return parsed.replace(second=0)
                return parsed
            except ValueError:
                continue
        return None

    def _get_reference_now(self) -> datetime:
        if not self.debug_mode_var.get():
            self.clock_mode_var.set("実時間")
            return datetime.now()

        parsed = self._parse_debug_time()
        if parsed is None:
            self.clock_mode_var.set("デバッグ時刻")
            self.status_var.set("デバッグ時刻の形式が不正です。YYYY-MM-DD HH:MM[:SS] で入力してください。")
            return datetime.now()

        self.clock_mode_var.set("デバッグ時刻")
        return parsed

    def _apply_debug_time(self) -> None:
        parsed = self._parse_debug_time()
        if parsed is None:
            messagebox.showerror("トレイン発車", "デバッグ時刻は YYYY-MM-DD HH:MM[:SS] で入力してください。")
            return

        self.debug_time_var.set(parsed.strftime("%Y-%m-%d %H:%M:%S"))
        self.debug_mode_var.set(True)
        self.status_var.set("デバッグ時刻を反映しました。")
        self._refresh_departures()

    def _set_debug_now(self) -> None:
        current = datetime.now().replace(microsecond=0)
        self.debug_time_var.set(current.strftime("%Y-%m-%d %H:%M:%S"))
        self.status_var.set("デバッグ時刻を現在時刻に合わせました。")
        if self.debug_mode_var.get():
            self._refresh_departures()

    def _shift_debug_time(self, minutes: int) -> None:
        base = self._parse_debug_time()
        if base is None:
            base = datetime.now().replace(microsecond=0)
        shifted = base + timedelta(minutes=minutes)
        self.debug_time_var.set(shifted.strftime("%Y-%m-%d %H:%M:%S"))
        self.debug_mode_var.set(True)
        self.status_var.set(f"デバッグ時刻を {minutes:+d} 分動かしました。")
        self._refresh_departures()

    def _on_debug_mode_toggled(self) -> None:
        if self.debug_mode_var.get():
            if self._parse_debug_time() is None:
                self._set_debug_now()
            self.status_var.set("デバッグ時刻モードで表示しています。")
        else:
            self.status_var.set("実時間モードに戻しました。")
        self._refresh_departures()

    def _set_card_alert(self, index: int, active: bool) -> None:
        widgets = self.card_widgets[index]
        background = CARD_ALERT_BACKGROUND if active else CARD_BACKGROUND
        time_color = CARD_TIME_ALERT if active and self._blink_on else CARD_TIME_NORMAL
        dest_color = CARD_DEST_ALERT if active and self._blink_on else CARD_DEST_NORMAL

        widgets["time"].configure(bg=background, fg=time_color)
        widgets["destination"].configure(bg=background, fg=dest_color)
        widgets["meta"].configure(bg=background, fg=CARD_META_NORMAL)

    def _on_station_changed(self, _: object) -> None:
        self._populate_direction_choices()

    def _refresh_departures(self, _: object | None = None) -> None:
        now = self._get_reference_now()
        self.clock_var.set(now.strftime("%Y-%m-%d %H:%M:%S"))
        self.day_type_var.set(DAY_TYPE_LABELS[current_day_type(now.date())])

        if not self.data or not self.station_var.get() or not self.direction_var.get():
            return

        departures = get_next_departures(self.data, self.station_var.get(), self.direction_var.get(), now=now, count=3)

        if not departures:
            self._set_empty_cards("本日の残り列車がありません", "保存済み時刻表を確認してください。")
            return

        for index, card in enumerate(self.card_vars):
            if index >= len(departures):
                card["time"].set("--:--")
                card["destination"].set("該当なし")
                card["meta"].set("")
                self._set_card_alert(index, False)
                continue

            departure = departures[index]
            card["time"].set(departure["time"])
            card["destination"].set(departure["destination"] or self.direction_var.get())

            when_label = "翌日" if departure["is_next_day"] else "当日"
            meta = f"{when_label} {departure['date_label']} {departure['day_type_label']}ダイヤ"
            if departure["symbol"]:
                meta += f" / 種別記号: {departure['symbol']}"
            if departure["timetable_time"] != departure["time"]:
                meta += f" / 時刻表表記: {departure['timetable_time']}"
            if departure["minutes_until"] is not None:
                meta += f" / あと {departure['minutes_until']} 分"
            card["meta"].set(meta)
            self._set_card_alert(index, departure["minutes_until"] <= 5)

    def _start_fetch(self) -> None:
        self.fetch_button.state(["disabled"])
        self.status_var.set("公式サイトから時刻表を取得して保存しています。")

        worker = threading.Thread(target=self._fetch_worker, daemon=True)
        worker.start()

    def _fetch_worker(self) -> None:
        try:
            data, path = fetch_and_save_line(DEFAULT_LINE)
        except Exception as exc:  # noqa: BLE001
            self.fetch_queue.put(("error", exc))
            return

        self.fetch_queue.put(("success", {"data": data, "path": path}))

    def _poll_fetch_queue(self) -> None:
        try:
            event, payload = self.fetch_queue.get_nowait()
        except queue.Empty:
            self.root.after(150, self._poll_fetch_queue)
            return

        self.fetch_button.state(["!disabled"])

        if event == "success":
            assert isinstance(payload, dict)
            self.data = payload["data"]
            self.path_var.set(str(payload["path"]))
            self.fetch_info_var.set(self.data.get("fetched_at", "不明"))
            self._populate_station_choices()
            self.status_var.set("時刻表を取得して保存しました。保存済みデータで案内を更新しています。")
            messagebox.showinfo("トレイン発車", "時刻表を取得して保存しました。")
        else:
            assert isinstance(payload, Exception)
            self.status_var.set("時刻表の取得に失敗しました。保存済みデータがあればそのまま利用できます。")
            messagebox.showerror("トレイン発車", str(payload))

        self.root.after(150, self._poll_fetch_queue)

    def _tick(self) -> None:
        self._blink_on = not self._blink_on
        self._refresh_departures()
        self.root.after(1000, self._tick)


def launch_app() -> None:
    root = tk.Tk()
    TrainHasshaApp(root)
    root.mainloop()
