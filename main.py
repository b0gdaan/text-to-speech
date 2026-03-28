"""
Business English TTS — D:/said
edge-tts (Microsoft Neural) · customtkinter GUI
"""

import os
import asyncio
import imageio_ffmpeg
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import re
import json
import tempfile
import shutil
import traceback
import subprocess
from pathlib import Path

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ── Голоса — только проверенные рабочие ───────────────────────────────────────
VOICES = {
    "🇺🇸 Guy         (муж)": "en-US-GuyNeural",
    "🇺🇸 Christopher (муж)": "en-US-ChristopherNeural",
    "🇺🇸 Eric        (муж)": "en-US-EricNeural",
    "🇺🇸 Roger       (муж)": "en-US-RogerNeural",
    "🇺🇸 Steffan     (муж)": "en-US-SteffanNeural",
    "🇺🇸 Jenny       (жен)": "en-US-JennyNeural",
    "🇺🇸 Aria        (жен)": "en-US-AriaNeural",
    "🇺🇸 Michelle    (жен)": "en-US-MichelleNeural",
    "🇬🇧 Ryan        (муж)": "en-GB-RyanNeural",
    "🇬🇧 Thomas      (муж)": "en-GB-ThomasNeural",
    "🇬🇧 Sonia       (жен)": "en-GB-SoniaNeural",
    "🇬🇧 Libby       (жен)": "en-GB-LibbyNeural",
    "🇬🇧 Maisie      (жен)": "en-GB-MaisieNeural",
    "🇦🇺 William     (муж)": "en-AU-WilliamNeural",
    "🇦🇺 Natasha     (жен)": "en-AU-NatashaNeural",
}
VOICE_KEYS = list(VOICES.keys())

# Дефолтные голоса по очереди (муж/жен чередуются)
DEFAULT_VOICES = [
    "🇺🇸 Guy         (муж)",
    "🇬🇧 Sonia       (жен)",
    "🇬🇧 Ryan        (муж)",
    "🇺🇸 Aria        (жен)",
]

PAUSE_SEC = 0.45


# ── Библиотека диалогов ────────────────────────────────────────────────────────
def load_library() -> dict:
    lib_path = Path(__file__).parent / "dialogues" / "library.json"
    if lib_path.exists():
        with open(lib_path, encoding="utf-8") as f:
            return json.load(f)
    return {"modules": []}


LIBRARY = load_library()


def build_dialogue_tree() -> dict:
    tree = {}
    for mod in LIBRARY.get("modules", []):
        tree[mod["title"]] = {}
        for les in mod.get("lessons", []):
            tree[mod["title"]][les["title"]] = [
                (d["title"], d.get("speakers", []), d["text"])
                for d in les.get("dialogues", [])
            ]
    return tree


TREE = build_dialogue_tree()
MODULES = list(TREE.keys())


def safe_name(s: str) -> str:
    """Безопасное имя файла/папки."""
    return re.sub(r'[\\/:*?"<>|]', "_", s).strip()[:50]


