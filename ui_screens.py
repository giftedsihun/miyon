"""Focused Tkinter screen renderers kept separate from application state and actions."""

from datetime import date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import csv
import sqlite3

from content import CONTENT
from learning_services import (DEFAULT_REVIEW_LIMIT, LEVEL_ORDER, normalized_review_limit,
                               personal_word_import_rows)
from study_logic import study_plan_pace
from storage import DATA_DIR
from progress_logic import (ERROR_CAUSE_LABELS, achievement_milestones, daily_reminder,
                             course_progress_insight, daily_course_items,
                             error_cause_recommendation, error_cause_summary, quiz_trend_insight,
                            practice_progress_summary, review_workload_insight, weekly_activity_summary)
from storage import SRS_DAYS


QUIZ_MODE_LABELS = {
    "words": "단어", "kanji": "한자", "grammar": "문법", "reading": "독해",
    "listening": "청해", "sentence": "문장 만들기", "dictation": "받아쓰기",
    "favorites": "즐겨찾기", "mock": "모의고사", "mixed": "혼합", "kana": "문자",
    "review": "예정 복습", "weak": "오답 노트", "diagnostic": "진단", "retry": "오답 다시 풀기",
    "error-focus": "오답 원인 집중 연습", "personal-words": "나의 단어장",
}


