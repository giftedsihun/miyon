import ctypes
import json
import random
import shutil
import sqlite3
import subprocess
import threading
import tkinter as tk
import tempfile
import urllib.error
import urllib.request
import winsound
from datetime import date, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

from content import (CONTENT, HIRAGANA, HIRAGANA_EXTRA, HIRAGANA_ROWS, KANA,
                        GRAMMAR_CLOZE, KANA_NOTES, KATAKANA, KATAKANA_EXTRA, KATAKANA_ROWS,
                        KOREAN_ROWS, LEVELS, LISTENING_DIALOGUES, READING_PASSAGES,
                       ROMAJI_ROWS, SENTENCE_BUILDING, WORD_CLOZE, WRITING_GUIDES)

APP_TITLE = "하루 일본어"
DATA_DIR = Path.home() / ".haru_japanese"
DB_PATH = DATA_DIR / "progress.db"
SRS_DAYS = (1, 2, 4, 7, 14, 30, 60)
LEVEL_ORDER = ["초보", "문자", "N5", "N4", "N3", "N2", "N1"]
ZUNDAMON_URL = "http://127.0.0.1:9880"
ZUNDAMON_REPOSITORY = "https://github.com/zunzun999/zundamon-speech-webui.git"
ZUNDAMON_DIRECTORY = DATA_DIR / "zundamon-speech-webui"
ZUNDAMON_API_DIRECTORY = ZUNDAMON_DIRECTORY / "GPT-SoVITS"
ZUNDAMON_RUNTIME = ZUNDAMON_DIRECTORY / ".haru-runtime"
ZUNDAMON_GPT_MODEL = ZUNDAMON_API_DIRECTORY / "GPT_weights_v2" / "zudamon_style_1-e15.ckpt"
ZUNDAMON_SOVITS_MODEL = ZUNDAMON_API_DIRECTORY / "SoVITS_weights_v2" / "zudamon_style_1_e8_s96.pth"
ZUNDAMON_REFERENCE_TEXT = "流し切りが完全に入ればデバフの効果が付与される"
ZUNDAMON_SETUP_LOG = DATA_DIR / "zundamon-setup.log"
ZUNDAMON_SERVER_LOG = DATA_DIR / "zundamon-api.log"
ZUNDAMON_READY_MARKER = ZUNDAMON_RUNTIME / ".haru-zundamon-ready"
ZUNDAMON_MODEL_FILES = (
    ("https://huggingface.co/zunzunpj/zundamon_GPT-SoVITS/resolve/main/GPT_weights_v2/zudamon_style_1-e15.ckpt", ZUNDAMON_GPT_MODEL),
    ("https://huggingface.co/zunzunpj/zundamon_GPT-SoVITS/resolve/main/SoVITS_weights_v2/zudamon_style_1_e8_s96.pth", ZUNDAMON_SOVITS_MODEL),
    ("https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/chinese-hubert-base/config.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base" / "config.json"),
    ("https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/chinese-hubert-base/preprocessor_config.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base" / "preprocessor_config.json"),
    ("https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/chinese-hubert-base/pytorch_model.bin", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base" / "pytorch_model.bin"),
    ("https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/chinese-roberta-wwm-ext-large/config.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large" / "config.json"),
    ("https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/chinese-roberta-wwm-ext-large/pytorch_model.bin", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large" / "pytorch_model.bin"),
    ("https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/chinese-roberta-wwm-ext-large/tokenizer.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large" / "tokenizer.json"),
)
ZUNDAMON_PYTHON_PACKAGES = (
    "numpy==1.24.4", "scipy", "tensorboard", "librosa==0.9.2", "numba==0.57.1",
    "pytorch-lightning", "gradio>=4.0,<=4.24.0", "ffmpeg-python", "tqdm", "cn2an", "pypinyin",
    "pyopenjtalk-plus", "g2p_en", "modelscope==1.10.0", "sentencepiece",
    "transformers==4.39.3", "chardet", "PyYAML", "psutil", "jieba",
    "wordsegment", "rotary_embedding_torch", "ToJyutping",
    "g2pk2", "ko_pron", "opencc", "fastapi<0.112.2", "uvicorn", "soundfile", "onnxruntime",
    "typeguard", "regex", "gruut", "pandas", "matplotlib", "einops", "inflect", "soxr",
)


def enable_high_dpi():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass


class Database:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(DB_PATH)
        self.connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS activity (day TEXT PRIMARY KEY, completed INTEGER NOT NULL DEFAULT 0, answers INTEGER NOT NULL DEFAULT 0)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS review (
            content_id TEXT PRIMARY KEY, correct INTEGER NOT NULL DEFAULT 0,
            wrong INTEGER NOT NULL DEFAULT 0, last_seen TEXT, due_date TEXT,
            interval_step INTEGER NOT NULL DEFAULT 0)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, taken_on TEXT NOT NULL, mode TEXT NOT NULL,
            level TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL)""")
        self.connection.execute("CREATE TABLE IF NOT EXISTS favorites (content_id TEXT PRIMARY KEY)")
        # Migrate databases created by earlier builds.
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(review)")}
        for column, definition in (("due_date", "TEXT"), ("interval_step", "INTEGER NOT NULL DEFAULT 0")):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE review ADD COLUMN {column} {definition}")
        activity_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(activity)")}
        if "answers" not in activity_columns:
            self.connection.execute("ALTER TABLE activity ADD COLUMN answers INTEGER NOT NULL DEFAULT 0")
        self.connection.commit()

    def get(self, key, default=None):
        row = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        self.connection.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))
        self.connection.commit()

    def complete_today(self):
        self.connection.execute("INSERT INTO activity(day,completed) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET completed=1", (date.today().isoformat(),))
        self.connection.commit()

    def record_answer(self, content_id, correct):
        current = self.connection.execute("SELECT interval_step FROM review WHERE content_id=?", (content_id,)).fetchone()
        step = min(current[0] + 1, len(SRS_DAYS) - 1) if correct and current else (1 if correct else 0)
        due = date.today() + timedelta(days=SRS_DAYS[step] if correct else 0)
        field = "correct" if correct else "wrong"
        self.connection.execute(
            f"INSERT INTO review(content_id,{field},last_seen,due_date,interval_step) VALUES(?,1,?,?,?) "
            f"ON CONFLICT(content_id) DO UPDATE SET {field}={field}+1,last_seen=excluded.last_seen,due_date=excluded.due_date,interval_step=excluded.interval_step",
            (content_id, date.today().isoformat(), due.isoformat(), step),
        )
        self.connection.execute("INSERT INTO activity(day,completed,answers) VALUES(?,0,1) ON CONFLICT(day) DO UPDATE SET answers=answers+1", (date.today().isoformat(),))
        self.complete_today()

    def due_items(self, limit=20):
        return self.connection.execute("SELECT content_id,correct,wrong,due_date FROM review WHERE due_date <= ? ORDER BY due_date, wrong-correct DESC LIMIT ?", (date.today().isoformat(), limit)).fetchall()

    def stats(self):
        correct, wrong = self.connection.execute("SELECT COALESCE(SUM(correct),0),COALESCE(SUM(wrong),0) FROM review").fetchone()
        days = self.connection.execute("SELECT COUNT(*) FROM activity WHERE completed=1").fetchone()[0]
        due = self.connection.execute("SELECT COUNT(*) FROM review WHERE due_date <= ?", (date.today().isoformat(),)).fetchone()[0]
        return days, correct, wrong, due

    def streak(self):
        days = {row[0] for row in self.connection.execute("SELECT day FROM activity WHERE completed=1")}
        value, cursor = 0, date.today()
        while cursor.isoformat() in days:
            value += 1; cursor -= timedelta(days=1)
        return value

    def record_quiz_result(self, mode, level, score, total):
        self.connection.execute("INSERT INTO quiz_results(taken_on,mode,level,score,total) VALUES(?,?,?,?,?)", (date.today().isoformat(), mode, level, score, total))
        self.connection.commit()

    def category_results(self):
        return self.connection.execute("SELECT mode, SUM(score), SUM(total) FROM quiz_results GROUP BY mode").fetchall()

    def recent_results(self, mode, limit=5):
        return self.connection.execute("SELECT score,total FROM quiz_results WHERE mode=? ORDER BY id DESC LIMIT ?", (mode, limit)).fetchall()

    def level_results(self):
        return self.connection.execute("SELECT level, SUM(score), SUM(total) FROM quiz_results WHERE level IN ('N5','N4','N3','N2','N1') GROUP BY level ORDER BY CASE level WHEN 'N5' THEN 1 WHEN 'N4' THEN 2 WHEN 'N3' THEN 3 WHEN 'N2' THEN 4 WHEN 'N1' THEN 5 END").fetchall()

    def today_answers(self):
        row = self.connection.execute("SELECT answers FROM activity WHERE day=?", (date.today().isoformat(),)).fetchone()
        return row[0] if row else 0

    def toggle_favorite(self, content_id):
        if self.connection.execute("SELECT 1 FROM favorites WHERE content_id=?", (content_id,)).fetchone():
            self.connection.execute("DELETE FROM favorites WHERE content_id=?", (content_id,))
            saved = False
        else:
            self.connection.execute("INSERT INTO favorites(content_id) VALUES(?)", (content_id,))
            saved = True
        self.connection.commit()
        return saved

    def is_favorite(self, content_id):
        return bool(self.connection.execute("SELECT 1 FROM favorites WHERE content_id=?", (content_id,)).fetchone())

    def favorite_ids(self):
        return {row[0].replace(":words:", ":word:") for row in self.connection.execute("SELECT content_id FROM favorites")}

    def weak_items(self, limit=30):
        return self.connection.execute("SELECT content_id,correct,wrong,due_date FROM review WHERE wrong > correct ORDER BY wrong-correct DESC, last_seen DESC LIMIT ?", (limit,)).fetchall()

    def weakness_categories(self):
        rows = self.connection.execute("SELECT content_id,correct,wrong FROM review WHERE correct + wrong > 0").fetchall()
        labels = {"kana": "문자", "word": "단어", "word-cloze": "단어 예문", "kanji": "한자", "grammar": "문법", "cloze": "문법 빈칸", "reading": "독해", "listening": "청해", "sentence": "문장 만들기", "dictation": "받아쓰기"}
        totals = {}
        for content_id, correct, wrong in rows:
            kind = content_id.split(":")[0] if content_id.startswith("kana:") else content_id.split(":")[1] if ":" in content_id else "other"
            label = labels.get(kind, kind)
            old_correct, old_wrong = totals.get(label, (0, 0)); totals[label] = (old_correct + correct, old_wrong + wrong)
        return sorted(((label, correct, wrong) for label, (correct, wrong) in totals.items()), key=lambda item: (item[1] / (item[1] + item[2]), -(item[1] + item[2])))


class JapaneseStudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.tk.call("tk", "scaling", self.winfo_fpixels("1i") / 72.0)
        self.title(APP_TITLE); self.geometry("1120x760"); self.minsize(720, 500); self.configure(bg="#f4f6f0")
        self.db = Database(); self.selected_level = self.db.get("level", "초보")
        self.zundamon_start_lock = threading.Lock()
        self.zundamon_install_lock = threading.Lock()
        self.zundamon_process = None
        self.configure_styles(); self.show_home()
        self.after(500, self.auto_start_zundamon)

    def configure_styles(self):
        style = ttk.Style(self); style.theme_use("clam")
        style.configure("TButton", font=("맑은 고딕", 10), padding=(13, 8), background="#ffffff")
        style.configure("Accent.TButton", font=("맑은 고딕", 10, "bold"), foreground="#ffffff", background="#165b52")
        style.map("Accent.TButton", background=[("active", "#10463f")])
        style.configure("TProgressbar", troughcolor="#e3e8df", background="#e17a55", thickness=11)

    def clear(self):
        for widget in self.winfo_children(): widget.destroy()

    def header(self, active="홈"):
        bar = tk.Frame(self, bg="#165b52", height=68); bar.pack(fill="x")
        tk.Label(bar, text="하루 일본어", font=("맑은 고딕", 20, "bold"), fg="white", bg="#165b52").pack(side="left", padx=32, pady=16)
        for label, command in (("홈", self.show_home), ("학습", self.show_learning), ("복습", self.show_review), ("통계", self.show_stats)):
            tk.Button(bar, text=label, command=command, relief="flat", cursor="hand2", font=("맑은 고딕", 10, "bold" if active == label else "normal"), fg="#ffe0ae" if active == label else "#d8e9e2", bg="#165b52", activebackground="#165b52", activeforeground="white").pack(side="left", padx=10)

    def page(self, active, title, subtitle):
        self.clear_quiz_shortcuts()
        self.clear(); self.header(active)
        outer = tk.Frame(self, bg="#f4f6f0"); outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg="#f4f6f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        main = tk.Frame(canvas, bg="#f4f6f0")
        window = canvas.create_window((0, 0), window=main, anchor="nw")
        def resize_content(event): canvas.configure(scrollregion=canvas.bbox("all"))
        def resize_canvas(event): canvas.itemconfigure(window, width=event.width)
        main.bind("<Configure>", resize_content); canvas.bind("<Configure>", resize_canvas)
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))
        content = tk.Frame(main, bg="#f4f6f0"); content.pack(fill="both", expand=True, padx=58, pady=32)
        tk.Label(content, text=title, font=("맑은 고딕", 27, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w")
        tk.Label(content, text=subtitle, font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(6, 22))
        return content

    def card(self, parent):
        return tk.Frame(parent, bg="white", highlightbackground="#dde5dc", highlightthickness=1)

    def current_content(self):
        return CONTENT.get(self.selected_level, CONTENT["N5"])

    def study_recommendation(self):
        results = {mode: (score, total) for mode, score, total in self.db.category_results() if total}
        priority = (("reading", "독해"), ("listening", "청해 연습"), ("grammar", "문법"), ("words", "단어"), ("kanji", "한자"), ("kana", "문자"))
        scored = []
        for mode, label in priority:
            score, total = results.get(mode, (0, 0))
            if total:
                scored.append((score / total, label))
        if not scored:
            return "첫 학습은 단어 카드부터 시작해 보세요. 10분이면 충분합니다."
        rate, label = min(scored)
        return f"최근 기록상 {label} 정확도 {round(rate * 100)}%예요. 오늘은 {label}을 먼저 복습해 보세요."

    def show_home(self):
        main = self.page("홈", "오늘도 한 걸음, 일본어와 가까워져요.", "오프라인 학습 기록은 이 PC에만 안전하게 저장됩니다.")
        days, correct, wrong, due = self.db.stats(); total = correct + wrong; rate = round(correct * 100 / total) if total else 0
        hero = self.card(main); hero.pack(fill="x")
        left = tk.Frame(hero, bg="white"); left.pack(side="left", fill="both", expand=True, padx=28, pady=24)
        tk.Label(left, text="현재 과정", font=("맑은 고딕", 10), fg="#718078", bg="white").pack(anchor="w")
        tk.Label(left, text=self.selected_level, font=("맑은 고딕", 30, "bold"), fg="#165b52", bg="white").pack(anchor="w")
        tk.Label(left, text=f"연속 학습 {self.db.streak()}일 · 정답률 {rate}% · 오늘 복습 {due}개", font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", pady=(3, 0))
        tk.Label(left, text=self.study_recommendation(), font=("맑은 고딕", 10), fg="#a2543e", bg="white", wraplength=620, justify="left").pack(anchor="w", pady=(9, 0))
        ttk.Button(hero, text="오늘의 코스 시작", style="Accent.TButton", command=self.show_learning).pack(side="right", padx=28, pady=37)
        goal = self.db.get("daily_goal", 20); today = self.db.today_answers()
        goal_card = self.card(main); goal_card.pack(fill="x", pady=(16, 0))
        goal_top = tk.Frame(goal_card, bg="white"); goal_top.pack(fill="x", padx=18, pady=(14, 5))
        tk.Label(goal_top, text="오늘의 목표", font=("맑은 고딕", 12, "bold"), fg="#173c35", bg="white").pack(side="left")
        tk.Label(goal_top, text=f"{today} / {goal}문항", font=("맑은 고딕", 11, "bold"), fg="#df7654", bg="white").pack(side="right")
        ttk.Progressbar(goal_card, maximum=goal, value=min(today, goal)).pack(fill="x", padx=18, pady=(0, 7))
        actions = tk.Frame(goal_card, bg="white"); actions.pack(anchor="e", padx=18, pady=(0, 12))
        self.voice_status = tk.Label(actions, text="ずんだもん AI 서버를 확인하고 있어요...", font=("맑은 고딕", 9), fg="#66776f", bg="white")
        self.voice_status.pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="AI 음성 설정", command=self.show_voice_settings).pack(side="left", padx=4)
        ttk.Button(actions, text="AI 음성 확인/시작", command=lambda: self.show_voice_settings(start=True)).pack(side="left", padx=4)
        ttk.Button(actions, text="목표 바꾸기", command=self.change_daily_goal).pack(side="left", padx=4)
        tk.Label(main, text="빠른 시작", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(30, 12))
        quick = tk.Frame(main, bg="#f4f6f0"); quick.pack(fill="x")
        for i, (title, detail, command) in enumerate((("오늘의 복습", f"지금 풀 문제 {due}개", lambda: self.start_quiz(mode="review")), ("오답 노트", "자주 틀린 항목 다시 보기", self.show_wrong_notebook), ("즐겨찾기 퀴즈", "저장한 카드만 확인", lambda: self.start_quiz(mode="favorites")), ("학습 계획", "목표와 하루 분량 설정", self.show_study_plan), ("모의고사", "어휘 · 문법 · 독해 · 청해", lambda: self.start_quiz(mode="mock")), ("과정 선택", "내 목표 직접 설정", self.show_level_select))):
            item = self.card(quick); item.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0, 9), pady=2); quick.columnconfigure(i % 3, weight=1)
            tk.Label(item, text=title, font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=16, pady=(17, 4))
            tk.Label(item, text=detail, font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=16)
            ttk.Button(item, text="열기", command=command).pack(anchor="w", padx=16, pady=15)

    def change_daily_goal(self):
        dialog = tk.Toplevel(self); dialog.title("오늘의 목표"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        tk.Label(dialog, text="하루에 풀 문항 수", font=("맑은 고딕", 14, "bold"), fg="#173c35", bg="white").pack(padx=32, pady=(24, 10))
        value = tk.IntVar(value=self.db.get("daily_goal", 20))
        ttk.Spinbox(dialog, from_=5, to=100, increment=5, textvariable=value, width=8, justify="center", font=("맑은 고딕", 12)).pack(pady=4)
        def save():
            self.db.set("daily_goal", max(5, min(100, value.get()))); dialog.destroy(); self.show_home()
        ttk.Button(dialog, text="저장", style="Accent.TButton", command=save).pack(pady=(14, 24))

    def show_study_plan(self):
        plan = self.db.get("study_plan", {"level": self.selected_level if self.selected_level in CONTENT else "N5", "days": 30, "daily_words": 10})
        level = plan.get("level", "N5"); days = max(1, int(plan.get("days", 30))); daily_words = max(1, int(plan.get("daily_words", 10)))
        word_count = len(CONTENT.get(level, CONTENT["N5"])["words"])
        target_days = max(days, (word_count + daily_words - 1) // daily_words)
        main = self.page("학습", "학습 계획", "목표 과정과 기간을 기준으로 오늘의 새 단어와 복습량을 안내합니다.")
        card = self.card(main); card.pack(fill="x")
        tk.Label(card, text=f"목표: {level} · 계획 기간: {days}일", font=("맑은 고딕", 18, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=22, pady=(20, 5))
        tk.Label(card, text=f"하루 새 단어 {daily_words}개 · 전체 {word_count}개 · 권장 최소 {target_days}일", font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", padx=22)
        tk.Label(card, text=f"오늘 Day {self.db.get('course_day', 1):03d}: 새 단어 {daily_words}개 + 문법 1개 + 복습 {self.db.stats()[3]}개", font=("맑은 고딕", 13, "bold"), fg="#a2543e", bg="white").pack(anchor="w", padx=22, pady=(12, 20))
        ttk.Button(main, text="계획 설정", style="Accent.TButton", command=self.edit_study_plan).pack(anchor="e", pady=18)

    def edit_study_plan(self):
        dialog = tk.Toplevel(self); dialog.title("학습 계획 설정"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        current = self.db.get("study_plan", {"level": "N5", "days": 30, "daily_words": 10})
        tk.Label(dialog, text="목표 과정", font=("맑은 고딕", 11, "bold"), bg="white").pack(padx=28, pady=(22, 3), anchor="w")
        level = tk.StringVar(value=current.get("level", "N5")); ttk.Combobox(dialog, textvariable=level, values=("N5", "N4", "N3", "N2", "N1"), state="readonly", width=12).pack(padx=28)
        tk.Label(dialog, text="목표 기간(일)", font=("맑은 고딕", 11, "bold"), bg="white").pack(padx=28, pady=(14, 3), anchor="w")
        days = tk.IntVar(value=current.get("days", 30)); ttk.Spinbox(dialog, from_=7, to=365, textvariable=days, width=10).pack(padx=28, anchor="w")
        tk.Label(dialog, text="하루 새 단어 수", font=("맑은 고딕", 11, "bold"), bg="white").pack(padx=28, pady=(14, 3), anchor="w")
        daily_words = tk.IntVar(value=current.get("daily_words", 10)); ttk.Spinbox(dialog, from_=3, to=50, textvariable=daily_words, width=10).pack(padx=28, anchor="w")
        def save():
            self.db.set("study_plan", {"level": level.get(), "days": max(7, days.get()), "daily_words": max(3, daily_words.get())}); dialog.destroy(); self.show_study_plan()
        ttk.Button(dialog, text="저장", style="Accent.TButton", command=save).pack(padx=28, pady=24, anchor="e")

    def zundamon_api_available(self, url, timeout=5):
        try:
            with urllib.request.urlopen(url.rstrip("/") + "/docs", timeout=timeout) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            return False

    def zundamon_runtime_python(self):
        return ZUNDAMON_RUNTIME / "Scripts" / "python.exe"

    def zundamon_ready(self):
        required = (
            ZUNDAMON_API_DIRECTORY / "api.py",
            ZUNDAMON_DIRECTORY / "reference" / "reference.wav",
            self.zundamon_runtime_python(),
            ZUNDAMON_READY_MARKER,
            ZUNDAMON_GPT_MODEL,
            ZUNDAMON_SOVITS_MODEL,
        ) + tuple(destination for _, destination in ZUNDAMON_MODEL_FILES[2:])
        return all(path.is_file() for path in required)

    def zundamon_status(self):
        if self.zundamon_api_available(str(self.db.get("zundamon_url", ZUNDAMON_URL)), timeout=2):
            return "연결됨: ずんだもん AI 서버가 실행 중이에요.", "#165b52"
        if self.zundamon_ready():
            return "준비 완료: ずんだもん AI 서버를 시작할 수 있어요.", "#66776f"
        return "준비 필요: AI 음성 파일과 실행 환경을 자동으로 설치합니다.", "#66776f"

    def zundamon_command(self):
        python = self.zundamon_runtime_python()
        return [
            str(python), "api.py", "-d", "cpu", "-fp", "-p", "9880",
            "-g", str(ZUNDAMON_GPT_MODEL), "-s", str(ZUNDAMON_SOVITS_MODEL),
            "-dr", "..\\reference\\reference.wav", "-dt", ZUNDAMON_REFERENCE_TEXT,
            "-dl", "ja",
        ]

    def run_zundamon_command(self, arguments, log_file, timeout, set_status):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as output:
            output.write("\n$ " + subprocess.list2cmdline([str(value) for value in arguments]) + "\n")
            output.flush()
            result = subprocess.run(
                [str(value) for value in arguments], stdout=output, stderr=subprocess.STDOUT,
                timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        if result.returncode:
            set_status("AI 음성 준비에 실패했어요. 자세한 오류는 " + str(log_file) + "에서 확인해 주세요.", "#b95140")
            return False
        return True

    def download_zundamon_file(self, source, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        request = urllib.request.Request(source, headers={"User-Agent": "HaruJapanese/1.0"})
        with urllib.request.urlopen(request, timeout=180) as response, open(temporary, "wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)

    def auto_start_zundamon(self):
        if self.db.get("zundamon_auto_start", True):
            self.start_zundamon_api(getattr(self, "voice_status", None))
        elif hasattr(self, "voice_status"):
            message, color = self.zundamon_status()
            self.voice_status.config(text=message, fg=color)

    def start_zundamon_api(self, status=None):
        url = str(self.db.get("zundamon_url", ZUNDAMON_URL)).strip().rstrip("/")

        def set_status(message, color):
            if status:
                self.after(0, lambda: status.winfo_exists() and status.config(text=message, fg=color))

        def run():
            if not self.zundamon_start_lock.acquire(blocking=False):
                set_status("ずんだもん AI 서버를 이미 시작하고 있어요...", "#66776f")
                return
            try:
                if self.zundamon_api_available(url):
                    set_status("연결됨: ずんだもん AI 서버가 이미 실행 중이에요.", "#165b52")
                    return
                if not self.zundamon_ready():
                    if not self.install_zundamon_api(set_status):
                        return
                set_status("ずんだもん AI 서버를 시작하고 있어요. 모델을 읽는 동안 잠시 기다려 주세요...", "#66776f")
                flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                with open(ZUNDAMON_SERVER_LOG, "a", encoding="utf-8") as server_log:
                    self.zundamon_process = subprocess.Popen(self.zundamon_command(), cwd=ZUNDAMON_API_DIRECTORY,
                                                              stdout=server_log, stderr=subprocess.STDOUT,
                                                              creationflags=flags)
                for _ in range(180):
                    if self.zundamon_api_available(url, timeout=2):
                        set_status("시작 완료: ずんだもん AI 음성을 사용할 수 있어요.", "#165b52")
                        return
                    if self.zundamon_process.poll() is not None:
                        set_status("AI 서버가 바로 종료됐어요. 오류는 " + str(ZUNDAMON_SERVER_LOG) + "에서 확인할 수 있어요.", "#b95140")
                        return
                    threading.Event().wait(1)
                set_status("서버 시작 시간이 초과됐어요. 로그를 확인해 주세요: " + str(ZUNDAMON_SERVER_LOG), "#b95140")
            except OSError as error:
                set_status(f"AI 서버를 시작할 수 없어요. ({error})", "#b95140")
            finally:
                self.zundamon_start_lock.release()

        threading.Thread(target=run, daemon=True).start()

    def install_zundamon_api(self, set_status):
        """Prepare the compatible runtime, models, and local Zundamon API on first use."""
        if not self.zundamon_install_lock.acquire(blocking=False):
            set_status("ずんだもん AI 파일을 이미 내려받고 있어요...", "#66776f")
            return False
        try:
            if self.zundamon_ready():
                return True
            if not (ZUNDAMON_API_DIRECTORY / "api.py").is_file():
                if ZUNDAMON_DIRECTORY.exists():
                    set_status("AI 프로젝트 복구를 위해 다시 내려받고 있어요...", "#66776f")
                    shutil.rmtree(ZUNDAMON_DIRECTORY)
                set_status("ずんだもん AI 프로젝트를 처음 내려받고 있어요...", "#66776f")
                if not self.run_zundamon_command(
                    ["git", "clone", "--recursive", "--depth", "1", ZUNDAMON_REPOSITORY, str(ZUNDAMON_DIRECTORY)],
                    ZUNDAMON_SETUP_LOG, 900, set_status,
                ) or not (ZUNDAMON_API_DIRECTORY / "api.py").is_file():
                    return False
            runtime_python = self.zundamon_runtime_python()
            if not runtime_python.is_file():
                set_status("AI 음성용 Python 3.10 환경을 준비하고 있어요. 처음 한 번만 필요합니다...", "#66776f")
                if not self.run_zundamon_command(
                    ["uv", "venv", "--python", "3.10", str(ZUNDAMON_RUNTIME)], ZUNDAMON_SETUP_LOG, 900, set_status,
                ):
                    return False
            if not ZUNDAMON_READY_MARKER.is_file():
                set_status("AI 음성 실행 패키지를 설치하고 있어요. 몇 분 걸릴 수 있어요...", "#66776f")
                if not self.run_zundamon_command(
                    ["uv", "pip", "install", "--python", str(runtime_python), "torch==2.1.2+cpu", "torchaudio==2.1.2+cpu", "--index-url", "https://download.pytorch.org/whl/cpu"],
                    ZUNDAMON_SETUP_LOG, 1800, set_status,
                ) or not self.run_zundamon_command(
                    ["uv", "pip", "install", "--python", str(runtime_python), "setuptools<81", "torch==2.1.2+cpu", "torchaudio==2.1.2+cpu", *ZUNDAMON_PYTHON_PACKAGES], ZUNDAMON_SETUP_LOG, 1800, set_status,
                ):
                    return False
            # Recreate compatibility files on later launches too, in case a package update restored them.
            # The upstream source imports extensions that are impractical to compile on a bare Windows PC.
            # For this Japanese-only app, these pure-Python compatibility modules provide the used API.
            compatibility_file = ZUNDAMON_RUNTIME / "Lib" / "site-packages" / "jieba_fast.py"
            compatibility_file.write_text(
                "import sys\nimport jieba as _jieba\nfrom jieba import *\nsys.modules[__name__] = _jieba\n",
                encoding="ascii",
            )
            shutil.rmtree(ZUNDAMON_RUNTIME / "Lib" / "site-packages" / "LangSegment", ignore_errors=True)
            langsegment_file = ZUNDAMON_RUNTIME / "Lib" / "site-packages" / "LangSegment.py"
            langsegment_file.write_text(
                "filters = None\n"
                "def setfilters(value):\n"
                "    global filters\n"
                "    filters = value\n"
                "def getTexts(text):\n"
                "    language = filters[0] if filters and len(filters) == 1 else 'ja'\n"
                "    return [{'text': text, 'lang': language}]\n"
                "class LangSegment:\n"
                "    setfilters = staticmethod(setfilters)\n"
                "    getTexts = staticmethod(getTexts)\n",
                encoding="ascii",
            )
            for index, (source, destination) in enumerate(ZUNDAMON_MODEL_FILES, start=1):
                if destination.is_file() and destination.stat().st_size > 1024:
                    continue
                set_status(f"AI 음성 모델을 내려받고 있어요 ({index}/{len(ZUNDAMON_MODEL_FILES)})...", "#66776f")
                try:
                    self.download_zundamon_file(source, destination)
                except (OSError, urllib.error.URLError) as error:
                    set_status(f"AI 모델 다운로드에 실패했어요. 인터넷 연결을 확인해 주세요. ({error})", "#b95140")
                    return False
            self.db.set("zundamon_api_directory", str(ZUNDAMON_API_DIRECTORY))
            self.db.set("zundamon_auto_start", True)
            ZUNDAMON_READY_MARKER.write_text("ready\n", encoding="ascii")
            set_status("ずんだもん AI 음성 준비가 끝났어요. 서버를 시작합니다...", "#165b52")
            return True
        except (OSError, subprocess.TimeoutExpired) as error:
            set_status(f"AI 파일을 내려받을 수 없어요. Git과 인터넷 연결을 확인해 주세요. ({error})", "#b95140")
            return False
        finally:
            self.zundamon_install_lock.release()

    def show_voice_settings(self, start=False):
        dialog = tk.Toplevel(self); dialog.title("로컬 AI 음성 설정"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        tk.Label(dialog, text="ずんだもん 로컬 AI 음성", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=28, pady=(24, 4))
        tk.Label(dialog, text="서버 시작을 누르면 Python 3.10 환경, 필요한 패키지와 모델을 자동으로 준비합니다.\n처음에는 대용량 파일을 내려받아 시간이 걸리며, 진행 오류는 설정 로그에 저장됩니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white", justify="left").pack(anchor="w", padx=28, pady=(0, 15))
        fields = (
            ("API 서버 주소", "zundamon_url", ZUNDAMON_URL),
            ("기본 속도 (0.5~2.0)", "zundamon_speed", "1.0"),
        )
        values = {}
        for label, key, default in fields:
            row = tk.Frame(dialog, bg="white"); row.pack(fill="x", padx=28, pady=4)
            tk.Label(row, text=label, width=18, anchor="w", font=("맑은 고딕", 10), fg="#173c35", bg="white").pack(side="left")
            value = tk.StringVar(value=str(self.db.get(key, default))); values[key] = value
            ttk.Entry(row, textvariable=value, width=32, font=("맑은 고딕", 10)).pack(side="left", fill="x", expand=True)
        status = tk.Label(dialog, text="", font=("맑은 고딕", 9), fg="#66776f", bg="white", wraplength=430, justify="left"); status.pack(anchor="w", padx=28, pady=(10, 0))
        auto_start = tk.BooleanVar(value=self.db.get("zundamon_auto_start", True))
        ttk.Checkbutton(dialog, text="앱 시작 시 AI 서버가 꺼져 있으면 자동으로 시작", variable=auto_start).pack(anchor="w", padx=28, pady=(8, 0))
        def settings():
            try:
                return (values["zundamon_url"].get().strip().rstrip("/"), max(0.5, min(2.0, float(values["zundamon_speed"].get()))))
            except ValueError:
                raise ValueError("속도는 0.5~2.0 사이의 숫자로 입력해 주세요.")
        def save():
            try: url, speed = settings()
            except ValueError as error: status.config(text=str(error), fg="#b95140"); return
            if not url.startswith(("http://", "https://")):
                status.config(text="서버 주소는 http:// 또는 https://로 시작해야 합니다.", fg="#b95140"); return
            for key, value in (("zundamon_url", url), ("zundamon_speed", speed),
                               ("zundamon_auto_start", auto_start.get())):
                self.db.set(key, value)
            status.config(text="저장했어요. 앱은 준비된 ずんだもん AI 서버만 사용합니다.", fg="#165b52")
        def test():
            save()
            if status.cget("fg") == "#b95140": return
            status.config(text="ずんだもん API 서버 연결을 확인하고 있어요...", fg="#66776f")
            def run():
                try:
                    url, _ = settings()
                    if not self.zundamon_api_available(url):
                        raise OSError("API 서버가 응답하지 않았습니다.")
                    message = "연결됨: ずんだもん GPT-SoVITS API 서버를 찾았어요."
                    self.after(0, lambda: status.config(text=message, fg="#165b52"))
                except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
                    self.after(0, lambda: status.config(text=f"연결할 수 없어요. API 서버 실행과 주소를 확인해 주세요. ({error})", fg="#b95140"))
            threading.Thread(target=run, daemon=True).start()
        controls = tk.Frame(dialog, bg="white"); controls.pack(anchor="e", padx=28, pady=(14, 24))
        def refresh_status():
            message, color = self.zundamon_status()
            status.config(text=message, fg=color)
        ttk.Button(controls, text="상태 새로고침", command=refresh_status).pack(side="left", padx=4)
        ttk.Button(controls, text="연결 확인", command=test).pack(side="left", padx=4)
        def start_server():
            save()
            if status.cget("fg") != "#b95140": self.start_zundamon_api(status)
        ttk.Button(controls, text="서버 시작", command=start_server).pack(side="left", padx=4)
        ttk.Button(controls, text="저장", style="Accent.TButton", command=save).pack(side="left", padx=4)
        if start:
            dialog.after(100, start_server)

    def show_level_select(self):
        main = self.page("홈", "어디서 시작할까요?", "직접 과정을 고르거나 12문항 진단으로 추천받으세요.")
        grid = tk.Frame(main, bg="#f4f6f0"); grid.pack(fill="both", expand=True)
        for i, (name, subtitle, desc, group) in enumerate(LEVELS):
            item = self.card(grid); item.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6); grid.columnconfigure(i % 3, weight=1)
            tk.Label(item, text=name, font=("맑은 고딕", 20, "bold"), fg="#df7654" if group == "기초" else "#165b52", bg="white").pack(anchor="w", padx=18, pady=(15, 1))
            tk.Label(item, text=subtitle, font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=18)
            tk.Label(item, text=desc, wraplength=210, justify="left", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=18, pady=(7, 10))
            ttk.Button(item, text="이 과정 선택", command=lambda value=name: self.select_level(value)).pack(anchor="w", padx=18, pady=(0, 15))
        ttk.Button(main, text="12문항 실력 진단 시작", style="Accent.TButton", command=self.start_diagnostic).pack(anchor="e", pady=18)

    def select_level(self, level):
        self.selected_level = level; self.db.set("level", level); self.show_home()

    def show_learning(self):
        day = self.db.get("course_day", 1)
        main = self.page("학습", "오늘의 학습", f"{self.selected_level} 과정 · Day {day:03d} · 25~35분 권장")
        if self.selected_level in ("초보", "문자"):
            lessons = (("히라가나", "기본 46자, 탁음과 요음", lambda: self.show_kana("hiragana")), ("가타카나", "외래어와 이름을 읽는 문자", lambda: self.show_kana("katakana")), ("문자 종합 퀴즈", "배운 문자를 바로 확인", lambda: self.start_quiz(mode="kana")), ("문자 규칙", "촉음, 장음, 요음 핵심 정리", self.show_kana_notes))
        else:
            lessons = (("오늘의 새 단어", "학습 계획에 맞춘 오늘 분량", self.show_daily_words), ("단어", "의미와 예문으로 익히기", lambda: self.show_catalog("words")), ("한자", "읽기와 핵심 어휘", lambda: self.show_catalog("kanji")), ("문법", "설명과 예문으로 정리", lambda: self.show_catalog("grammar")), ("문장 만들기", "단어 조각을 올바른 순서로 배열", self.show_sentence_building), ("받아쓰기", "듣고 일본어를 직접 입력", self.show_dictation), ("독해", "짧은 지문으로 핵심 찾기", lambda: self.start_quiz(mode="reading")), ("청해 연습", "ずんだもん AI 음성으로 대화 듣기", lambda: self.start_quiz(mode="listening")), ("한자 쓰기", "직접 써 보며 형태 익히기", self.show_kanji_writing), ("종합 모의고사", "어휘 · 문법 · 독해 · 청해", lambda: self.start_quiz(mode="mock")))
        for title, detail, command in lessons:
            row = self.card(main); row.pack(fill="x", pady=5)
            tk.Label(row, text=title, width=12, font=("맑은 고딕", 12, "bold"), fg="#df7654", bg="white").pack(side="left", padx=16, pady=17)
            tk.Label(row, text=detail, font=("맑은 고딕", 11), fg="#173c35", bg="white").pack(side="left")
            ttk.Button(row, text="학습", command=command).pack(side="right", padx=16)
        ttk.Button(main, text="오늘 학습 완료 표시", style="Accent.TButton", command=self.complete_lesson).pack(anchor="e", pady=22)

    def complete_lesson(self):
        self.db.complete_today(); self.db.set("course_day", self.db.get("course_day", 1) + 1)
        messagebox.showinfo("오늘의 학습", "오늘의 학습을 기록했어요. 내일도 부담 없이 이어가세요."); self.show_learning()

    def show_kana_menu(self):
        main = self.page("학습", "기초 문자", "두 문자를 분리해 익힌 뒤 종합 퀴즈로 확인하세요.")
        for title, detail, command, color in (("히라가나", "기본 46자 + 탁음 · 반탁음 · 요음", lambda: self.show_kana("hiragana"), "#df7654"), ("가타카나", "기본 46자 + 탁음 · 반탁음 · 요음", lambda: self.show_kana("katakana"), "#165b52")):
            item = self.card(main); item.pack(fill="x", pady=7)
            tk.Label(item, text=title, font=("맑은 고딕", 22, "bold"), fg=color, bg="white").pack(anchor="w", padx=24, pady=(20, 3))
            tk.Label(item, text=detail, font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", padx=24)
            ttk.Button(item, text="학습 시작", style="Accent.TButton", command=command).pack(anchor="e", padx=24, pady=(0, 18))

    def show_kana(self, script):
        hira = script == "hiragana"; title = "히라가나" if hira else "가타카나"; accent = "#df7654" if hira else "#165b52"
        rows, extras = (HIRAGANA_ROWS, HIRAGANA_EXTRA) if hira else (KATAKANA_ROWS, KATAKANA_EXTRA)
        main = self.page("학습", title, "한 줄씩 소리 내어 읽고, 글자를 누르면 바로 ずんだもん 발음이 재생됩니다.")
        notebook = ttk.Notebook(main); notebook.pack(fill="both", expand=True)
        basic, extra = tk.Frame(notebook, bg="white"), tk.Frame(notebook, bg="white"); notebook.add(basic, text="  기본 46자  "); notebook.add(extra, text="  탁음 · 요음  ")
        for row_index, chars in enumerate(rows):
            readings, roman = KOREAN_ROWS[row_index].split(), ROMAJI_ROWS[row_index].split()
            tk.Label(basic, text=f"{roman[0]}행", width=6, font=("맑은 고딕", 10, "bold"), fg="#718078", bg="white").grid(row=row_index, column=0, padx=12, pady=5)
            for column, char in enumerate(chars): self.kana_cell(basic, char, readings[column], accent, row_index, column + 1)
        for col in range(6): basic.columnconfigure(col, weight=1)
        grid = tk.Frame(extra, bg="white"); grid.pack(fill="both", expand=True, padx=17, pady=18)
        for i, (char, reading) in enumerate(extras): self.kana_cell(grid, char, reading, accent, i // 7, i % 7)
        for col in range(7): grid.columnconfigure(col, weight=1)
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(anchor="e", pady=12)
        ttk.Button(controls, text="글자 쓰기 연습", command=lambda: self.show_kana_writing(script)).pack(side="left", padx=4)
        ttk.Button(controls, text=f"{title} 퀴즈", style="Accent.TButton", command=lambda: self.start_quiz(mode="kana", kana_set=(HIRAGANA + HIRAGANA_EXTRA if hira else KATAKANA + KATAKANA_EXTRA), title=title)).pack(side="left", padx=4)

    def kana_cell(self, parent, char, reading, accent, row, column):
        # A one-line button height keeps all ten kana rows visible on smaller windows.
        tk.Button(parent, text=f"{char}\n{reading}", command=lambda: self.speak_japanese(char), relief="flat", cursor="hand2", font=("맑은 고딕", 15, "bold"), fg=accent, bg="#f5f8f3", activebackground="#fff2e6", width=7, height=1).grid(row=row, column=column, sticky="nsew", padx=3, pady=3)

    def show_kana_writing(self, script):
        hira = script == "hiragana"; title = "히라가나" if hira else "가타카나"
        chars = HIRAGANA + HIRAGANA_EXTRA if hira else KATAKANA + KATAKANA_EXTRA
        self.kana_writing_index = 0
        main = self.page("학습", f"{title} 쓰기 연습", "견본을 보고 빈 칸에 따라 써 보세요. 입력한 글자는 모양 인식 없이 일치 여부만 확인합니다.")
        card = self.card(main); card.pack(fill="both", expand=True)
        target = tk.Label(card, font=("Yu Gothic", 96, "bold"), fg="#df7654" if hira else "#165b52", bg="white"); target.pack(pady=(26, 0))
        reading = tk.Label(card, font=("맑은 고딕", 18, "bold"), fg="#173c35", bg="white"); reading.pack()
        guide = tk.Label(card, text="1. 견본을 천천히 관찰합니다.  2. 아래 칸에 같은 글자를 입력하거나 손으로 써 봅니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white"); guide.pack(pady=(8, 12))
        entry = ttk.Entry(card, justify="center", font=("Yu Gothic", 35), width=8); entry.pack(pady=10)
        feedback = tk.Label(card, font=("맑은 고딕", 11), fg="#66776f", bg="white"); feedback.pack(pady=(0, 8))
        canvas, stroke_count, clear_canvas = self.make_writing_canvas(card)
        tk.Label(card, text="마우스나 터치로 직접 그려 보세요. 획 수는 연습 기록용이며 글자 모양을 채점하지 않습니다.", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(pady=(7, 0))
        def render():
            char, sound = chars[self.kana_writing_index]
            target.config(text=char); reading.config(text=f"발음: {sound}"); entry.delete(0, "end"); clear_canvas(); feedback.config(text="견본을 보고 천천히 한 번 써 보세요.", fg="#66776f"); entry.focus_set()
        def check():
            char, _ = chars[self.kana_writing_index]
            if entry.get().strip() == char:
                self.db.record_answer(f"kana:{char}", True); feedback.config(text="맞게 입력했어요. 손으로도 세 번 더 써 보세요.", fg="#165b52")
            else:
                self.db.record_answer(f"kana:{char}", False); feedback.config(text=f"견본은 「{char}」입니다. 다시 보고 써 보세요.", fg="#b95140")
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
        ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
        ttk.Button(controls, text="입력 확인", command=check).pack(side="left", padx=4)
        ttk.Button(controls, text="그림 지우기", command=clear_canvas).pack(side="left", padx=4)
        ttk.Button(controls, text="다음", style="Accent.TButton", command=lambda: move(1)).pack(side="left", padx=4)
        def move(step): self.kana_writing_index = (self.kana_writing_index + step) % len(chars); render()
        render()

    def show_kana_notes(self):
        main = self.page("학습", "문자 읽기 규칙", "문자를 조합해 자연스럽게 읽기 위한 네 가지 핵심입니다.")
        for symbol, title, text in KANA_NOTES:
            item = self.card(main); item.pack(fill="x", pady=5)
            tk.Label(item, text=symbol, font=("맑은 고딕", 20, "bold"), fg="#df7654", bg="white", width=14).pack(side="left", padx=15, pady=15)
            block = tk.Frame(item, bg="white"); block.pack(side="left", fill="x", expand=True, pady=12)
            tk.Label(block, text=title, font=("맑은 고딕", 12, "bold"), fg="#173c35", bg="white").pack(anchor="w")
            tk.Label(block, text=text, font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(anchor="w")

    def show_daily_words(self):
        plan = self.db.get("study_plan", {"daily_words": 10})
        count = max(3, int(plan.get("daily_words", 10))); data = self.current_content()["words"]
        day = max(1, self.db.get("course_day", 1)); start = ((day - 1) * count) % len(data); items = [data[(start + index) % len(data)] for index in range(min(count, len(data)))]
        self.show_catalog("words", items, f"Day {day:03d} · 오늘의 새 단어 {len(items)}개를 예문과 함께 익혀 보세요.")

    def show_catalog(self, category, items=None, subtitle=None):
        titles = {"words": "단어 카드", "kanji": "한자 카드", "grammar": "문법 학습"}; data = items or self.current_content()[category]; self.catalog_index = 0
        main = self.page("학습", titles[category], subtitle or f"{self.selected_level} 과정 · 예문까지 읽고 다음 카드로 넘어가세요.")
        search_row = tk.Frame(main, bg="#f4f6f0"); search_row.pack(fill="x", pady=(0, 10))
        query = tk.StringVar()
        search = ttk.Entry(search_row, textvariable=query, width=34, font=("맑은 고딕", 10)); search.pack(side="left")
        tk.Label(search_row, text="일본어, 읽기, 뜻으로 검색", font=("맑은 고딕", 9), fg="#718078", bg="#f4f6f0").pack(side="left", padx=9)
        favorites_only = tk.BooleanVar(value=False)
        tag = tk.StringVar(value="전체")
        ttk.Checkbutton(search_row, text="즐겨찾기만", variable=favorites_only, command=lambda: filter_cards()).pack(side="right")
        if category == "words":
            ttk.Combobox(search_row, textvariable=tag, values=("전체", "동사", "명사", "형용사·부사"), state="readonly", width=11).pack(side="right", padx=8)
        card = self.card(main); card.pack(fill="both", expand=True)
        title = tk.Label(card, font=("맑은 고딕", 33, "bold"), fg="#165b52", bg="white"); title.pack(pady=(55, 12))
        detail = tk.Label(card, font=("맑은 고딕", 16), fg="#173c35", bg="white", wraplength=760, justify="center"); detail.pack(padx=25)
        example = tk.Label(card, font=("맑은 고딕", 12), fg="#66776f", bg="white", wraplength=760, justify="center"); example.pack(pady=(15, 25))
        counter = tk.Label(card, font=("맑은 고딕", 10), fg="#718078", bg="white"); counter.pack()
        favorite = ttk.Button(card); favorite.pack(pady=(10, 0))
        visible = list(data)
        def item_id(item): return f"{self.selected_level}:{category}:{item[0]}"
        def render():
            if not visible:
                title.config(text="검색 결과 없음", font=("맑은 고딕", 24, "bold")); detail.config(text="다른 검색어를 입력해 보세요."); example.config(text=""); counter.config(text=""); favorite.pack_forget(); return
            item = visible[self.catalog_index]
            if category == "words": title.config(text=item[0]); detail.config(text=f"{item[1]} · {item[2]}"); example.config(text=item[3])
            elif category == "kanji": title.config(text=item[0]); detail.config(text=f"읽기: {item[1]} · 뜻: {item[2]}"); example.config(text=f"핵심 어휘: {item[3]}")
            else: title.config(text=item[0], font=("맑은 고딕", 23, "bold")); detail.config(text=item[1]); example.config(text=item[2])
            counter.config(text=f"{self.catalog_index + 1} / {len(visible)}")
            favorite.pack(pady=(10, 0)); favorite.config(text="즐겨찾기 해제" if self.db.is_favorite(item_id(item)) else "즐겨찾기 추가", command=lambda value=item: toggle_favorite(value))
        def toggle_favorite(item):
            self.db.toggle_favorite(item_id(item)); render()
        def filter_cards(*_):
            nonlocal visible
            text = query.get().strip().lower()
            def matches_tag(item):
                if category != "words" or tag.get() == "전체": return True
                word = item[0]
                if tag.get() == "동사": return word.endswith(("る", "う", "く", "す", "む", "ぶ", "つ"))
                if tag.get() == "형용사·부사": return word.endswith(("い", "な", "に")) or word in ("特に", "最近", "具体的")
                return not (word.endswith(("る", "う", "く", "す", "む", "ぶ", "つ", "い", "な", "に")) or word in ("特に", "最近", "具体的"))
            visible = [item for item in data if (not text or text in " ".join(item).lower()) and matches_tag(item) and (not favorites_only.get() or self.db.is_favorite(item_id(item)))]
            self.catalog_index = 0; render()
        query.trace_add("write", filter_cards)
        tag.trace_add("write", filter_cards)
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
        ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
        ttk.Button(controls, text="이 카테고리 퀴즈", style="Accent.TButton", command=lambda: self.start_quiz(mode=category)).pack(side="left", padx=4)
        if category in ("words", "grammar"):
            ttk.Button(controls, text="예문 듣기", command=lambda: self.speak_japanese(data[self.catalog_index][3] if category == "words" else data[self.catalog_index][2])).pack(side="left", padx=4)
        if category == "kanji":
            ttk.Button(controls, text="쓰기 연습", command=self.show_kanji_writing).pack(side="left", padx=4)
        ttk.Button(controls, text="다음", command=lambda: move(1)).pack(side="left", padx=4)
        def move(step):
            if visible: self.catalog_index = (self.catalog_index + step) % len(visible); render()
        render()

    def speak_japanese(self, text, status=None, rate=0):
        self.stop_speech()
        self.speak_with_zundamon(text, status, rate)

    def speak_with_zundamon(self, text, status=None, rate=0):
        """Request WAV audio from the user-run Zundamon GPT-SoVITS API server."""
        url = str(self.db.get("zundamon_url", ZUNDAMON_URL)).rstrip("/")
        try:
            speed = float(self.db.get("zundamon_speed", 1.0)) * (1 + rate / 20)
        except (TypeError, ValueError):
            if status: status.config(text="AI 음성 설정 값이 올바르지 않습니다. 홈의 AI 음성 설정을 확인해 주세요.", fg="#b95140")
            return
        payload = json.dumps({
            "text": text, "text_language": "ja", "speed": max(0.5, min(2.0, speed)),
        }).encode("utf-8")
        if status: status.config(text="ずんだもん AI 서버와 음성을 준비하고 있어요...", fg="#66776f")
        def run():
            try:
                if not self.zundamon_api_available(url, timeout=2):
                    # A listen action should also recover a stopped server, not require a separate setup step.
                    self.start_zundamon_api(status)
                    for _ in range(180):
                        if self.zundamon_api_available(url, timeout=2):
                            break
                        threading.Event().wait(1)
                    else:
                        raise OSError("AI 서버 준비 시간이 초과됐습니다.")
                if status: self.after(0, lambda: status.winfo_exists() and status.config(text="ずんだもん AI 음성이 발음을 만들고 있어요...", fg="#66776f"))
                request = urllib.request.Request(url + "/", data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=90) as response:
                    audio = response.read()
                if not audio.startswith(b"RIFF"):
                    raise OSError("ずんだもん API가 WAV 오디오를 반환하지 않았습니다.")
                path = tempfile.NamedTemporaryFile(prefix="haru_japanese_", suffix=".wav", delete=False).name
                with open(path, "wb") as audio_file: audio_file.write(audio)
                self.speech_audio_path = path
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                if status: self.after(0, lambda: status.config(text="ずんだもん AI 음성으로 재생 중이에요.", fg="#165b52"))
            except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
                message = "ずんだもん AI 서버를 자동으로 시작했지만 준비되지 않았어요. 처음 실행이라면 모델과 Python 환경 설치가 필요할 수 있습니다. AI 음성 설정에서 서버 창의 오류를 확인해 주세요."
                self.after(0, lambda: status.config(text=message, fg="#b95140") if status else messagebox.showinfo("ずんだもん AI 음성", message))
        threading.Thread(target=run, daemon=True).start()

    def stop_speech(self):
        winsound.PlaySound(None, winsound.SND_PURGE)

    def show_kanji_writing(self):
        if self.selected_level not in CONTENT:
            self.select_level("N5"); return
        data = self.current_content()["kanji"]; self.writing_index = 0
        main = self.page("학습", "한자 쓰기 연습", "참고 획순과 견본을 보고 빈 칸에 직접 써 보세요. 입력 확인은 글자 일치만 검사하며 필체 인식은 하지 않습니다.")
        card = self.card(main); card.pack(fill="both", expand=True)
        target = tk.Label(card, font=("맑은 고딕", 84, "bold"), fg="#165b52", bg="white"); target.pack(pady=(28, 0))
        info = tk.Label(card, font=("맑은 고딕", 15), fg="#173c35", bg="white"); info.pack(pady=4)
        practice = tk.Text(card, height=7, font=("Yu Gothic", 28), relief="solid", borderwidth=1, padx=16, pady=12)
        practice.pack(fill="x", padx=70, pady=16)
        hint = tk.Label(card, font=("맑은 고딕", 10), fg="#66776f", bg="white"); hint.pack()
        strokes = tk.Label(card, font=("맑은 고딕", 10), fg="#a2543e", bg="white", wraplength=760, justify="center"); strokes.pack(pady=(8, 0))
        answer = ttk.Entry(card, justify="center", font=("Yu Gothic", 24), width=7); answer.pack(pady=(8, 0))
        feedback = tk.Label(card, font=("맑은 고딕", 10), fg="#66776f", bg="white"); feedback.pack(pady=(5, 0))
        canvas, stroke_count, clear_canvas = self.make_writing_canvas(card, len(WRITING_GUIDES.get(data[0][0], ())))
        tk.Label(card, text="마우스나 터치로 큰 칸에 직접 써 보세요. 획 수는 연습 기록이며 자동 필체 채점은 하지 않습니다.", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(pady=(7, 0))
        def render():
            char, reading, meaning, example = data[self.writing_index]
            guide_steps = WRITING_GUIDES.get(char, [])
            target.config(text=char); info.config(text=f"읽기: {reading} · 뜻: {meaning}"); hint.config(text=f"핵심 어휘: {example} · 큰 칸에 {char}를 직접 써 보세요."); strokes.config(text="참고 획순: " + "  →  ".join(guide_steps or ["이 글자는 참고 획순 안내가 준비 중입니다."])); practice.delete("1.0", "end"); answer.delete(0, "end"); clear_canvas(len(guide_steps)); feedback.config(text="")
        def check():
            char = data[self.writing_index][0]
            if answer.get().strip() == char:
                self.db.record_answer(f"{self.selected_level}:kanji:{char}", True); feedback.config(text="맞게 입력했어요. 큰 칸에서도 같은 글자를 반복해 보세요.", fg="#165b52")
            else:
                self.db.record_answer(f"{self.selected_level}:kanji:{char}", False); feedback.config(text=f"입력 견본은 「{char}」입니다. 위 참고 순서를 보며 다시 써 보세요.", fg="#b95140")
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
        ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
        ttk.Button(controls, text="발음 듣기", command=lambda: self.speak_japanese(data[self.writing_index][0])).pack(side="left", padx=4)
        ttk.Button(controls, text="획순 단계 보기", command=lambda: self.show_stroke_steps(data[self.writing_index][0])).pack(side="left", padx=4)
        ttk.Button(controls, text="입력 확인", command=check).pack(side="left", padx=4)
        ttk.Button(controls, text="그림 지우기", command=clear_canvas).pack(side="left", padx=4)
        ttk.Button(controls, text="다음", style="Accent.TButton", command=lambda: move(1)).pack(side="left", padx=4)
        def move(step): self.writing_index = (self.writing_index + step) % len(data); render()
        render()

    def make_writing_canvas(self, parent, expected_strokes=0):
        frame = tk.Frame(parent, bg="white"); frame.pack(pady=(12, 0))
        canvas = tk.Canvas(frame, width=400, height=180, bg="#fbfcf9", highlightbackground="#cfd9ce", highlightthickness=1, cursor="pencil")
        canvas.pack()
        count = tk.Label(frame, text="그린 획: 0", font=("맑은 고딕", 9), fg="#718078", bg="white"); count.pack(pady=(3, 0))
        state = {"last": None, "strokes": 0, "expected": expected_strokes}
        def update_count():
            suffix = f" / 참고 {state['expected']}획" if state["expected"] else ""
            color = "#165b52" if state["expected"] and state["strokes"] == state["expected"] else "#718078"
            count.config(text=f"그린 획: {state['strokes']}{suffix}", fg=color)
        def start(event):
            state["last"] = (event.x, event.y); state["strokes"] += 1; update_count()
        def draw(event):
            if state["last"]:
                x, y = state["last"]; canvas.create_line(x, y, event.x, event.y, fill="#173c35", width=4, capstyle="round", smooth=True); state["last"] = (event.x, event.y)
        def end(event): state["last"] = None
        def clear(expected=None):
            if expected is not None: state["expected"] = expected
            canvas.delete("all"); state["last"] = None; state["strokes"] = 0; update_count()
        canvas.bind("<ButtonPress-1>", start); canvas.bind("<B1-Motion>", draw); canvas.bind("<ButtonRelease-1>", end)
        return canvas, count, clear

    def show_stroke_steps(self, char):
        steps = WRITING_GUIDES.get(char)
        if not steps:
            messagebox.showinfo("획순 안내", f"「{char}」의 단계별 획순 안내는 아직 준비 중입니다. 견본을 보고 천천히 연습해 보세요.")
            return
        dialog = tk.Toplevel(self); dialog.title(f"{char} 획순 단계"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        tk.Label(dialog, text=char, font=("Yu Gothic", 72, "bold"), fg="#165b52", bg="white").pack(padx=70, pady=(24, 0))
        position = tk.Label(dialog, font=("맑은 고딕", 10, "bold"), fg="#a2543e", bg="white"); position.pack(pady=(4, 0))
        instruction = tk.Label(dialog, font=("맑은 고딕", 15), fg="#173c35", bg="white", wraplength=420, justify="center", height=3); instruction.pack(padx=30, pady=10)
        index = [0]
        def render():
            position.config(text=f"{index[0] + 1} / {len(steps)} 획")
            instruction.config(text=steps[index[0]])
        controls = tk.Frame(dialog, bg="white"); controls.pack(pady=(4, 24))
        ttk.Button(controls, text="이전 획", command=lambda: move(-1)).pack(side="left", padx=4)
        ttk.Button(controls, text="다음 획", style="Accent.TButton", command=lambda: move(1)).pack(side="left", padx=4)
        def move(change):
            index[0] = (index[0] + change) % len(steps); render()
        render()

    def show_sentence_building(self):
        if self.selected_level not in CONTENT:
            self.select_level("N5"); return
        items = SENTENCE_BUILDING[self.selected_level]; state = {"index": 0, "chosen": []}
        main = self.page("학습", "문장 만들기", "단어 조각을 눌러 자연스러운 일본어 문장을 완성하세요.")
        card = self.card(main); card.pack(fill="both", expand=True)
        cue = tk.Label(card, font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white", wraplength=720, justify="center"); cue.pack(pady=(34, 10))
        answer = tk.Label(card, font=("Yu Gothic", 24, "bold"), fg="#165b52", bg="#f5f8f3", wraplength=720, justify="center", height=2); answer.pack(fill="x", padx=35, pady=8)
        choices = tk.Frame(card, bg="white"); choices.pack(fill="x", padx=35, pady=12)
        feedback = tk.Label(card, font=("맑은 고딕", 11), fg="#66776f", bg="white", wraplength=720); feedback.pack(pady=(2, 14))
        def render():
            korean, correct, distractors = items[state["index"]]; state["correct"] = correct; state["available"] = correct + distractors; random.shuffle(state["available"]); state["chosen"] = []
            cue.config(text=korean); answer.config(text="여기에 조각을 순서대로 선택하세요"); feedback.config(text="")
            for child in choices.winfo_children(): child.destroy()
            for index, chunk in enumerate(state["available"]):
                ttk.Button(choices, text=chunk, command=lambda value=chunk: choose(value)).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
                choices.columnconfigure(index % 3, weight=1)
        def choose(chunk):
            if chunk not in state["available"]: return
            state["chosen"].append(chunk); state["available"].remove(chunk)
            answer.config(text=" ".join(state["chosen"]))
            for child in choices.winfo_children(): child.destroy()
            for index, value in enumerate(state["available"]):
                ttk.Button(choices, text=value, command=lambda item=value: choose(item)).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
                choices.columnconfigure(index % 3, weight=1)
        def check():
            korean, correct, _ = items[state["index"]]; content_id = f"{self.selected_level}:sentence:{'|'.join(correct)}"
            if state["chosen"] == correct:
                self.db.record_answer(content_id, True); feedback.config(text="정확해요! 어순과 조사를 함께 확인해 보세요.", fg="#165b52")
            else:
                self.db.record_answer(content_id, False); feedback.config(text="정답: " + " ".join(correct), fg="#b95140")
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
        ttk.Button(controls, text="초기화", command=render).pack(side="left", padx=4)
        ttk.Button(controls, text="정답 확인", command=check).pack(side="left", padx=4)
        ttk.Button(controls, text="다음 문장", style="Accent.TButton", command=lambda: next_item()).pack(side="left", padx=4)
        def next_item(): state["index"] = (state["index"] + 1) % len(items); render()
        render()

    def show_dictation(self):
        if self.selected_level not in CONTENT:
            self.select_level("N5"); return
        words = self.current_content()["words"]
        self.dictation_index = 0
        main = self.page("학습", "단어 받아쓰기", "발음을 듣고 일본어 표기와 읽기를 직접 입력하세요. AI 음성이 자동으로 준비됩니다.")
        card = self.card(main); card.pack(fill="both", expand=True)
        hint = tk.Label(card, font=("맑은 고딕", 15, "bold"), fg="#173c35", bg="white"); hint.pack(pady=(32, 10))
        entry = ttk.Entry(card, justify="center", font=("Yu Gothic", 28), width=18); entry.pack(pady=10)
        feedback = tk.Label(card, font=("맑은 고딕", 11), fg="#66776f", bg="white", wraplength=700); feedback.pack(pady=8)
        def render():
            word, reading, meaning, example = words[self.dictation_index]
            hint.config(text=f"뜻: {meaning}  ·  예문: {example}"); entry.delete(0, "end"); feedback.config(text="먼저 발음을 듣고 입력해 보세요.", fg="#66776f")
        def check():
            word, reading, meaning, _ = words[self.dictation_index]; guess = entry.get().strip()
            content_id = f"{self.selected_level}:dictation:{word}"
            if guess == word:
                self.db.record_answer(content_id, True); feedback.config(text=f"정답! {word} ({reading})", fg="#165b52")
            else:
                self.db.record_answer(content_id, False); feedback.config(text=f"정답: {word} ({reading})", fg="#b95140")
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
        ttk.Button(controls, text="느리게 듣기", command=lambda: self.speak_japanese(words[self.dictation_index][0], feedback, -3)).pack(side="left", padx=4)
        ttk.Button(controls, text="발음 듣기", command=lambda: self.speak_japanese(words[self.dictation_index][0], feedback)).pack(side="left", padx=4)
        ttk.Button(controls, text="입력 확인", command=check).pack(side="left", padx=4)
        ttk.Button(controls, text="다음", style="Accent.TButton", command=lambda: next_item()).pack(side="left", padx=4)
        def next_item(): self.dictation_index = (self.dictation_index + 1) % len(words); render()
        render()

    def start_diagnostic(self):
        self.start_quiz(mode="diagnostic", title="12문항 실력 진단")

    def question_pool(self, mode, kana_set=None):
        pool = []
        if mode == "diagnostic":
            # Two literacy checks plus one vocabulary and grammar check per JLPT level.
            chars = kana_set or KANA
            for char, reading in random.sample(chars, 2):
                pool.append((f"「{char}」의 발음은 무엇인가요?", reading, [x[1] for x in chars if x[1] != reading], f"kana:{char}"))
            for level in ("N5", "N4", "N3", "N2", "N1"):
                word, reading, meaning, _ = random.choice(CONTENT[level]["words"])
                pool.append((f"「{word}」({reading})의 뜻은 무엇인가요?", meaning, [x[2] for x in CONTENT[level]["words"] if x[2] != meaning], f"{level}:word:{word}"))
                pattern, explanation, _ = random.choice(CONTENT[level]["grammar"])
                pool.append((f"「{pattern}」의 설명으로 알맞은 것은?", explanation, [x[1] for x in CONTENT[level]["grammar"] if x[1] != explanation], f"{level}:grammar:{pattern}"))
                prompt, answer, distractors = random.choice(GRAMMAR_CLOZE[level])
                pool.append((f"[문법 빈칸] {prompt}", answer, distractors, f"{level}:cloze:{prompt}"))
                prompt, answer, distractors = random.choice(WORD_CLOZE[level])
                pool.append((f"[단어 예문 빈칸] {prompt}", answer, distractors, f"{level}:word-cloze:{prompt}"))
            return pool
        if mode == "kana":
            chars = kana_set or KANA
            for char, reading in chars:
                pool.append((f"「{char}」의 발음은 무엇인가요?", reading, [x[1] for x in chars if x[1] != reading], f"kana:{char}"))
        if mode in ("reading", "mock"):
            for index, (title, passage, question, answer, options) in enumerate(READING_PASSAGES.get(self.selected_level, [])):
                pool.append((f"[독해 · {title}]\n{passage}\n\n{question}", answer, [option for option in options if option != answer], f"{self.selected_level}:reading:{index}"))
        if mode in ("listening", "mock"):
            for index, (dialogue, question, answer, options) in enumerate(LISTENING_DIALOGUES.get(self.selected_level, [])):
                pool.append((f"[청해 연습 · 대화문]\n{dialogue}\n\n{question}", answer, [option for option in options if option != answer], f"{self.selected_level}:listening:{index}"))
        levels = [self.selected_level]
        for level in levels:
            if level not in CONTENT: continue
            content = CONTENT[level]
            if mode in ("words", "mixed", "review", "weak", "diagnostic", "mock"):
                for word, reading, meaning, _ in content["words"]: pool.append((f"「{word}」({reading})의 뜻은 무엇인가요?", meaning, [x[2] for x in content["words"] if x[2] != meaning], f"{level}:word:{word}"))
                for prompt, answer, distractors in WORD_CLOZE[level]:
                    pool.append((f"[단어 예문 빈칸] {prompt}", answer, distractors, f"{level}:word-cloze:{prompt}"))
            if mode in ("kanji", "mixed", "diagnostic", "mock"):
                for char, reading, meaning, _ in content["kanji"]: pool.append((f"한자 「{char}」의 뜻은 무엇인가요?", meaning, [x[2] for x in content["kanji"] if x[2] != meaning], f"{level}:kanji:{char}"))
            if mode in ("grammar", "mixed", "diagnostic", "mock"):
                for pattern, explanation, example in content["grammar"]: pool.append((f"「{pattern}」의 설명으로 알맞은 것은?", explanation, [x[1] for x in content["grammar"] if x[1] != explanation], f"{level}:grammar:{pattern}"))
                for prompt, answer, distractors in GRAMMAR_CLOZE[level]:
                    pool.append((f"[문법 빈칸] {prompt}", answer, distractors, f"{level}:cloze:{prompt}"))
            if mode in ("sentence", "mixed", "mock"):
                for korean, chunks, distractors in SENTENCE_BUILDING[level]:
                    answer = " ".join(chunks); alternatives = set()
                    while len(alternatives) < 3:
                        candidate = " ".join(random.sample(chunks, len(chunks)))
                        if candidate != answer: alternatives.add(candidate)
                    pool.append((f"[문장 만들기] {korean}\n알맞은 문장 순서는?", answer, list(alternatives), f"{level}:sentence:{'|'.join(chunks)}"))
            if mode in ("dictation",):
                for word, reading, meaning, _ in content["words"]:
                    pool.append((f"[받아쓰기] 「{reading}」의 일본어 표기는?", word, [item[0] for item in content["words"] if item[0] != word], f"{level}:dictation:{word}"))
        if mode == "favorites":
            ids = self.db.favorite_ids()
            base_pool = self.question_pool("mixed") + self.question_pool("kanji") + self.question_pool("grammar")
            pool = [item for item in base_pool if item[3] in ids]
        if mode in ("review", "weak"):
            ids = {row[0] for row in (self.db.due_items() if mode == "review" else self.db.weak_items())}
            all_items = (self.question_pool("mixed") + self.question_pool("kana") +
                          self.question_pool("reading") + self.question_pool("listening") +
                          self.question_pool("dictation"))
            pool = [item for item in all_items if item[3] in ids]
        return pool

    def start_quiz(self, mode="mixed", kana_set=None, title=None):
        if mode in ("reading", "listening", "mock") and self.selected_level not in CONTENT:
            messagebox.showinfo("시험 대비", "독해·청해·모의고사는 N5 과정을 선택한 뒤 시작할 수 있어요.")
            self.select_level("N5")
            return
        pool = self.question_pool(mode, kana_set)
        if not pool:
            messagebox.showinfo("복습", "지금 예정된 복습이 없어요. 새 학습을 진행해 보세요."); return
        self.quiz_mode, self.quiz_pool, self.quiz_position, self.quiz_score = mode, pool, 0, 0
        self.quiz_answered = False; self.quiz_after_id = None; self.quiz_option_values = []
        self.quiz_limit = 12 if mode in ("diagnostic", "mock") else min(10, len(pool)); random.shuffle(self.quiz_pool)
        is_review = mode in ("review", "weak")
        default_title = "예정 복습" if mode == "review" else "오답 노트 복습" if mode == "weak" else "즐겨찾기 퀴즈" if mode == "favorites" else "오늘의 퀴즈"
        main = self.page("복습" if is_review else "학습", title or default_title, f"{self.quiz_limit}문항 · 1~4번 답 선택 · Enter 다음 문제 · Space 청해 다시 듣기")
        self.quiz_progress = ttk.Progressbar(main, maximum=self.quiz_limit); self.quiz_progress.pack(fill="x", pady=(0, 16))
        self.quiz_prompt = tk.Label(main, font=("맑은 고딕", 22, "bold"), fg="#165b52", bg="white", wraplength=650, justify="center", height=4)
        self.quiz_prompt.pack(fill="x", pady=6)
        self.quiz_options = tk.Frame(main, bg="#f4f6f0"); self.quiz_options.pack(fill="x", pady=10)
        self.quiz_feedback = tk.Label(main, font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0", wraplength=650, justify="center"); self.quiz_feedback.pack(pady=9)
        self.bind("<Key-1>", lambda event: self.quiz_key_answer(0))
        self.bind("<Key-2>", lambda event: self.quiz_key_answer(1))
        self.bind("<Key-3>", lambda event: self.quiz_key_answer(2))
        self.bind("<Key-4>", lambda event: self.quiz_key_answer(3))
        self.bind("<Return>", self.quiz_key_next)
        self.bind("<space>", self.quiz_key_listen)
        self.next_question()

    def next_question(self):
        if self.quiz_position >= self.quiz_limit:
            self.finish_quiz(); return
        for child in self.quiz_options.winfo_children(): child.destroy()
        prompt, answer, distractors, content_id = self.quiz_pool[self.quiz_position]
        options = random.sample(distractors, min(3, len(distractors))) + [answer]; random.shuffle(options)
        self.quiz_answered = False; self.quiz_option_values = options
        self.current_question = (prompt, answer, content_id)
        listening = ":listening:" in content_id
        if listening:
            dialogue, question = prompt.split("\n\n", 1)
            self.current_dialogue = dialogue.replace("[청해 연습 · 대화문]\n", "")
            self.quiz_prompt.config(text="[청해 연습]\n먼저 대화를 듣고 질문에 답해 보세요.\n\n" + question)
        else:
            self.current_dialogue = None; self.quiz_prompt.config(text=prompt)
        self.quiz_feedback.config(text=f"문제 {self.quiz_position + 1} / {self.quiz_limit}", fg="#66776f"); self.quiz_progress["value"] = self.quiz_position
        option_row_offset = 0
        if listening:
            listen_controls = tk.Frame(self.quiz_options, bg="#f4f6f0"); listen_controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            ttk.Button(listen_controls, text="느리게 듣기", command=lambda: self.speak_japanese(self.current_dialogue, self.quiz_feedback, -3)).pack(side="left", padx=4)
            ttk.Button(listen_controls, text="보통 속도로 듣기", command=lambda: self.speak_japanese(self.current_dialogue, self.quiz_feedback, 0)).pack(side="left", padx=4)
            ttk.Button(listen_controls, text="재생 중지", command=self.stop_speech).pack(side="left", padx=4)
            ttk.Button(listen_controls, text="대본 보기", command=self.reveal_dialogue).pack(side="right", padx=4)
            option_row_offset = 1
            self.after(250, lambda dialogue=self.current_dialogue: self.speak_japanese(dialogue, self.quiz_feedback, -3))
        for i, option in enumerate(options): ttk.Button(self.quiz_options, text=option, command=lambda choice=option: self.check_answer(choice)).grid(row=i // 2 + option_row_offset, column=i % 2, sticky="ew", padx=5, pady=5)
        self.quiz_options.columnconfigure(0, weight=1); self.quiz_options.columnconfigure(1, weight=1)

    def reveal_dialogue(self):
        if self.current_dialogue:
            self.quiz_prompt.config(text="[청해 연습 · 대본]\n" + self.current_dialogue + "\n\n" + self.current_question[0].split("\n\n", 1)[1])

    def check_answer(self, choice):
        if self.quiz_answered:
            return
        self.quiz_answered = True
        self.stop_speech()
        for child in self.quiz_options.winfo_children():
            if isinstance(child, ttk.Button):
                child.configure(state="disabled")
            for nested in child.winfo_children():
                if isinstance(nested, ttk.Button): nested.configure(state="disabled")
        prompt, answer, content_id = self.current_question; correct = choice == answer; self.db.record_answer(content_id, correct)
        if correct: self.quiz_score += 1; text, color = "정답이에요! 다음 문제로 넘어갑니다.", "#165b52"
        else: text, color = f"정답: {answer}\n간격 복습 목록에 추가했어요.", "#b95140"
        self.quiz_feedback.config(text=text, fg=color); self.quiz_position += 1; self.quiz_after_id = self.after(850 if correct else 1500, self.next_question)

    def quiz_key_answer(self, index):
        if not self.quiz_answered and index < len(self.quiz_option_values):
            self.check_answer(self.quiz_option_values[index])
        return "break"

    def quiz_key_next(self, event=None):
        if self.quiz_answered:
            if self.quiz_after_id:
                self.after_cancel(self.quiz_after_id); self.quiz_after_id = None
            self.next_question()
        return "break"

    def quiz_key_listen(self, event=None):
        if self.current_dialogue:
            self.speak_japanese(self.current_dialogue, self.quiz_feedback, -3)
        return "break"

    def clear_quiz_shortcuts(self):
        for sequence in ("<Key-1>", "<Key-2>", "<Key-3>", "<Key-4>", "<Return>", "<space>"):
            self.unbind(sequence)

    def finish_quiz(self):
        self.stop_speech()
        self.clear_quiz_shortcuts()
        rate = round(self.quiz_score * 100 / self.quiz_limit)
        self.db.record_quiz_result(self.quiz_mode, self.selected_level, self.quiz_score, self.quiz_limit)
        if self.quiz_mode == "diagnostic":
            recommended = "문자" if rate < 35 else "N5" if rate < 55 else "N4" if rate < 70 else "N3" if rate < 82 else "N2" if rate < 93 else "N1"
            self.selected_level = recommended; self.db.set("level", recommended)
            messagebox.showinfo("진단 결과", f"{self.quiz_limit}문항 중 {self.quiz_score}문항 정답 ({rate}%)\n추천 시작 과정: {recommended}\n\n진단은 학습 시작점을 돕는 간단한 참고 결과입니다.")
        else: messagebox.showinfo("퀴즈 완료", f"{self.quiz_limit}문항 중 {self.quiz_score}문항 정답 ({rate}%)\n틀린 문제는 자동으로 간격 복습에 등록했습니다.")
        self.show_home()

    def show_review(self):
        main = self.page("복습", "간격 복습", "틀린 문제와 오늘 예정된 문제를 다시 풀어 기억을 오래 유지하세요.")
        rows = self.db.due_items(); _, _, _, due = self.db.stats()
        tk.Label(main, text=f"오늘 복습할 항목 {due}개", font=("맑은 고딕", 16, "bold"), fg="#165b52", bg="#f4f6f0").pack(anchor="w", pady=(0, 12))
        if not rows: tk.Label(main, text="복습 대기 항목이 없어요. 오늘도 훌륭하게 해냈습니다.", font=("맑은 고딕", 12), fg="#66776f", bg="#f4f6f0").pack(pady=55)
        for content_id, correct, wrong, due_date in rows:
            row = self.card(main); row.pack(fill="x", pady=3)
            readable = (content_id.replace("kana:", "문자 · ").replace(":word:", " · 단어 · ")
                         .replace(":word-cloze:", " · 단어 예문 빈칸 · ")
                         .replace(":kanji:", " · 한자 · ").replace(":grammar:", " · 문법 · ")
                         .replace(":cloze:", " · 문법 빈칸 · ").replace(":sentence:", " · 문장 만들기 · ").replace(":dictation:", " · 받아쓰기 · "))
            tk.Label(row, text=readable, font=("맑은 고딕", 11, "bold"), fg="#173c35", bg="white").pack(side="left", padx=15, pady=13)
            tk.Label(row, text=f"정답 {correct} · 오답 {wrong} · 예정 {due_date}", font=("맑은 고딕", 9), fg="#b95140", bg="white").pack(side="right", padx=15)
        ttk.Button(main, text="예정 복습 시작", style="Accent.TButton", command=lambda: self.start_quiz(mode="review")).pack(anchor="e", pady=18)

    def readable_content_id(self, content_id):
        return (content_id.replace("kana:", "문자 · ").replace(":word:", " · 단어 · ")
                .replace(":word-cloze:", " · 단어 예문 빈칸 · ")
                .replace(":kanji:", " · 한자 · ").replace(":grammar:", " · 문법 · ")
                .replace(":cloze:", " · 문법 빈칸 · ")
                .replace(":sentence:", " · 문장 만들기 · ").replace(":dictation:", " · 받아쓰기 · ")
                .replace(":reading:", " · 독해 · ").replace(":listening:", " · 청해 · "))

    def show_wrong_notebook(self):
        main = self.page("복습", "오답 노트", "정답보다 오답이 많은 항목입니다. 약한 부분부터 다시 퀴즈로 확인하세요.")
        rows = self.db.weak_items()
        if not rows:
            tk.Label(main, text="아직 쌓인 오답이 없어요. 퀴즈를 풀면 약한 항목이 여기에 표시됩니다.", font=("맑은 고딕", 12), fg="#66776f", bg="#f4f6f0", wraplength=700).pack(pady=55)
            return
        for content_id, correct, wrong, due_date in rows:
            row = self.card(main); row.pack(fill="x", pady=4)
            tk.Label(row, text=self.readable_content_id(content_id), font=("맑은 고딕", 11, "bold"), fg="#173c35", bg="white").pack(side="left", padx=16, pady=14)
            tk.Label(row, text=f"오답 {wrong} · 정답 {correct}", font=("맑은 고딕", 10, "bold"), fg="#b95140", bg="white").pack(side="right", padx=16)
        ttk.Button(main, text="오답 다시 풀기", style="Accent.TButton", command=lambda: self.start_quiz(mode="weak")).pack(anchor="e", pady=18)

    def show_stats(self):
        main = self.page("통계", "학습 통계", "숫자는 이 기기의 오프라인 학습 기록만으로 계산됩니다.")
        days, correct, wrong, due = self.db.stats(); total = correct + wrong; rate = round(correct * 100 / total) if total else 0
        grid = tk.Frame(main, bg="#f4f6f0"); grid.pack(fill="x")
        for i, (label, value) in enumerate((("학습한 날", f"{days}일"), ("연속 학습", f"{self.db.streak()}일"), ("푼 문제", f"{total}개"), ("정답률", f"{rate}%"), ("복습 대기", f"{due}개"))):
            item = self.card(grid); item.grid(row=0, column=i, sticky="nsew", padx=(0, 7)); grid.columnconfigure(i, weight=1)
            tk.Label(item, text=label, font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=13, pady=(14, 3))
            tk.Label(item, text=value, font=("맑은 고딕", 21, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=13, pady=(0, 14))
        tk.Label(main, text="학습 방법", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(32, 8))
        tk.Label(main, text="정답은 1일, 2일, 4일, 7일, 14일, 30일, 60일 간격으로 다시 제시됩니다. 오답은 바로 복습 목록에 돌아옵니다.", font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0", wraplength=800, justify="left").pack(anchor="w")
        results = self.db.category_results()
        if results:
            tk.Label(main, text="영역별 시험 기록", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(28, 9))
            records = tk.Frame(main, bg="#f4f6f0"); records.pack(fill="x")
            labels = {"words": "단어", "kanji": "한자", "grammar": "문법", "reading": "독해", "listening": "청해", "sentence": "문장 만들기", "dictation": "받아쓰기", "favorites": "즐겨찾기", "mock": "모의고사", "mixed": "혼합", "kana": "문자"}
            for index, (mode, score, total) in enumerate(results):
                item = self.card(records); item.grid(row=index // 4, column=index % 4, sticky="nsew", padx=4, pady=4)
                records.columnconfigure(index % 4, weight=1)
                tk.Label(item, text=labels.get(mode, mode), font=("맑은 고딕", 10, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=12, pady=(11, 2))
                tk.Label(item, text=f"{round(score * 100 / total)}% · {score}/{total}", font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", padx=12, pady=(0, 11))
        levels = self.db.level_results()
        if levels:
            tk.Label(main, text="레벨별 실전 준비도", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(26, 8))
            for level, score, total in levels:
                row = tk.Frame(main, bg="#f4f6f0"); row.pack(fill="x", pady=3)
                tk.Label(row, text=level, width=5, font=("맑은 고딕", 11, "bold"), fg="#165b52", bg="#f4f6f0").pack(side="left")
                progress = ttk.Progressbar(row, maximum=100, value=round(score * 100 / total)); progress.pack(side="left", fill="x", expand=True, padx=10)
                tk.Label(row, text=f"{round(score * 100 / total)}% ({score}/{total})", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(side="right")
        weaknesses = self.db.weakness_categories()
        if weaknesses:
            tk.Label(main, text="약점 유형 분석", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(26, 8))
            tk.Label(main, text="직접 푼 문제의 유형별 정답률입니다. 낮은 영역부터 다시 연습해 보세요.", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(0, 6))
            for label, correct, wrong in weaknesses:
                total_for_kind = correct + wrong; percent = round(correct * 100 / total_for_kind)
                row = tk.Frame(main, bg="#f4f6f0"); row.pack(fill="x", pady=3)
                tk.Label(row, text=label, width=12, font=("맑은 고딕", 10, "bold"), fg="#165b52", bg="#f4f6f0").pack(side="left")
                ttk.Progressbar(row, maximum=100, value=percent).pack(side="left", fill="x", expand=True, padx=10)
                tk.Label(row, text=f"{percent}% ({correct}/{total_for_kind})", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(side="right")


if __name__ == "__main__":
    enable_high_dpi()
    JapaneseStudyApp().mainloop()
