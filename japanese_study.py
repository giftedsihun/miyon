import ctypes
import json
import random
import sqlite3
import subprocess
import threading
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

from content import (CONTENT, HIRAGANA, HIRAGANA_EXTRA, HIRAGANA_ROWS, KANA,
                      KANA_NOTES, KATAKANA, KATAKANA_EXTRA, KATAKANA_ROWS,
                      KOREAN_ROWS, LEVELS, LISTENING_DIALOGUES, READING_PASSAGES,
                      ROMAJI_ROWS, WRITING_GUIDES)

APP_TITLE = "하루 일본어"
DATA_DIR = Path.home() / ".haru_japanese"
DB_PATH = DATA_DIR / "progress.db"
SRS_DAYS = (1, 2, 4, 7, 14, 30, 60)
LEVEL_ORDER = ["초보", "문자", "N5", "N4", "N3", "N2", "N1"]


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
        self.connection.execute("CREATE TABLE IF NOT EXISTS activity (day TEXT PRIMARY KEY, completed INTEGER NOT NULL DEFAULT 0)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS review (
            content_id TEXT PRIMARY KEY, correct INTEGER NOT NULL DEFAULT 0,
            wrong INTEGER NOT NULL DEFAULT 0, last_seen TEXT, due_date TEXT,
            interval_step INTEGER NOT NULL DEFAULT 0)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, taken_on TEXT NOT NULL, mode TEXT NOT NULL,
            level TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL)""")
        # Migrate databases created by earlier builds.
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(review)")}
        for column, definition in (("due_date", "TEXT"), ("interval_step", "INTEGER NOT NULL DEFAULT 0")):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE review ADD COLUMN {column} {definition}")
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


class JapaneseStudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.tk.call("tk", "scaling", self.winfo_fpixels("1i") / 72.0)
        self.title(APP_TITLE); self.geometry("1120x760"); self.minsize(900, 620); self.configure(bg="#f4f6f0")
        self.db = Database(); self.selected_level = self.db.get("level", "초보")
        self.configure_styles(); self.show_home()

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
        self.clear(); self.header(active)
        main = tk.Frame(self, bg="#f4f6f0"); main.pack(fill="both", expand=True, padx=58, pady=32)
        tk.Label(main, text=title, font=("맑은 고딕", 27, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w")
        tk.Label(main, text=subtitle, font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(6, 22))
        return main

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
        tk.Label(main, text="빠른 시작", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(30, 12))
        quick = tk.Frame(main, bg="#f4f6f0"); quick.pack(fill="x")
        for i, (title, detail, command) in enumerate((("오늘의 복습", f"지금 풀 문제 {due}개", lambda: self.start_quiz(mode="review")), ("문자 과정", "히라가나 · 가타카나", self.show_kana_menu), ("모의고사", "어휘 · 문법 · 독해 · 청해", lambda: self.start_quiz(mode="mock")), ("과정 선택", "내 목표 직접 설정", self.show_level_select))):
            item = self.card(quick); item.grid(row=0, column=i, sticky="nsew", padx=(0, 9), pady=2); quick.columnconfigure(i, weight=1)
            tk.Label(item, text=title, font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=16, pady=(17, 4))
            tk.Label(item, text=detail, font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=16)
            ttk.Button(item, text="열기", command=command).pack(anchor="w", padx=16, pady=15)

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
            lessons = (("단어", "의미와 예문으로 익히기", lambda: self.show_catalog("words")), ("한자", "읽기와 핵심 어휘", lambda: self.show_catalog("kanji")), ("문법", "설명과 예문으로 정리", lambda: self.show_catalog("grammar")), ("독해", "짧은 지문으로 핵심 찾기", lambda: self.start_quiz(mode="reading")), ("청해 연습", "Windows 음성으로 대화 듣기", lambda: self.start_quiz(mode="listening")), ("한자 쓰기", "직접 써 보며 형태 익히기", self.show_kanji_writing), ("종합 모의고사", "어휘 · 문법 · 독해 · 청해", lambda: self.start_quiz(mode="mock")))
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
        main = self.page("학습", title, "한 줄씩 소리 내어 읽고, 글자를 눌러 크게 확인하세요.")
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
        tk.Button(parent, text=f"{char}\n{reading}", command=lambda: self.show_kana_detail(char, reading, accent), relief="flat", cursor="hand2", font=("맑은 고딕", 16, "bold"), fg=accent, bg="#f5f8f3", activebackground="#fff2e6", width=7, height=2).grid(row=row, column=column, sticky="nsew", padx=3, pady=3)

    def show_kana_detail(self, char, reading, accent):
        dialog = tk.Toplevel(self); dialog.title("글자 확인"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        tk.Label(dialog, text=char, font=("맑은 고딕", 70, "bold"), fg=accent, bg="white").pack(padx=70, pady=(30, 0))
        tk.Label(dialog, text=reading, font=("맑은 고딕", 20, "bold"), fg="#173c35", bg="white").pack()
        tk.Label(dialog, text="소리 내어 세 번 읽어 보세요.", font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(pady=12)
        controls = tk.Frame(dialog, bg="white"); controls.pack(pady=(0, 26))
        ttk.Button(controls, text="발음 듣기", command=lambda: self.speak_japanese(char)).pack(side="left", padx=4)
        ttk.Button(controls, text="닫기", command=dialog.destroy).pack(side="left", padx=4)

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

    def show_catalog(self, category):
        titles = {"words": "단어 카드", "kanji": "한자 카드", "grammar": "문법 학습"}; data = self.current_content()[category]; self.catalog_index = 0
        main = self.page("학습", titles[category], f"{self.selected_level} 과정 · 예문까지 읽고 다음 카드로 넘어가세요.")
        card = self.card(main); card.pack(fill="both", expand=True)
        title = tk.Label(card, font=("맑은 고딕", 33, "bold"), fg="#165b52", bg="white"); title.pack(pady=(55, 12))
        detail = tk.Label(card, font=("맑은 고딕", 16), fg="#173c35", bg="white", wraplength=760, justify="center"); detail.pack(padx=25)
        example = tk.Label(card, font=("맑은 고딕", 12), fg="#66776f", bg="white", wraplength=760, justify="center"); example.pack(pady=(15, 25))
        counter = tk.Label(card, font=("맑은 고딕", 10), fg="#718078", bg="white"); counter.pack()
        def render():
            item = data[self.catalog_index]
            if category == "words": title.config(text=item[0]); detail.config(text=f"{item[1]} · {item[2]}"); example.config(text=item[3])
            elif category == "kanji": title.config(text=item[0]); detail.config(text=f"읽기: {item[1]} · 뜻: {item[2]}"); example.config(text=f"핵심 어휘: {item[3]}")
            else: title.config(text=item[0], font=("맑은 고딕", 23, "bold")); detail.config(text=item[1]); example.config(text=item[2])
            counter.config(text=f"{self.catalog_index + 1} / {len(data)}")
        controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
        ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
        ttk.Button(controls, text="이 카테고리 퀴즈", style="Accent.TButton", command=lambda: self.start_quiz(mode=category)).pack(side="left", padx=4)
        if category in ("words", "grammar"):
            ttk.Button(controls, text="예문 듣기", command=lambda: self.speak_japanese(data[self.catalog_index][3] if category == "words" else data[self.catalog_index][2])).pack(side="left", padx=4)
        if category == "kanji":
            ttk.Button(controls, text="쓰기 연습", command=self.show_kanji_writing).pack(side="left", padx=4)
        ttk.Button(controls, text="다음", command=lambda: move(1)).pack(side="left", padx=4)
        def move(step): self.catalog_index = (self.catalog_index + step) % len(data); render()
        render()

    def speak_japanese(self, text, status=None, rate=0):
        """Use installed Windows voices without bundling network-dependent audio files."""
        self.stop_speech()
        rate = max(-10, min(10, int(rate)))
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$v = $s.GetInstalledVoices() | Where-Object {$_.VoiceInfo.Culture.Name -eq 'ja-JP'} | Select-Object -First 1; "
            "if ($v) {$s.SelectVoice($v.VoiceInfo.Name); $s.Rate = " + str(rate) + "; $s.Speak('" + text.replace("'", "''").replace("\n", " ") + "')} else {exit 2}"
        )
        if status: status.config(text="Windows 일본어 음성을 준비하고 있어요...", fg="#66776f")
        def run():
            try:
                process = subprocess.Popen(["powershell", "-NoProfile", "-Command", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.speech_process = process
                result_code = process.wait(timeout=45)
                is_current = self.speech_process is process
                if is_current: self.speech_process = None
                if not is_current: return
                if result_code == 0:
                    self.after(0, lambda: status.config(text="Windows 일본어 음성으로 재생했어요.", fg="#165b52") if status else None)
                else:
                    message = "이 PC에는 일본어 Windows 음성이 없습니다. 설정 > 시간 및 언어 > 언어 및 지역에서 일본어 음성 기능을 추가해 주세요."
                    self.after(0, lambda: status.config(text=message, fg="#b95140") if status else messagebox.showinfo("일본어 음성", message))
            except (OSError, subprocess.TimeoutExpired):
                if getattr(self, "speech_process", None):
                    self.speech_process.kill(); self.speech_process = None
                self.after(0, lambda: messagebox.showerror("음성 재생", "Windows 음성 서비스를 실행할 수 없습니다."))
        threading.Thread(target=run, daemon=True).start()

    def stop_speech(self):
        process = getattr(self, "speech_process", None)
        if process and process.poll() is None:
            process.kill()
        self.speech_process = None

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
            if mode in ("words", "mixed", "review", "diagnostic", "mock"):
                for word, reading, meaning, _ in content["words"]: pool.append((f"「{word}」({reading})의 뜻은 무엇인가요?", meaning, [x[2] for x in content["words"] if x[2] != meaning], f"{level}:word:{word}"))
            if mode in ("kanji", "mixed", "diagnostic", "mock"):
                for char, reading, meaning, _ in content["kanji"]: pool.append((f"한자 「{char}」의 뜻은 무엇인가요?", meaning, [x[2] for x in content["kanji"] if x[2] != meaning], f"{level}:kanji:{char}"))
            if mode in ("grammar", "mixed", "diagnostic", "mock"):
                for pattern, explanation, example in content["grammar"]: pool.append((f"「{pattern}」의 설명으로 알맞은 것은?", explanation, [x[1] for x in content["grammar"] if x[1] != explanation], f"{level}:grammar:{pattern}"))
        if mode == "review":
            ids = {row[0] for row in self.db.due_items()}
            all_items = (self.question_pool("mixed") + self.question_pool("kana") +
                         self.question_pool("reading") + self.question_pool("listening"))
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
        self.quiz_limit = 12 if mode in ("diagnostic", "mock") else min(10, len(pool)); random.shuffle(self.quiz_pool)
        main = self.page("학습" if mode != "review" else "복습", title or ("예정 복습" if mode == "review" else "오늘의 퀴즈"), f"{self.quiz_limit}문항 · 답을 선택하면 해설과 다음 문제가 표시됩니다.")
        self.quiz_progress = ttk.Progressbar(main, maximum=self.quiz_limit); self.quiz_progress.pack(fill="x", pady=(0, 16))
        self.quiz_prompt = tk.Label(main, font=("맑은 고딕", 22, "bold"), fg="#165b52", bg="white", wraplength=650, justify="center", height=4)
        self.quiz_prompt.pack(fill="x", pady=6)
        self.quiz_options = tk.Frame(main, bg="#f4f6f0"); self.quiz_options.pack(fill="x", pady=10)
        self.quiz_feedback = tk.Label(main, font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0", wraplength=650, justify="center"); self.quiz_feedback.pack(pady=9)
        self.next_question()

    def next_question(self):
        if self.quiz_position >= self.quiz_limit:
            self.finish_quiz(); return
        for child in self.quiz_options.winfo_children(): child.destroy()
        prompt, answer, distractors, content_id = self.quiz_pool[self.quiz_position]
        options = random.sample(distractors, min(3, len(distractors))) + [answer]; random.shuffle(options)
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
        self.stop_speech()
        for child in self.quiz_options.winfo_children():
            if isinstance(child, ttk.Button):
                child.configure(state="disabled")
            for nested in child.winfo_children():
                if isinstance(nested, ttk.Button): nested.configure(state="disabled")
        prompt, answer, content_id = self.current_question; correct = choice == answer; self.db.record_answer(content_id, correct)
        if correct: self.quiz_score += 1; text, color = "정답이에요! 다음 문제로 넘어갑니다.", "#165b52"
        else: text, color = f"정답: {answer}\n간격 복습 목록에 추가했어요.", "#b95140"
        self.quiz_feedback.config(text=text, fg=color); self.quiz_position += 1; self.after(850 if correct else 1500, self.next_question)

    def finish_quiz(self):
        self.stop_speech()
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
            readable = content_id.replace("kana:", "문자 · ").replace(":word:", " · 단어 · ").replace(":kanji:", " · 한자 · ").replace(":grammar:", " · 문법 · ")
            tk.Label(row, text=readable, font=("맑은 고딕", 11, "bold"), fg="#173c35", bg="white").pack(side="left", padx=15, pady=13)
            tk.Label(row, text=f"정답 {correct} · 오답 {wrong} · 예정 {due_date}", font=("맑은 고딕", 9), fg="#b95140", bg="white").pack(side="right", padx=15)
        ttk.Button(main, text="예정 복습 시작", style="Accent.TButton", command=lambda: self.start_quiz(mode="review")).pack(anchor="e", pady=18)

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
            labels = {"words": "단어", "kanji": "한자", "grammar": "문법", "reading": "독해", "listening": "청해", "mock": "모의고사", "mixed": "혼합", "kana": "문자"}
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


if __name__ == "__main__":
    enable_high_dpi()
    JapaneseStudyApp().mainloop()