def render_home(app):
    """Render the home dashboard while actions remain methods of the application."""
    main = app.page("홈", "오늘도 한 걸음, 일본어와 가까워져요.", "오프라인 학습 기록은 이 PC에만 안전하게 저장됩니다.")
    _, correct, wrong, due = app.db.stats()
    total = correct + wrong
    rate = round(correct * 100 / total) if total else 0
    goal, today, streak = app.db.get("daily_goal", 20), app.db.today_answers(), app.db.streak()
    hero = app.card(main); hero.pack(fill="x")
    left = tk.Frame(hero, bg="white"); left.pack(side="left", fill="both", expand=True, padx=28, pady=24)
    tk.Label(left, text="현재 과정", font=("맑은 고딕", 10), fg="#718078", bg="white").pack(anchor="w")
    tk.Label(left, text=app.selected_level, font=("맑은 고딕", 30, "bold"), fg="#165b52", bg="white").pack(anchor="w")
    tk.Label(left, text=f"연속 학습 {streak}일 · 정답률 {rate}% · 오늘 복습 {due}개", font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", pady=(3, 0))
    tk.Label(left, text=app.study_recommendation(), font=("맑은 고딕", 10), fg="#a2543e", bg="white", wraplength=620, justify="left").pack(anchor="w", pady=(9, 0))
    hero_actions = tk.Frame(hero, bg="white"); hero_actions.pack(side="right", padx=28, pady=28)
    ttk.Button(hero_actions, text="오늘의 코스 시작", style="Accent.TButton", command=app.show_learning).pack(fill="x")
    if due:
        limit = normalized_review_limit(app.db.get("review_limit", DEFAULT_REVIEW_LIMIT))
        ttk.Button(hero_actions, text=f"오늘 복습 먼저 · 최대 {limit}개", command=app.start_review_session).pack(fill="x", pady=(7, 0))
    recommended = error_cause_recommendation(app.db.error_cause_results())
    if recommended:
        ttk.Button(hero_actions, text=f"{recommended[1]} 집중 연습", command=app.start_recommended_practice).pack(fill="x", pady=(7, 0))
    reminder = daily_reminder(goal, today, due, streak, app.db.get("daily_reminder_dismissed") == date.today().isoformat())
    if reminder:
        reminder_card = tk.Frame(main, bg="#fff4dc", highlightbackground="#efd49c", highlightthickness=1); reminder_card.pack(fill="x", pady=(16, 0))
        title, message, action_label = reminder
        tk.Label(reminder_card, text=title, font=("맑은 고딕", 12, "bold"), fg="#9b5a20", bg="#fff4dc").pack(anchor="w", padx=18, pady=(12, 2))
        tk.Label(reminder_card, text=message, font=("맑은 고딕", 10), fg="#795b3b", bg="#fff4dc", wraplength=760, justify="left").pack(anchor="w", padx=18)
        controls = tk.Frame(reminder_card, bg="#fff4dc"); controls.pack(anchor="e", padx=14, pady=(4, 12))
        ttk.Button(controls, text=action_label, style="Accent.TButton", command=app.start_review_session if due else app.show_learning).pack(side="left", padx=4)
        ttk.Button(controls, text="오늘은 숨기기", command=lambda: (app.db.set("daily_reminder_dismissed", date.today().isoformat()), app.show_home())).pack(side="left", padx=4)
    goal_card = app.card(main); goal_card.pack(fill="x", pady=(16, 0))
    goal_top = tk.Frame(goal_card, bg="white"); goal_top.pack(fill="x", padx=18, pady=(14, 5))
    tk.Label(goal_top, text="오늘의 목표", font=("맑은 고딕", 12, "bold"), fg="#173c35", bg="white").pack(side="left")
    tk.Label(goal_top, text=f"{today} / {goal}문항", font=("맑은 고딕", 11, "bold"), fg="#df7654", bg="white").pack(side="right")
    ttk.Progressbar(goal_card, maximum=goal, value=min(today, goal)).pack(fill="x", padx=18, pady=(0, 7))
    actions = tk.Frame(goal_card, bg="white"); actions.pack(anchor="e", padx=18, pady=(0, 12))
    app.voice_status = tk.Label(actions, text="ずんだもん AI 서버를 확인하고 있어요...", font=("맑은 고딕", 9), fg="#66776f", bg="white"); app.voice_status.pack(side="left", padx=(0, 10))
    for label, action in (("화면 크기", app.show_display_settings), ("색상 대비", app.show_theme_settings), ("AI 음성 설정", app.show_voice_settings), ("AI 음성 확인/시작", lambda: app.show_voice_settings(start=True)), ("목표 바꾸기", app.change_daily_goal)):
        ttk.Button(actions, text=label, command=action).pack(side="left", padx=4)
    tk.Label(main, text="빠른 시작", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(30, 12))
    quick = tk.Frame(main, bg="#f4f6f0"); quick.pack(fill="x")
    limit = normalized_review_limit(app.db.get("review_limit", DEFAULT_REVIEW_LIMIT))
    for index, (title, detail, action) in enumerate((("오늘의 복습", f"예정 {due}개 · 한 번에 최대 {limit}개", app.start_review_session), ("오답 노트", "자주 틀린 항목 다시 보기", app.show_wrong_notebook), ("나의 단어장", "내 단어 등록 · 복습 · 퀴즈", app.show_personal_words), ("즐겨찾기", "저장 카드 모아 보기와 퀴즈", app.show_favorites_library), ("학습 계획", "목표와 하루 분량 설정", app.show_study_plan), ("모의고사", "시간 제한 · 영역별 분석", app.start_mock_exam), ("과정 선택", "내 목표 직접 설정", app.show_level_select))):
        item = app.card(quick); item.grid(row=index // 3, column=index % 3, sticky="nsew", padx=(0, 9), pady=2); quick.columnconfigure(index % 3, weight=1)
        tk.Label(item, text=title, font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=16, pady=(17, 4))
        tk.Label(item, text=detail, font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=16)
        ttk.Button(item, text="열기", command=action).pack(anchor="w", padx=16, pady=15)


def render_learning(app):
    """Render the daily learning menu while quiz and course actions stay on the app."""
    day = app.course_day()
    plan = app.study_plan()
    course_level = plan["level"] if app.selected_level in CONTENT else app.selected_level
    main = app.page("학습", "오늘의 학습", f"{course_level} 과정 · Day {day:03d} · 25~35분 권장")
    if app.selected_level in ("초보", "문자"):
        lessons = (
            ("히라가나", "기본 46자, 탁음과 요음", lambda: app.show_kana("hiragana")),
            ("가타카나", "외래어와 이름을 읽는 문자", lambda: app.show_kana("katakana")),
            ("문자 종합 퀴즈", "배운 문자를 바로 확인", lambda: app.start_quiz(mode="kana")),
            ("문자 규칙", "촉음, 장음, 요음 핵심 정리", app.show_kana_notes),
        )
    else:
        reading_pool = app.question_pool("reading")
        listening_pool = app.question_pool("listening")
        completed = app.db.completed_practice_ids()
        reading_done, reading_total = practice_progress_summary([item[3] for item in reading_pool], completed)
        listening_done, listening_total = practice_progress_summary([item[3] for item in listening_pool], completed)
        progress = app.db.course_card_progress(course_level)
        lessons = (
            ("오늘의 새 단어", "학습 계획에 맞춘 오늘 분량", app.show_daily_words),
            ("오늘의 문법", "Day 순서에 맞춘 핵심 문법", app.show_daily_grammar),
            ("나의 단어장", f"직접 등록한 표현 {len(app.db.personal_words())}개", app.show_personal_words),
            ("단어", f"학습 전 {progress['words'][0]} · 학습 중 {progress['words'][1]} · 안정 {progress['words'][2]}", lambda: app.show_catalog("words", content_level=course_level)),
            ("한자", f"학습 전 {progress['kanji'][0]} · 학습 중 {progress['kanji'][1]} · 안정 {progress['kanji'][2]}", lambda: app.show_catalog("kanji", content_level=course_level)),
            ("문법", f"학습 전 {progress['grammar'][0]} · 학습 중 {progress['grammar'][1]} · 안정 {progress['grammar'][2]}", lambda: app.show_catalog("grammar", content_level=course_level)),
            ("문장 만들기", "단어 조각을 올바른 순서로 배열", app.show_sentence_building),
            ("받아쓰기", "듣고 일본어를 직접 입력", app.show_dictation),
            ("독해", f"짧은 지문으로 핵심 찾기 · 완료 {reading_done}/{reading_total}", lambda: app.start_practice_quiz("reading", reading_pool)),
            ("청해 연습", f"ずんだもん AI 음성으로 대화 듣기 · 완료 {listening_done}/{listening_total}", lambda: app.start_practice_quiz("listening", listening_pool)),
            ("한자 쓰기", "직접 써 보며 형태 익히기", app.show_kanji_writing),
            ("종합 모의고사", "시간 제한 · 어휘 · 문법 · 독해 · 청해", app.start_mock_exam),
        )
    for title, detail, command in lessons:
        row = app.card(main); row.pack(fill="x", pady=5)
        tk.Label(row, text=title, width=12, font=("맑은 고딕", 12, "bold"), fg="#df7654", bg="white").pack(side="left", padx=16, pady=17)
        tk.Label(row, text=detail, font=("맑은 고딕", 11), fg="#173c35", bg="white").pack(side="left")
        ttk.Button(row, text="학습", command=command).pack(side="right", padx=16)
    ttk.Button(main, text="오늘 학습 완료 표시", style="Accent.TButton", command=app.complete_lesson).pack(anchor="e", pady=22)


def render_level_select(app, levels):
    """Render course selection while persisting the selection through app callbacks."""
    main = app.page("홈", "어디서 시작할까요?", "직접 과정을 고르거나 12문항 진단으로 추천받으세요.")
    grid = tk.Frame(main, bg="#f4f6f0"); grid.pack(fill="both", expand=True)
    for index, (name, subtitle, description, group) in enumerate(levels):
        item = app.card(grid); item.grid(row=index // 3, column=index % 3, sticky="nsew", padx=6, pady=6); grid.columnconfigure(index % 3, weight=1)
        tk.Label(item, text=name, font=("맑은 고딕", 20, "bold"), fg="#df7654" if group == "기초" else "#165b52", bg="white").pack(anchor="w", padx=18, pady=(15, 1))
        tk.Label(item, text=subtitle, font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=18)
        tk.Label(item, text=description, wraplength=210, justify="left", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=18, pady=(7, 10))
        ttk.Button(item, text="이 과정 선택", command=lambda value=name: app.select_level(value)).pack(anchor="w", padx=18, pady=(0, 15))
    ttk.Button(main, text="12문항 실력 진단 시작", style="Accent.TButton", command=app.start_diagnostic).pack(anchor="e", pady=18)


def render_kana_menu(app):
    """Render the character-study menu while practice actions stay on the app."""
    main = app.page("학습", "기초 문자", "두 문자를 분리해 익힌 뒤 종합 퀴즈로 확인하세요.")
    choices = (
        ("히라가나", "기본 46자 + 탁음 · 반탁음 · 요음", lambda: app.show_kana("hiragana"), "#df7654"),
        ("가타카나", "기본 46자 + 탁음 · 반탁음 · 요음", lambda: app.show_kana("katakana"), "#165b52"),
    )
    for title, detail, command, color in choices:
        item = app.card(main); item.pack(fill="x", pady=7)
        tk.Label(item, text=title, font=("맑은 고딕", 22, "bold"), fg=color, bg="white").pack(anchor="w", padx=24, pady=(20, 3))
        tk.Label(item, text=detail, font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", padx=24)
        ttk.Button(item, text="학습 시작", style="Accent.TButton", command=command).pack(anchor="e", padx=24, pady=(0, 18))


def render_kana_notes(app, notes):
    """Render reading-rule reference cards without owning character practice state."""
    main = app.page("학습", "문자 읽기 규칙", "문자를 조합해 자연스럽게 읽기 위한 네 가지 핵심입니다.")
    for symbol, title, text in notes:
        item = app.card(main); item.pack(fill="x", pady=5)
        tk.Label(item, text=symbol, font=("맑은 고딕", 20, "bold"), fg="#df7654", bg="white", width=14).pack(side="left", padx=15, pady=15)
        block = tk.Frame(item, bg="white"); block.pack(side="left", fill="x", expand=True, pady=12)
        tk.Label(block, text=title, font=("맑은 고딕", 12, "bold"), fg="#173c35", bg="white").pack(anchor="w")
        tk.Label(block, text=text, font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(anchor="w")


def render_study_plan(app):
    """Render course pace and progress; plan settings remain an application dialog callback."""
    plan = app.study_plan()
    level, days, daily_words = plan["level"], plan["days"], plan["daily_words"]
    word_count = len(CONTENT.get(level, CONTENT["N5"])["words"])
    target_days = max(days, (word_count + daily_words - 1) // daily_words)
    course_day = app.course_day()
    _, words, grammar = daily_course_items(plan, course_day)
    progress = app.db.course_card_progress(level)
    new_cards, active_cards, stable_cards, insight = course_progress_insight(progress)
    main = app.page("학습", "학습 계획", "목표 과정과 기간을 기준으로 오늘의 새 단어와 복습량을 안내합니다.")
    card = app.card(main); card.pack(fill="x")
    tk.Label(card, text=f"목표: {level} · 계획 기간: {days}일", font=("맑은 고딕", 18, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=22, pady=(20, 5))
    tk.Label(card, text=f"하루 새 단어 {daily_words}개 · 전체 {word_count}개 · 권장 최소 {target_days}일", font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", padx=22)
    tk.Label(card, text=f"오늘 Day {course_day:03d}: 새 단어 {len(words)}개 + 문법 1개 + 복습 {app.db.stats()[3]}개", font=("맑은 고딕", 13, "bold"), fg="#a2543e", bg="white").pack(anchor="w", padx=22, pady=(12, 4))
    tk.Label(card, text=f"오늘 문법: {grammar[0]} · 단어: {', '.join(item[0] for item in words)}", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=760, justify="left").pack(anchor="w", padx=22, pady=(0, 20))
    progress_card = app.card(main); progress_card.pack(fill="x", pady=(0, 12))
    tk.Label(progress_card, text="카드 학습 진도", font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=22, pady=(15, 3))
    tk.Label(progress_card, text=f"학습 전 {new_cards} · 학습 중 {active_cards} · 안정적 암기 {stable_cards}", font=("맑은 고딕", 11, "bold"), fg="#a2543e", bg="white").pack(anchor="w", padx=22)
    tk.Label(progress_card, text=insight, font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=760, justify="left").pack(anchor="w", padx=22, pady=(4, 10))
    for category, label in (("words", "단어"), ("kanji", "한자"), ("grammar", "문법")):
        new, active, stable = progress[category]
        total = new + active + stable
        row = tk.Frame(progress_card, bg="white"); row.pack(fill="x", padx=22, pady=2)
        tk.Label(row, text=label, width=5, font=("맑은 고딕", 10, "bold"), fg="#165b52", bg="white").pack(side="left")
        ttk.Progressbar(row, maximum=max(1, total), value=stable).pack(side="left", fill="x", expand=True, padx=8)
        tk.Label(row, text=f"안정 {stable}/{total}", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(side="right")
    total_cards = sum(sum(values) for values in progress.values())
    planned_cards, remaining_days, _, pace = study_plan_pace(plan, course_day, total_cards, stable_cards)
    tk.Label(progress_card, text=f"계획 페이스 · Day {course_day}/{days} · 계획상 카드 {planned_cards}/{total_cards} · 남은 {remaining_days}일", font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=22, pady=(10, 2))
    tk.Label(progress_card, text=pace, font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=760, justify="left").pack(anchor="w", padx=22, pady=(0, 10))
    actions = tk.Frame(progress_card, bg="white"); actions.pack(anchor="e", padx=18, pady=(0, 14))
    for category, label in (("words", "새 단어"), ("kanji", "새 한자"), ("grammar", "새 문법")):
        if progress[category][0]:
            ttk.Button(actions, text=f"{label} 시작", command=lambda value=category: app.start_catalog_state_quiz(value, level, "학습 전")).pack(side="left", padx=4)
    for category, label in (("words", "단어 복습"), ("kanji", "한자 복습"), ("grammar", "문법 복습")):
        if progress[category][1]:
            ttk.Button(actions, text=label, command=lambda value=category: app.start_catalog_state_quiz(value, level, "학습 중")).pack(side="left", padx=4)
    for category, label in (("words", "안정 단어"), ("kanji", "안정 한자"), ("grammar", "안정 문법")):
        if not progress[category][0] and not progress[category][1] and progress[category][2]:
            ttk.Button(actions, text=label, command=lambda value=category: app.start_catalog_state_quiz(value, level, "안정적 암기")).pack(side="left", padx=4)
    ttk.Button(main, text="계획 설정", style="Accent.TButton", command=app.edit_study_plan).pack(anchor="e", pady=18)


def render_personal_words(app):
    """Render the personal-word library while persistence actions stay on the app database."""
    main = app.page("학습", "나의 단어장", "직접 등록한 표현도 기존 단어처럼 간격 복습과 퀴즈로 익힐 수 있어요.")
    words = app.db.personal_words()
    summary = app.card(main); summary.pack(fill="x", pady=(0, 14))
    tk.Label(summary, text=f"등록한 표현 {len(words)}개", font=("맑은 고딕", 15, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=18, pady=(14, 3))
    tk.Label(summary, text="일본어, 읽기, 뜻은 필수입니다. 예문이나 암기 힌트는 선택 사항이에요.", font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(anchor="w", padx=18)

    def open_editor(saved=None):
        dialog = tk.Toplevel(app); dialog.title("나의 단어 편집" if saved else "나의 단어 추가"); dialog.configure(bg="white")
        dialog.transient(app); dialog.grab_set(); dialog.resizable(False, False)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        fields = (("일본어", "word"), ("읽기", "reading"), ("뜻", "meaning"), ("예문 또는 암기 힌트 (선택)", "example"))
        values = {}
        for label, key in fields:
            tk.Label(dialog, text=label, font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=26, pady=(16 if key == "word" else 8, 3))
            value = tk.StringVar(value=(saved[{"word": 1, "reading": 2, "meaning": 3, "example": 4}[key]] if saved else ""))
            ttk.Entry(dialog, textvariable=value, width=48, font=("맑은 고딕", 11)).pack(padx=26)
            values[key] = value
        status = tk.Label(dialog, text="", font=("맑은 고딕", 9), fg="#b95140", bg="white"); status.pack(anchor="w", padx=26, pady=(8, 0))

        def save():
            try:
                app.db.save_personal_word(*(values[key].get() for key in ("word", "reading", "meaning", "example")), word_id=saved[0] if saved else None)
            except (ValueError, sqlite3.IntegrityError) as error:
                status.config(text=str(error)); return
            dialog.destroy(); app.show_personal_words()

        ttk.Button(dialog, text="저장", style="Accent.TButton", command=save).pack(anchor="e", padx=26, pady=22)

    def import_words():
        source = filedialog.askopenfilename(parent=app, title="나의 단어장 CSV 가져오기", initialdir=DATA_DIR, filetypes=(("CSV 파일", "*.csv"), ("모든 파일", "*.*")))
        if not source:
            return
        try:
            with open(source, encoding="utf-8-sig", newline="") as input_file:
                rows = personal_word_import_rows(input_file.read())
            if not rows:
                raise ValueError("가져올 단어가 없습니다.")
            inserted, updated = app.db.import_personal_words(rows)
        except (OSError, UnicodeError, ValueError, csv.Error, sqlite3.Error) as error:
            messagebox.showerror("가져오기 실패", f"단어장 CSV를 읽지 못했어요.\n{error}", parent=app)
            return
        messagebox.showinfo("가져오기 완료", f"새 표현 {inserted}개를 추가했고, 같은 일본어·읽기 표현 {updated}개를 갱신했어요.", parent=app)
        app.show_personal_words()

    def delete_word(word_id):
        if messagebox.askyesno("내 단어 삭제", "이 표현과 연결된 복습 기록도 삭제합니다. 계속할까요?", parent=app):
            app.db.delete_personal_word(word_id); app.show_personal_words()

    controls = tk.Frame(summary, bg="white"); controls.pack(anchor="e", padx=18, pady=(5, 14))
    ttk.Button(controls, text="표현 추가", command=open_editor).pack(side="left", padx=4)
    if words:
        ttk.Button(controls, text="내 단어 퀴즈", style="Accent.TButton", command=lambda: app.start_quiz(mode="personal-words")).pack(side="left", padx=4)
    ttk.Button(controls, text="CSV 가져오기", command=import_words).pack(side="left", padx=4)
    if not words:
        tk.Label(main, text="여행, 드라마, 업무에서 만난 표현을 등록해 나만의 복습 카드로 만들어 보세요.", font=("맑은 고딕", 12), fg="#66776f", bg="#f4f6f0", wraplength=720, justify="left").pack(pady=45)
        return
    for saved in words:
        word_id, word, reading, meaning, example, _ = saved
        row = app.card(main); row.pack(fill="x", pady=4)
        text = tk.Frame(row, bg="white"); text.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        tk.Label(text, text=word, font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w")
        tk.Label(text, text=f"{reading} · {meaning}", font=("맑은 고딕", 10), fg="#165b52", bg="white").pack(anchor="w")
        if example:
            tk.Label(text, text=example, font=("맑은 고딕", 9), fg="#718078", bg="white", wraplength=600, justify="left").pack(anchor="w", pady=(3, 0))
        actions = tk.Frame(row, bg="white"); actions.pack(side="right", padx=14)
        ttk.Button(actions, text="발음", command=lambda value=word: app.speak_japanese(value)).pack(side="left", padx=3)
        ttk.Button(actions, text="편집", command=lambda value=saved: open_editor(value)).pack(side="left", padx=3)
        ttk.Button(actions, text="삭제", command=lambda value=word_id: delete_word(value)).pack(side="left", padx=3)


def render_favorites_library(app):
    """Render favorite cards while the app retains navigation and quiz callbacks."""
    main = app.page("학습", "즐겨찾기", "과정을 바꾼 뒤에도 저장한 단어, 한자, 문법 카드를 한곳에서 다시 볼 수 있어요.")
    cards = app.db.favorite_cards()
    if not cards:
        tk.Label(main, text="아직 저장한 카드가 없어요. 단어·한자·문법 카드에서 즐겨찾기를 추가해 보세요.", font=("맑은 고딕", 12), fg="#66776f", bg="#f4f6f0", wraplength=720, justify="left").pack(pady=55)
        return
    summary = app.card(main); summary.pack(fill="x", pady=(0, 14))
    tk.Label(summary, text=f"저장한 카드 {len(cards)}개", font=("맑은 고딕", 15, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=18, pady=(14, 3))
    levels = ", ".join(sorted({level for _, level, _, _, _, _ in cards}, key=lambda value: LEVEL_ORDER.index(value)))
    tk.Label(summary, text=f"포함 과정: {levels} · 현재 과정과 관계없이 퀴즈에 출제됩니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(anchor="w", padx=18)
    ttk.Button(summary, text="저장 카드 퀴즈", style="Accent.TButton", command=lambda: app.start_quiz(mode="favorites")).pack(anchor="e", padx=18, pady=(4, 13))

    def remove_favorite(content_id):
        app.db.toggle_favorite(content_id)
        app.show_favorites_library()

    for content_id, level, category, title, detail, example in cards:
        row = app.card(main); row.pack(fill="x", pady=4)
        text = tk.Frame(row, bg="white"); text.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        tk.Label(text, text=f"{level} · {QUIZ_MODE_LABELS.get(category, category)}", font=("맑은 고딕", 9, "bold"), fg="#a2543e", bg="white").pack(anchor="w")
        tk.Label(text, text=title, font=("맑은 고딕", 13, "bold"), fg="#173c35", bg="white").pack(anchor="w", pady=(2, 0))
        tk.Label(text, text=detail, font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(anchor="w")
        tk.Label(text, text=example, font=("맑은 고딕", 9), fg="#718078", bg="white", wraplength=660, justify="left").pack(anchor="w", pady=(3, 0))
        ttk.Button(row, text="해제", command=lambda identifier=content_id: remove_favorite(identifier)).pack(side="right", padx=16)


def render_review(app):
    """Render due and upcoming SRS work; quiz actions remain application callbacks."""
    main = app.page("복습", "간격 복습", "틀린 문제와 오늘 예정된 문제를 다시 풀어 기억을 오래 유지하세요.")
    limit = normalized_review_limit(app.db.get("review_limit", DEFAULT_REVIEW_LIMIT))
    rows = app.db.due_items(limit)
    _, _, _, due = app.db.stats()
    tk.Label(main, text=f"오늘 복습할 항목 {due}개", font=("맑은 고딕", 16, "bold"), fg="#165b52", bg="#f4f6f0").pack(anchor="w", pady=(0, 12))
    forecast = app.db.review_forecast()
    _, upcoming_total, _, message = review_workload_insight(forecast)
    forecast_card = app.card(main); forecast_card.pack(fill="x", pady=(0, 16))
    tk.Label(forecast_card, text="7일 복습 계획", font=("맑은 고딕", 12, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=16, pady=(14, 3))
    tk.Label(forecast_card, text=message, font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=820, justify="left").pack(anchor="w", padx=16)
    schedule = tk.Frame(forecast_card, bg="white"); schedule.pack(fill="x", padx=16, pady=(12, 14))
    for index, (due_date, count) in enumerate(forecast):
        current = date.fromisoformat(due_date)
        label = "오늘" if index == 0 else "내일" if index == 1 else current.strftime("%m/%d")
        day = tk.Frame(schedule, bg="#f0f5f1" if count else "#f7f8f5"); day.grid(row=0, column=index, sticky="nsew", padx=2)
        schedule.columnconfigure(index, weight=1)
        tk.Label(day, text=label, font=("맑은 고딕", 9, "bold"), fg="#165b52", bg=day.cget("bg")).pack(pady=(7, 0))
        tk.Label(day, text=f"{count}개", font=("맑은 고딕", 13, "bold"), fg="#df7654" if count else "#718078", bg=day.cget("bg")).pack(pady=(0, 7))
    if upcoming_total:
        tk.Label(forecast_card, text=f"오늘 이후 예정 복습 합계 {upcoming_total}개", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="e", padx=16, pady=(0, 10))
    if not rows:
        tk.Label(main, text="오늘 예정된 복습이 없어요. 다음 일정도 확인해 보세요.", font=("맑은 고딕", 12), fg="#66776f", bg="#f4f6f0").pack(pady=(30, 18))
    for content_id, correct, wrong, _, step in rows:
        row = app.card(main); row.pack(fill="x", pady=3)
        tk.Label(row, text=app.readable_content_id(content_id), font=("맑은 고딕", 11, "bold"), fg="#173c35", bg="white").pack(side="left", padx=15, pady=13)
        tk.Label(row, text=f"오늘 복습 · {SRS_DAYS[step]}일 간격 · 정답 {correct} · 오답 {wrong}", font=("맑은 고딕", 9), fg="#b95140", bg="white").pack(side="right", padx=15)
    if rows:
        shown = min(len(rows), limit)
        tk.Label(main, text=f"한 번에 최대 {limit}개씩 진행합니다. 이번 세션 {shown}개", font=("맑은 고딕", 10), fg="#718078", bg="#f4f6f0").pack(anchor="e", pady=(8, 0))
        ttk.Button(main, text=f"복습 시작 · {shown}개", style="Accent.TButton", command=app.start_review_session).pack(anchor="e", pady=(4, 18))
    upcoming = app.db.upcoming_items()
    if upcoming:
        tk.Label(main, text="다음 복습 일정", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(20, 8))
        tk.Label(main, text="미리 확인만 할 수 있으며, 예정일이 되면 복습 목록에 자동으로 나타납니다.", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(0, 6))
    for content_id, _, _, due_date, step in upcoming:
        row = app.card(main); row.pack(fill="x", pady=3)
        days_until = (date.fromisoformat(due_date) - date.today()).days
        timing = "내일" if days_until == 1 else f"{days_until}일 뒤"
        tk.Label(row, text=app.readable_content_id(content_id), font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(side="left", padx=15, pady=11)
        tk.Label(row, text=f"{timing} · {due_date} · {SRS_DAYS[step]}일 간격", font=("맑은 고딕", 9), fg="#66776f", bg="white").pack(side="right", padx=15)


def render_stats(app):
    """Render the statistics overview and delegate detailed rows to the app callbacks."""
    main = app.page("통계", "학습 통계", "숫자는 이 기기의 오프라인 학습 기록만으로 계산됩니다.")
    days, correct, wrong, due = app.db.stats()
    total = correct + wrong
    rate = round(correct * 100 / total) if total else 0
    grid = tk.Frame(main, bg="#f4f6f0"); grid.pack(fill="x")
    for index, (label, value) in enumerate((("학습한 날", f"{days}일"), ("연속 학습", f"{app.db.streak()}일"), ("푼 문제", f"{total}개"), ("정답률", f"{rate}%"), ("복습 대기", f"{due}개"))):
        item = app.card(grid); item.grid(row=0, column=index, sticky="nsew", padx=(0, 7)); grid.columnconfigure(index, weight=1)
        tk.Label(item, text=label, font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=13, pady=(14, 3))
        tk.Label(item, text=value, font=("맑은 고딕", 21, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=13, pady=(0, 14))
    activity = app.db.weekly_activity()
    active_days, weekly_answers, best_answers = weekly_activity_summary(activity)
    tk.Label(main, text="최근 7일 학습 리듬", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(30, 8))
    tk.Label(main, text=f"이번 주 {active_days}일 학습 · {weekly_answers}문항 풀이 · 하루 최다 {best_answers}문항", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(0, 8))
    rhythm = app.card(main); rhythm.pack(fill="x")
    for index, (day_text, completed, answers) in enumerate(activity):
        day = date.fromisoformat(day_text)
        column = tk.Frame(rhythm, bg="white"); column.grid(row=0, column=index, sticky="nsew", padx=3, pady=14); rhythm.columnconfigure(index, weight=1)
        tk.Label(column, text="오늘" if day == date.today() else f"{day.month}/{day.day}", font=("맑은 고딕", 9, "bold"), fg="#165b52" if completed else "#9aa6a0", bg="white").pack()
        tk.Label(column, text=f"{answers}문항" if answers else "휴식", font=("맑은 고딕", 11, "bold"), fg="#df7654" if answers else "#8a9790", bg="white").pack(pady=(5, 2))
    tk.Label(main, text="학습 이정표", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(26, 8))
    milestones = tk.Frame(main, bg="#f4f6f0"); milestones.pack(fill="x")
    for index, (title, requirement, achieved) in enumerate(achievement_milestones(days, total, app.db.streak())):
        item = app.card(milestones); item.grid(row=index // 3, column=index % 3, sticky="nsew", padx=(0, 7), pady=3); milestones.columnconfigure(index % 3, weight=1)
        tk.Label(item, text="달성" if achieved else "진행 중", font=("맑은 고딕", 9, "bold"), fg="#165b52" if achieved else "#a2543e", bg="white").pack(anchor="w", padx=13, pady=(12, 2))
        tk.Label(item, text=title, font=("맑은 고딕", 12, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=13)
        tk.Label(item, text=requirement, font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=13, pady=(3, 12))
    _render_stats_insights(app, main)


def _render_stats_insights(app, main):
    recent = app.db.recent_quiz_results()
    trend = quiz_trend_insight(recent)
    if trend:
        accuracy, change, message = trend
        card = app.card(main); card.pack(fill="x", pady=(26, 0))
        tk.Label(card, text="최근 퀴즈 흐름", font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=18, pady=(15, 3))
        detail = f"최근 {len(recent)}회 정확도 {accuracy}%" + (f" · 변화 {change:+d}%p" if change is not None else "")
        tk.Label(card, text=detail, font=("맑은 고딕", 11, "bold"), fg="#df7654", bg="white").pack(anchor="w", padx=18)
        tk.Label(card, text=message, font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=800, justify="left").pack(anchor="w", padx=18, pady=(4, 15))
    causes = error_cause_summary(app.db.error_cause_results())
    if causes:
        cause, label, correct, wrong = error_cause_recommendation(app.db.error_cause_results())
        card = app.card(main); card.pack(fill="x", pady=(26, 0))
        total = correct + wrong
        tk.Label(card, text="오답 원인 분석", font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=18, pady=(15, 3))
        tk.Label(card, text=f"가장 먼저 볼 원인: {label} · 오답 {wrong}회 · 정확도 {round(correct * 100 / total)}%", font=("맑은 고딕", 11, "bold"), fg="#a2543e", bg="white").pack(anchor="w", padx=18)
        details = " · ".join(f"{ERROR_CAUSE_LABELS.get(name, name)} {count}회" for name, _, count in causes[:4])
        tk.Label(card, text=f"오답이 쌓인 세부 원인: {details}", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=800, justify="left").pack(anchor="w", padx=18, pady=(4, 3))
        controls = tk.Frame(card, bg="white"); controls.pack(anchor="e", padx=18, pady=(2, 14))
        ttk.Button(controls, text="회복 경로 보기", command=lambda: app.show_error_cause_path(cause, label)).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text=f"{label} 집중 연습", style="Accent.TButton", command=lambda: app.start_error_cause_quiz(cause, label)).pack(side="left")
    render_stats_details(app, main)


def render_stats_details(app, main):
    """Render action-heavy detailed statistics while callbacks remain on the app."""
    history = app.db.quiz_history()
    if history:
        tk.Label(main, text="최근 퀴즈 기록", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(26, 8))
        tk.Label(main, text="가장 최근에 푼 순서로 표시합니다.", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(0, 6))
        for taken_on, mode, level, score, quiz_total in history:
            row = app.card(main); row.pack(fill="x", pady=3)
            rate = round(score * 100 / quiz_total) if quiz_total else 0
            tk.Label(row, text=QUIZ_MODE_LABELS.get(mode, mode), font=("맑은 고딕", 11, "bold"), fg="#173c35", bg="white").pack(side="left", padx=15, pady=12)
            tk.Label(row, text=f"{taken_on} · {level} · {score}/{quiz_total} ({rate}%)", font=("맑은 고딕", 10, "bold"), fg="#165b52" if rate >= 70 else "#a2543e", bg="white").pack(side="right", padx=15)
    tk.Label(main, text="과정별 카드 숙련도", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(28, 8))
    tk.Label(main, text="학습함은 한 번 이상 답한 카드, 안정 기억은 정답이 더 많고 4일 이상 간격으로 복습되는 카드입니다.", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(0, 6))
    for level, reviewed, mastered, available in app.db.level_mastery():
        coverage = round(reviewed * 100 / available) if available else 0
        mastery = round(mastered * 100 / available) if available else 0
        row = app.card(main); row.pack(fill="x", pady=3)
        tk.Label(row, text=level, width=5, font=("맑은 고딕", 11, "bold"), fg="#165b52", bg="white").pack(side="left", padx=(13, 5), pady=12)
        ttk.Progressbar(row, maximum=100, value=mastery).pack(side="left", fill="x", expand=True, padx=8)
        tk.Label(row, text=f"학습 {reviewed}/{available} ({coverage}%) · 안정 {mastered} ({mastery}%)", font=("맑은 고딕", 9, "bold"), fg="#66776f", bg="white").pack(side="right", padx=14)
    tk.Label(main, text="학습 방법", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(32, 8))
    tk.Label(main, text="정답 뒤 기억 난이도를 고르면 1일, 2일, 4일, 7일, 14일, 30일, 60일 간격을 더 빠르거나 느리게 조절합니다. 오답은 바로 복습 목록에 돌아옵니다.", font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0", wraplength=800, justify="left").pack(anchor="w")
    backup = app.card(main); backup.pack(fill="x", pady=(26, 0))
    tk.Label(backup, text="학습 기록 보호", font=("맑은 고딕", 13, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=18, pady=(15, 3))
    tk.Label(backup, text="하루마다 최근 14일치 자동 백업을 남기며, 필요할 때 직접 백업·복원하거나 CSV로 기록을 꺼낼 수 있어요.", font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(anchor="w", padx=18)
    record_actions = tk.Frame(backup, bg="white"); record_actions.pack(anchor="e", padx=18, pady=(4, 14))
    ttk.Button(record_actions, text="CSV 내보내기", command=app.export_learning_record).pack(side="left", padx=(0, 6))
    ttk.Button(record_actions, text="백업 및 복원 관리", command=app.show_backup_restore).pack(side="left")
    _render_category_results(app, main)
    _render_level_results(app, main)
    _render_weaknesses(app, main)


def _render_category_results(app, main):
    results = app.db.category_results()
    if not results:
        return
    tk.Label(main, text="영역별 시험 기록", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(28, 9))
    records = tk.Frame(main, bg="#f4f6f0"); records.pack(fill="x")
    for index, (mode, score, total) in enumerate(results):
        item = app.card(records); item.grid(row=index // 4, column=index % 4, sticky="nsew", padx=4, pady=4)
        records.columnconfigure(index % 4, weight=1)
        tk.Label(item, text=QUIZ_MODE_LABELS.get(mode, mode), font=("맑은 고딕", 10, "bold"), fg="#165b52", bg="white").pack(anchor="w", padx=12, pady=(11, 2))
        tk.Label(item, text=f"{round(score * 100 / total) if total else 0}% · {score}/{total}", font=("맑은 고딕", 11), fg="#66776f", bg="white").pack(anchor="w", padx=12, pady=(0, 11))


def _render_level_results(app, main):
    levels = app.db.level_results()
    if not levels:
        return
    tk.Label(main, text="레벨별 실전 준비도", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(26, 8))
    for level, score, total in levels:
        row = tk.Frame(main, bg="#f4f6f0"); row.pack(fill="x", pady=3)
        rate = round(score * 100 / total) if total else 0
        tk.Label(row, text=level, width=5, font=("맑은 고딕", 11, "bold"), fg="#165b52", bg="#f4f6f0").pack(side="left")
        ttk.Progressbar(row, maximum=100, value=rate).pack(side="left", fill="x", expand=True, padx=10)
        tk.Label(row, text=f"{rate}% ({score}/{total})", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(side="right")


def _render_weaknesses(app, main):
    weaknesses = app.db.weakness_categories()
    if not weaknesses:
        return
    tk.Label(main, text="약점 유형 분석", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w", pady=(26, 8))
    tk.Label(main, text="직접 푼 문제의 유형별 정답률입니다. 낮은 영역부터 다시 연습해 보세요.", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(0, 6))
    for label, correct, wrong in weaknesses:
        total = correct + wrong
        rate = round(correct * 100 / total)
        row = tk.Frame(main, bg="#f4f6f0"); row.pack(fill="x", pady=3)
        tk.Label(row, text=label, width=12, font=("맑은 고딕", 10, "bold"), fg="#165b52", bg="#f4f6f0").pack(side="left")
        ttk.Progressbar(row, maximum=100, value=rate).pack(side="left", fill="x", expand=True, padx=10)
        tk.Label(row, text=f"{rate}% ({correct}/{total})", font=("맑은 고딕", 10), fg="#66776f", bg="#f4f6f0").pack(side="right")