# ── Ядро синтеза (без GUI) ─────────────────────────────────────────────────────
def synth_dialogue(text: str, voice_map: dict, out_path: str, rate_str: str,
                   log_cb=None, progress_cb=None) -> bool:
    """
    Синтезирует диалог в MP3-файл.
    voice_map: {speaker_name: voice_id}
    Возвращает True при успехе.
    """
    import edge_tts

    lines = re.findall(r'\[([^\]]+)\]:\s*(.+)', text)
    if not lines:
        if log_cb: log_cb("❌ Нет реплик в формате [Имя]: текст")
        return False

    tmp_dir = tempfile.mkdtemp()
    try:
        # Тишина между репликами
        sil = os.path.join(tmp_dir, "sil.mp3")
        subprocess.run([FFMPEG, "-y", "-f", "lavfi",
                        "-i", f"anullsrc=r=24000:cl=mono",
                        "-t", str(PAUSE_SEC), "-q:a", "9", sil],
                       capture_output=True)

        loop = asyncio.new_event_loop()
        mp3_files = []

        async def synth_one(speaker, line_text, idx):
            vid = voice_map.get(speaker)
            if not vid:
                if log_cb: log_cb(f"  ⚠ {speaker} — голос не задан, пропуск")
                return None
            preview = line_text[:50] + ("…" if len(line_text) > 50 else "")
            if log_cb: log_cb(f"  [{idx+1}/{len(lines)}] {speaker}: {preview}")
            p = os.path.join(tmp_dir, f"line_{idx:04d}.mp3")
            await edge_tts.Communicate(line_text, vid, rate=rate_str).save(p)
            return p

        for idx, (spk, lt) in enumerate(lines):
            p = loop.run_until_complete(synth_one(spk, lt, idx))
            if p and os.path.exists(p):
                mp3_files.append(p)
                mp3_files.append(sil)
            if progress_cb:
                progress_cb((idx + 1) / len(lines))

        loop.close()

        if not mp3_files:
            if log_cb: log_cb("❌ Нет аудио-сегментов")
            return False

        # Склейка
        cl = os.path.join(tmp_dir, "list.txt")
        with open(cl, "w", encoding="utf-8") as f:
            for p in mp3_files:
                f.write(f"file '{p}'\n")

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        r = subprocess.run(
            [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cl, "-c", "copy", out_path],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            if log_cb: log_cb(f"❌ ffmpeg: {r.stderr[-300:]}")
            return False

        return True

    finally:
        # Не удаляем tmp если это output_file (для одиночного режима)
        if tmp_dir != os.path.dirname(out_path):
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Business English TTS  ·  D:\\said")
        self.geometry("1320x860")
        self.minsize(1000, 680)

        self.output_file: str | None = None
        self.is_playing = False
        self.voice_dropdowns: dict[str, ctk.CTkComboBox] = {}
        self._busy = False          # блокировка двойной генерации

        self._init_audio()
        self._build_ui()

        self.after(200, lambda: (
            self.status_lbl.configure(text="✅ Готово (edge-tts)", text_color="lightgreen"),
            self._set_gen_btns(True)
        ))

    # ── Audio ──────────────────────────────────────────────────────────────────
    def _init_audio(self):
        try:
            import pygame
            pygame.mixer.init(frequency=24000)
            self._pg = pygame
        except Exception as e:
            self._pg = None

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self._build_library_panel()
        self._build_center_panel()
        self._build_control_panel()

    # ══ ЛЕВАЯ ПАНЕЛЬ: библиотека ══════════════════════════════════════════════
    def _build_library_panel(self):
        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=0, padx=(12, 5), pady=12, sticky="nsew")
        frm.grid_rowconfigure(4, weight=1)
        frm.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frm, text="📚 Библиотека",
                     font=ctk.CTkFont(size=15, weight="bold")
                     ).grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")

        ctk.CTkLabel(frm, text="Модуль", font=ctk.CTkFont(size=11), text_color="gray"
                     ).grid(row=1, column=0, padx=12, pady=(0, 2), sticky="w")
        self.mod_cb = ctk.CTkComboBox(frm, values=MODULES, command=self._on_module,
                                       state="readonly")
        self.mod_cb.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        if MODULES:
            self.mod_cb.set(MODULES[0])

        ctk.CTkLabel(frm, text="Урок / Диалог", font=ctk.CTkFont(size=11),
                     text_color="gray"
                     ).grid(row=3, column=0, padx=12, pady=(0, 2), sticky="w")

        self.lesson_scroll = ctk.CTkScrollableFrame(frm)
        self.lesson_scroll.grid(row=4, column=0, padx=12, pady=0, sticky="nsew")
        self.lesson_scroll.grid_columnconfigure(0, weight=1)

        # Кнопки внизу библиотеки
        btn_frm = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frm.grid(row=5, column=0, padx=12, pady=(8, 4), sticky="ew")
        btn_frm.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frm, text="⬆  Загрузить",
                      command=self._load_selected_dialogue, height=36
                      ).grid(row=0, column=0, padx=(0, 3), sticky="ew")

        self.gen_one_lib_btn = ctk.CTkButton(
            btn_frm, text="🎙  Этот",
            command=self._gen_selected_from_lib,
            height=36, fg_color="#1a5c8a", hover_color="#134468"
        )
        self.gen_one_lib_btn.grid(row=0, column=1, padx=(3, 0), sticky="ew")

        self.batch_btn = ctk.CTkButton(
            frm, text="⚡  Сгенерировать ВСЁ из библиотеки",
            command=self._start_batch,
            height=40,
            fg_color="#5a2d8a", hover_color="#3e1e60",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.batch_btn.grid(row=6, column=0, padx=12, pady=(0, 12), sticky="ew")

        self._radio_var = tk.StringVar(value="")
        self._dialogue_map: dict[str, tuple] = {}  # key → (speakers, text)

        if MODULES:
            self._on_module(MODULES[0])

    def _on_module(self, mod_name: str):
        for w in self.lesson_scroll.winfo_children():
            w.destroy()
        self._dialogue_map.clear()
        self._radio_var.set("")

        row = 0
        for les_title, dialogues in TREE.get(mod_name, {}).items():
            ctk.CTkLabel(self.lesson_scroll, text=les_title,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#7ec8e3", wraplength=210, justify="left"
                         ).grid(row=row, column=0, padx=4, pady=(10, 2), sticky="w")
            row += 1
            for dial_title, speakers, dial_text in dialogues:
                key = f"{les_title}||{dial_title}"
                self._dialogue_map[key] = (speakers, dial_text)
                rb = ctk.CTkRadioButton(self.lesson_scroll, text=dial_title,
                                         variable=self._radio_var, value=key,
                                         font=ctk.CTkFont(size=11))
                rb.grid(row=row, column=0, padx=12, pady=2, sticky="w")
                row += 1

    def _load_selected_dialogue(self):
        key = self._radio_var.get()
        if not key:
            messagebox.showinfo("Подсказка", "Выберите диалог из списка")
            return
        _, text = self._dialogue_map[key]
        # Переключиться на вкладку "Библиотека"
        self.tabs.set("📖 Из библиотеки")
        self.lib_text.configure(state="normal")
        self.lib_text.delete("1.0", "end")
        self.lib_text.insert("1.0", text)
        self.lib_text.configure(state="disabled")
        self._parse_speakers_from(text)

    def _gen_selected_from_lib(self):
        """Загрузить выбранный диалог и сразу сгенерировать."""
        key = self._radio_var.get()
        if not key:
            messagebox.showinfo("Подсказка", "Выберите диалог из списка")
            return
        self._load_selected_dialogue()
        self._start_gen()

    # ══ ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: вкладки ═══════════════════════════════════════════
    def _build_center_panel(self):
        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=1, padx=5, pady=12, sticky="nsew")
        frm.grid_rowconfigure(0, weight=1)
        frm.grid_columnconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(frm)
        self.tabs.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # ── Вкладка 1: Из библиотеки ──────────────────────────────────────────
        tab1 = self.tabs.add("📖 Из библиотеки")
        tab1.grid_rowconfigure(0, weight=1)
        tab1.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tab1, text="Выберите диалог слева → «Загрузить»",
                     font=ctk.CTkFont(size=11), text_color="gray"
                     ).grid(row=0, column=0, sticky="nw", padx=4, pady=(0, 4))

        self.lib_text = ctk.CTkTextbox(tab1,
                                        font=ctk.CTkFont(family="Consolas", size=13),
                                        wrap="word", state="disabled")
        self.lib_text.grid(row=1, column=0, sticky="nsew")
        tab1.grid_rowconfigure(1, weight=1)

        # ── Вкладка 2: Свой текст ─────────────────────────────────────────────
        tab2 = self.tabs.add("✏️ Свой текст")
        tab2.grid_rowconfigure(1, weight=1)
        tab2.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tab2,
                     text="Формат:  [Имя]: текст реплики   (до 4 персонажей)",
                     font=ctk.CTkFont(size=11), text_color="gray"
                     ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 4))

        self.custom_text = ctk.CTkTextbox(tab2,
                                           font=ctk.CTkFont(family="Consolas", size=13),
                                           wrap="word")
        self.custom_text.grid(row=1, column=0, sticky="nsew")

        # Вставить пример
        example = (
            "[Alex]: Good morning, Sarah. Have you reviewed the proposal?\n"
            "[Sarah]: Yes, I went through it last night. I have a few concerns.\n"
            "[Alex]: Let's go over them one by one.\n"
            "[Sarah]: Sure. First, the delivery terms seem quite tight."
        )
        self.custom_text.insert("1.0", example)

        ctk.CTkButton(tab2, text="🔍  Определить персонажей",
                      command=self._parse_speakers_custom, height=34
                      ).grid(row=2, column=0, padx=0, pady=(8, 0), sticky="ew")

        # Следить за переключением вкладок
        self.tabs.configure(command=self._on_tab_switch)

    def _on_tab_switch(self):
        tab = self.tabs.get()
        if tab == "✏️ Свой текст":
            self._parse_speakers_custom()

    def _parse_speakers_custom(self):
        text = self.custom_text.get("1.0", "end")
        self._parse_speakers_from(text)

    def _parse_speakers_from(self, text: str):
        speakers = list(dict.fromkeys(re.findall(r'\[([^\]]+)\]:', text)))[:4]
        for w in self.voices_frame.winfo_children():
            w.destroy()
        self.voice_dropdowns.clear()

        if not speakers:
            ctk.CTkLabel(self.voices_frame,
                         text="Нет реплик.\nФормат: [Имя]: текст",
                         text_color="gray").grid(padx=10, pady=10)
            return

        for i, sp in enumerate(speakers):
            ctk.CTkLabel(self.voices_frame, text=f"👤  {sp}",
                         font=ctk.CTkFont(size=13, weight="bold")
                         ).grid(row=i * 2, column=0, padx=10, pady=(10, 2), sticky="w")
            cb = ctk.CTkComboBox(self.voices_frame, values=VOICE_KEYS, width=230)
            cb.set(DEFAULT_VOICES[i % len(DEFAULT_VOICES)])
            cb.grid(row=i * 2 + 1, column=0, padx=10, pady=(0, 4), sticky="ew")
            self.voice_dropdowns[sp] = cb

        self._log(f"Персонажей: {', '.join(speakers)}")

    def _current_text(self) -> str:
        tab = self.tabs.get()
        if tab == "📖 Из библиотеки":
            return self.lib_text.get("1.0", "end").strip()
        return self.custom_text.get("1.0", "end").strip()

    # ══ ПРАВАЯ ПАНЕЛЬ: голоса и управление ════════════════════════════════════
    def _build_control_panel(self):
        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=2, padx=(5, 12), pady=12, sticky="nsew")
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(frm, text="🎙 Голоса и управление",
                     font=ctk.CTkFont(size=15, weight="bold")
                     ).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")

        self.status_lbl = ctk.CTkLabel(frm, text="⏳ Инициализация…",
                                        font=ctk.CTkFont(size=12), text_color="orange")
        self.status_lbl.grid(row=1, column=0, padx=14, pady=(0, 2), sticky="w")

        ctk.CTkLabel(frm, text="⚡ Требуется интернет",
                     font=ctk.CTkFont(size=10), text_color="#555"
                     ).grid(row=2, column=0, padx=14, pady=(0, 6), sticky="w")

        self.voices_frame = ctk.CTkScrollableFrame(frm, height=180)
        self.voices_frame.grid(row=3, column=0, padx=14, pady=0, sticky="nsew")
        self.voices_frame.grid_columnconfigure(0, weight=1)

        # Скорость
        sp_frm = ctk.CTkFrame(frm, fg_color="transparent")
        sp_frm.grid(row=4, column=0, padx=14, pady=(10, 4), sticky="ew")
        sp_frm.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(sp_frm, text="Скорость:", font=ctk.CTkFont(size=12)).grid(row=0, column=0)
        self.speed_var = tk.DoubleVar(value=0)
        ctk.CTkSlider(sp_frm, from_=-50, to=50, variable=self.speed_var,
                      number_of_steps=20, command=self._upd_speed
                      ).grid(row=0, column=1, padx=(8, 6), sticky="ew")
        self.speed_lbl = ctk.CTkLabel(sp_frm, text="+0%", width=40, font=ctk.CTkFont(size=12))
        self.speed_lbl.grid(row=0, column=2)

        # Кнопка «Сгенерировать текущий»
        self.gen_btn = ctk.CTkButton(frm, text="🎙  Сгенерировать",
                                      command=self._start_gen,
                                      height=44, state="disabled",
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.gen_btn.grid(row=5, column=0, padx=14, pady=(8, 4), sticky="ew")

        self.progress = ctk.CTkProgressBar(frm)
        self.progress.grid(row=6, column=0, padx=14, pady=(0, 8), sticky="ew")
        self.progress.set(0)

        # Прогресс батча
        self.batch_progress_lbl = ctk.CTkLabel(frm, text="", font=ctk.CTkFont(size=10),
                                                text_color="#aaa")
        self.batch_progress_lbl.grid(row=7, column=0, padx=14, pady=(0, 4), sticky="w")

        # Плеер
        pl = ctk.CTkFrame(frm, fg_color="transparent")
        pl.grid(row=8, column=0, padx=14, pady=(0, 6), sticky="ew")
        pl.grid_columnconfigure((0, 1), weight=1)

        self.play_btn = ctk.CTkButton(pl, text="▶  Воспроизвести",
                                       command=self._toggle_play,
                                       state="disabled", height=38)
        self.play_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.save_btn = ctk.CTkButton(pl, text="💾  Сохранить",
                                       command=self._save,
                                       state="disabled", height=38,
                                       fg_color="#2d7a2d", hover_color="#1f5c1f")
        self.save_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Кнопка открыть папку output
        self.open_out_btn = ctk.CTkButton(frm, text="📂  Открыть папку output",
                                           command=self._open_output_folder,
                                           height=32, fg_color="#3a3a3a",
                                           hover_color="#555")
        self.open_out_btn.grid(row=9, column=0, padx=14, pady=(4, 0), sticky="ew")

        # Лог
        ctk.CTkLabel(frm, text="Лог", font=ctk.CTkFont(size=11, weight="bold")
                     ).grid(row=10, column=0, padx=14, pady=(8, 2), sticky="w")
        self.log_box = ctk.CTkTextbox(frm, height=140,
                                       font=ctk.CTkFont(family="Consolas", size=10))
        self.log_box.grid(row=11, column=0, padx=14, pady=(0, 14), sticky="ew")
        self.log_box.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg: str):
        def _do():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _do)

    def _upd_speed(self, _=None):
        v = int(self.speed_var.get())
        self.speed_lbl.configure(text=f"{'+' if v>=0 else ''}{v}%")

    def _rate_str(self) -> str:
        v = int(self.speed_var.get())
        return f"+{v}%" if v >= 0 else f"{v}%"

    def _set_gen_btns(self, enabled: bool):
        s = "normal" if enabled else "disabled"
        self.gen_btn.configure(state=s)
        self.batch_btn.configure(state=s)
        self.gen_one_lib_btn.configure(state=s)

    # ══ ОДИНОЧНАЯ ГЕНЕРАЦИЯ ═══════════════════════════════════════════════════
    def _start_gen(self):
        if self._busy:
            return
        text = self._current_text()
        if not text:
            messagebox.showwarning("Внимание", "Текст пустой")
            return
        if not self.voice_dropdowns:
            messagebox.showwarning("Внимание", "Нажмите «Определить персонажей» или загрузите диалог")
            return
        self._busy = True
        self._set_gen_btns(False)
        self.gen_btn.configure(text="⏳ Генерация…")
        self.play_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.progress.set(0)

        voice_map = {sp: VOICES[cb.get()] for sp, cb in self.voice_dropdowns.items()}
        rate = self._rate_str()

        tmp_out = os.path.join(tempfile.mkdtemp(), "output.mp3")

        def worker():
            ok = synth_dialogue(
                text, voice_map, tmp_out, rate,
                log_cb=self._log,
                progress_cb=lambda v: self.after(0, lambda vv=v: self.progress.set(vv))
            )
            if ok:
                self.output_file = tmp_out
                sz = os.path.getsize(tmp_out) // 1024
                self._log(f"✅ Готово! {sz} KB")
                self.after(0, self._on_single_done)
            else:
                self.after(0, self._reset_after_gen)

        threading.Thread(target=worker, daemon=True).start()

    def _on_single_done(self):
        self._reset_after_gen()
        self.play_btn.configure(state="normal")
        self.save_btn.configure(state="normal")

    def _reset_after_gen(self):
        self._busy = False
        self._set_gen_btns(True)
        self.gen_btn.configure(text="🎙  Сгенерировать")

    # ══ БАТЧ-ГЕНЕРАЦИЯ ВСЕЙ БИБЛИОТЕКИ ═══════════════════════════════════════
    def _start_batch(self):
        if self._busy:
            return

        out_root = r"D:\said\output"
        if not messagebox.askyesno(
            "Сгенерировать всё",
            f"Будут сгенерированы ВСЕ диалоги из библиотеки.\n\n"
            f"Файлы сохранятся в:\n{out_root}\n\n"
            f"Уже существующие файлы будут пропущены.\n\n"
            f"Продолжить?"
        ):
            return

        self._busy = True
        self._set_gen_btns(False)
        self.batch_btn.configure(text="⏳ Генерация всей библиотеки…")
        self.progress.set(0)
        rate = self._rate_str()

        threading.Thread(target=self._batch_worker, args=(out_root, rate), daemon=True).start()

    def _batch_worker(self, out_root: str, rate: str):
        # Собрать все диалоги из библиотеки
        all_items = []
        for mod in LIBRARY.get("modules", []):
            for les in mod.get("lessons", []):
                for dial in les.get("dialogues", []):
                    all_items.append({
                        "mod_id":    mod.get("id", "M"),
                        "mod_title": mod["title"],
                        "les_id":    les.get("id", "L"),
                        "les_title": les["title"],
                        "title":     dial["title"],
                        "speakers":  dial.get("speakers", []),
                        "text":      dial["text"],
                    })

        total = len(all_items)
        done = 0
        skipped = 0
        errors = 0

        self._log(f"📦 Всего диалогов: {total}")

        for i, d in enumerate(all_items):
            # Имена файлов и папок
            mod_dir  = safe_name(f"{d['mod_id']}_{d['mod_title'][:35]}")
            les_dir  = safe_name(f"{d['les_id']}_{d['les_title'][:35]}")
            out_path = os.path.join(out_root, mod_dir, les_dir,
                                    safe_name(d["title"]) + ".mp3")

            label = f"[{i+1}/{total}] {d['title']}"

            # Пропустить уже готовые
            if os.path.exists(out_path):
                self._log(f"  ⏩ {label} — уже есть")
                skipped += 1
                self.after(0, lambda v=(i+1)/total: self.progress.set(v))
                self.after(0, lambda l=label, sk=skipped, d2=done, e=errors:
                           self.batch_progress_lbl.configure(
                               text=f"Готово: {d2}  Пропущено: {sk}  Ошибок: {e}"))
                continue

            self._log(f"🎙 {label}")

            # Назначить голоса автоматически по порядку
            speakers = d["speakers"]
            if not speakers:
                speakers = list(dict.fromkeys(re.findall(r'\[([^\]]+)\]:', d["text"])))
            voice_map = {sp: VOICES[DEFAULT_VOICES[j % len(DEFAULT_VOICES)]]
                         for j, sp in enumerate(speakers[:4])}

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            ok = synth_dialogue(
                d["text"], voice_map, out_path, rate,
                log_cb=self._log,
            )
            if ok:
                done += 1
                sz = os.path.getsize(out_path) // 1024
                self._log(f"  ✅ {sz} KB → {os.path.basename(out_path)}")
            else:
                errors += 1

            self.after(0, lambda v=(i+1)/total: self.progress.set(v))
            self.after(0, lambda d2=done, sk=skipped, e=errors:
                       self.batch_progress_lbl.configure(
                           text=f"Готово: {d2}  Пропущено: {sk}  Ошибок: {e}"))

        self._log(f"\n🎉 Завершено! Готово: {done}, Пропущено: {skipped}, Ошибок: {errors}")
        self._log(f"📂 Папка: {out_root}")
        self.after(0, self._reset_batch)

    def _reset_batch(self):
        self._busy = False
        self._set_gen_btns(True)
        self.batch_btn.configure(text="⚡  Сгенерировать ВСЁ из библиотеки")

    # ══ ПЛЕЕР ═════════════════════════════════════════════════════════════════
    def _toggle_play(self):
        if not self.output_file or not os.path.exists(self.output_file):
            return
        if not self._pg:
            messagebox.showerror("Ошибка", "pygame не инициализирован")
            return
        if self.is_playing:
            self._pg.mixer.music.stop()
            self.is_playing = False
            self.play_btn.configure(text="▶  Воспроизвести")
        else:
            self._pg.mixer.music.load(self.output_file)
            self._pg.mixer.music.play()
            self.is_playing = True
            self.play_btn.configure(text="⏹  Остановить")
            self._poll()

    def _poll(self):
        if self.is_playing:
            if not self._pg.mixer.music.get_busy():
                self.is_playing = False
                self.play_btn.configure(text="▶  Воспроизвести")
            else:
                self.after(400, self._poll)

    # ══ СОХРАНЕНИЕ ════════════════════════════════════════════════════════════
    def _save(self):
        if not self.output_file:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3")],
            initialdir=r"D:\said",
            initialfile="dialogue.mp3",
        )
        if path:
            shutil.copy(self.output_file, path)
            self._log(f"💾 Сохранено: {path}")

    def _open_output_folder(self):
        folder = r"D:\said\output"
        os.makedirs(folder, exist_ok=True)
        os.startfile(folder)


if __name__ == "__main__":
    app = App()
    app.mainloop()
