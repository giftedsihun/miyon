"""Tkinter widgets for an active quiz; session state stays in ``QuizSession``."""

import tkinter as tk
from tkinter import ttk


def build_quiz_screen(app, active, title, subtitle):
    main = app.page(active, title, subtitle)
    app.quiz_progress = ttk.Progressbar(main, maximum=app.quiz_limit)
    app.quiz_progress.pack(fill="x", pady=(0, 16))
    app.quiz_prompt = tk.Label(main, font=("맑은 고딕", 22, "bold"), fg="#165b52", bg="white", wraplength=650, justify="center", height=4)
    app.quiz_prompt.pack(fill="x", pady=6)
    app.quiz_options = tk.Frame(main, bg="#f4f6f0")
    app.quiz_options.pack(fill="x", pady=10)
    app.quiz_feedback = tk.Label(main, font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0", wraplength=650, justify="center")
    app.quiz_feedback.pack(pady=9)
    app.quiz_timer = tk.Label(main, font=("맑은 고딕", 11, "bold"), fg="#a2543e", bg="#f4f6f0")
    if app.quiz_time_limit:
        app.quiz_timer.pack(pady=(0, 6))


def render_question(app, prompt, answer, content_id, options, explanation, study_tip):
    """Render one question and return the listening dialogue, if applicable."""
    for child in app.quiz_options.winfo_children():
        child.destroy()
    listening = ":listening:" in content_id
    dialogue = None
    if listening:
        dialogue, question = prompt.split("\n\n", 1)
        dialogue = dialogue.replace("[청해 연습 · 대화문]\n", "")
        app.quiz_prompt.config(text="[청해 연습]\n먼저 대화를 듣고 질문에 답해 보세요.\n\n" + question)
    else:
        app.quiz_prompt.config(text=prompt)
    app.quiz_feedback.config(text=f"문제 {app.quiz_position + 1} / {app.quiz_limit}", fg="#66776f")
    app.quiz_progress["value"] = app.quiz_position
    offset = 0
    if listening:
        controls = tk.Frame(app.quiz_options, bg="#f4f6f0")
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Button(controls, text="느리게 듣기", command=lambda: app.speak_japanese(dialogue, app.quiz_feedback, -3)).pack(side="left", padx=4)
        ttk.Button(controls, text="보통 속도로 듣기", command=lambda: app.speak_japanese(dialogue, app.quiz_feedback, 0)).pack(side="left", padx=4)
        ttk.Button(controls, text="재생 중지", command=app.stop_speech).pack(side="left", padx=4)
        ttk.Button(controls, text="대본 보기", command=app.reveal_dialogue).pack(side="right", padx=4)
        offset = 1
    if study_tip:
        app.quiz_feedback.config(text=f"문제 {app.quiz_position + 1} / {app.quiz_limit}\n{study_tip}", fg="#66776f")
    for index, option in enumerate(options):
        ttk.Button(app.quiz_options, text=option, command=lambda choice=option: app.check_answer(choice)).grid(
            row=index // 2 + offset, column=index % 2, sticky="ew", padx=5, pady=5,
        )
    app.quiz_options.columnconfigure(0, weight=1)
    app.quiz_options.columnconfigure(1, weight=1)
    return dialogue


def show_quality_controls(app):
    controls = tk.Frame(app.quiz_options, bg="#f4f6f0")
    controls.grid(row=3, column=0, columnspan=2, pady=(10, 0))
    for label, quality, detail in (("어려움", "hard", "내일"), ("보통", "normal", "다음 간격"), ("쉬움", "easy", "더 긴 간격")):
        ttk.Button(controls, text=f"{label} · {detail}", command=lambda value=quality: app.finish_correct_answer(value)).pack(side="left", padx=4)
