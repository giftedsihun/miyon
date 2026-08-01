"""Interactive practice renderers: kana/kanji writing, sentence building, dictation.

Widgets and per-screen state stay here; persistence and navigation side effects
are delegated to application callbacks (``app.db``, ``app.page``, ``app.speak_japanese``).
"""

import random
import tkinter as tk
from tkinter import messagebox, ttk

from content import (CONTENT, HIRAGANA, HIRAGANA_EXTRA, KATAKANA, KATAKANA_EXTRA,
                     SENTENCE_BUILDING, WRITING_GUIDES)


def make_writing_canvas(parent, expected_strokes=0):
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


def render_kana_writing(app, script):
    hira = script == "hiragana"; title = "히라가나" if hira else "가타카나"
    chars = HIRAGANA + HIRAGANA_EXTRA if hira else KATAKANA + KATAKANA_EXTRA
    app.kana_writing_index = 0
    main = app.page("학습", f"{title} 쓰기 연습", "견본을 보고 빈 칸에 따라 써 보세요. 입력한 글자는 모양 인식 없이 일치 여부만 확인합니다.")
    card = app.card(main); card.pack(fill="both", expand=True)
    target = tk.Label(card, font=("Yu Gothic", 96, "bold"), fg="#df7654" if hira else "#165b52", bg="white"); target.pack(pady=(26, 0))
    reading = tk.Label(card, font=("맑은 고딕", 18, "bold"), fg="#173c35", bg="white"); reading.pack()
    guide = tk.Label(card, text="1. 견본을 천천히 관찰합니다.  2. 아래 칸에 같은 글자를 입력하거나 손으로 써 봅니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white"); guide.pack(pady=(8, 12))
    entry = ttk.Entry(card, justify="center", font=("Yu Gothic", 35), width=8); entry.pack(pady=10)
    feedback = tk.Label(card, font=("맑은 고딕", 11), fg="#66776f", bg="white"); feedback.pack(pady=(0, 8))
    canvas, stroke_count, clear_canvas = make_writing_canvas(card)
    tk.Label(card, text="마우스나 터치로 직접 그려 보세요. 획 수는 연습 기록용이며 글자 모양을 채점하지 않습니다.", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(pady=(7, 0))
    def render():
        char, sound = chars[app.kana_writing_index]
        target.config(text=char); reading.config(text=f"발음: {sound}"); entry.delete(0, "end"); clear_canvas(); feedback.config(text="견본을 보고 천천히 한 번 써 보세요.", fg="#66776f"); entry.focus_set()
    def check():
        char, _ = chars[app.kana_writing_index]
        if entry.get().strip() == char:
            app.db.record_answer(f"kana:{char}", True); feedback.config(text="맞게 입력했어요. 손으로도 세 번 더 써 보세요.", fg="#165b52")
        else:
            app.db.record_answer(f"kana:{char}", False); feedback.config(text=f"견본은 「{char}」입니다. 다시 보고 써 보세요.", fg="#b95140")
    controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
    ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
    ttk.Button(controls, text="입력 확인", command=check).pack(side="left", padx=4)
    ttk.Button(controls, text="그림 지우기", command=clear_canvas).pack(side="left", padx=4)
    ttk.Button(controls, text="다음", style="Accent.TButton", command=lambda: move(1)).pack(side="left", padx=4)
    def move(step): app.kana_writing_index = (app.kana_writing_index + step) % len(chars); render()
    render()


def render_kanji_writing(app):
    if app.selected_level not in CONTENT:
        app.select_level("N5"); return
    data = app.current_content()["kanji"]; app.writing_index = 0
    main = app.page("학습", "한자 쓰기 연습", "참고 획순과 견본을 보고 빈 칸에 직접 써 보세요. 입력 확인은 글자 일치만 검사하며 필체 인식은 하지 않습니다.")
    card = app.card(main); card.pack(fill="both", expand=True)
    target = tk.Label(card, font=("맑은 고딕", 84, "bold"), fg="#165b52", bg="white"); target.pack(pady=(28, 0))
    info = tk.Label(card, font=("맑은 고딕", 15), fg="#173c35", bg="white"); info.pack(pady=4)
    practice = tk.Text(card, height=7, font=("Yu Gothic", 28), relief="solid", borderwidth=1, padx=16, pady=12)
    practice.pack(fill="x", padx=70, pady=16)
    hint = tk.Label(card, font=("맑은 고딕", 10), fg="#66776f", bg="white"); hint.pack()
    strokes = tk.Label(card, font=("맑은 고딕", 10), fg="#a2543e", bg="white", wraplength=760, justify="center"); strokes.pack(pady=(8, 0))
    answer = ttk.Entry(card, justify="center", font=("Yu Gothic", 24), width=7); answer.pack(pady=(8, 0))
    feedback = tk.Label(card, font=("맑은 고딕", 10), fg="#66776f", bg="white"); feedback.pack(pady=(5, 0))
    canvas, stroke_count, clear_canvas = make_writing_canvas(card, len(WRITING_GUIDES.get(data[0][0], ())))
    tk.Label(card, text="마우스나 터치로 큰 칸에 직접 써 보세요. 획 수는 연습 기록이며 자동 필체 채점은 하지 않습니다.", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(pady=(7, 0))
    def render():
        char, reading, meaning, example = data[app.writing_index]
        guide_steps = WRITING_GUIDES.get(char, [])
        target.config(text=char); info.config(text=f"읽기: {reading} · 뜻: {meaning}"); hint.config(text=f"핵심 어휘: {example} · 큰 칸에 {char}를 직접 써 보세요."); strokes.config(text="참고 획순: " + "  →  ".join(guide_steps or ["이 글자는 참고 획순 안내가 준비 중입니다."])); practice.delete("1.0", "end"); answer.delete(0, "end"); clear_canvas(len(guide_steps)); feedback.config(text="")
    def check():
        char = data[app.writing_index][0]
        if answer.get().strip() == char:
            app.db.record_answer(f"{app.selected_level}:kanji:{char}", True); feedback.config(text="맞게 입력했어요. 큰 칸에서도 같은 글자를 반복해 보세요.", fg="#165b52")
        else:
            app.db.record_answer(f"{app.selected_level}:kanji:{char}", False); feedback.config(text=f"입력 견본은 「{char}」입니다. 위 참고 순서를 보며 다시 써 보세요.", fg="#b95140")
    controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
    ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
    ttk.Button(controls, text="발음 듣기", command=lambda: app.speak_japanese(data[app.writing_index][0])).pack(side="left", padx=4)
    ttk.Button(controls, text="획순 단계 보기", command=lambda: render_stroke_steps(app, data[app.writing_index][0])).pack(side="left", padx=4)
    ttk.Button(controls, text="입력 확인", command=check).pack(side="left", padx=4)
    ttk.Button(controls, text="그림 지우기", command=clear_canvas).pack(side="left", padx=4)
    ttk.Button(controls, text="다음", style="Accent.TButton", command=lambda: move(1)).pack(side="left", padx=4)
    def move(step): app.writing_index = (app.writing_index + step) % len(data); render()
    render()


def render_stroke_steps(app, char):
    steps = WRITING_GUIDES.get(char)
    if not steps:
        messagebox.showinfo("획순 안내", f"「{char}」의 단계별 획순 안내는 아직 준비 중입니다. 견본을 보고 천천히 연습해 보세요.")
        return
    dialog = tk.Toplevel(app); dialog.title(f"{char} 획순 단계"); dialog.configure(bg="white"); dialog.transient(app); dialog.grab_set()
    dialog.bind("<Escape>", lambda event: dialog.destroy())
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


def render_sentence_building(app):
    if app.selected_level not in CONTENT:
        app.select_level("N5"); return
    items = SENTENCE_BUILDING[app.selected_level]; state = {"index": 0, "chosen": []}
    main = app.page("학습", "문장 만들기", "단어 조각을 눌러 자연스러운 일본어 문장을 완성하세요.")
    card = app.card(main); card.pack(fill="both", expand=True)
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
        korean, correct, _ = items[state["index"]]; content_id = f"{app.selected_level}:sentence:{'|'.join(correct)}"
        if state["chosen"] == correct:
            app.db.record_answer(content_id, True); feedback.config(text="정확해요! 어순과 조사를 함께 확인해 보세요.", fg="#165b52")
        else:
            app.db.record_answer(content_id, False); feedback.config(text="정답: " + " ".join(correct), fg="#b95140")
    controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
    ttk.Button(controls, text="초기화", command=render).pack(side="left", padx=4)
    ttk.Button(controls, text="정답 확인", command=check).pack(side="left", padx=4)
    ttk.Button(controls, text="다음 문장", style="Accent.TButton", command=lambda: next_item()).pack(side="left", padx=4)
    def next_item(): state["index"] = (state["index"] + 1) % len(items); render()
    render()


def render_dictation(app):
    if app.selected_level not in CONTENT:
        app.select_level("N5"); return
    words = app.current_content()["words"]
    app.dictation_index = 0
    main = app.page("학습", "단어 받아쓰기", "발음을 듣고 일본어 표기와 읽기를 직접 입력하세요. AI 음성이 자동으로 준비됩니다.")
    card = app.card(main); card.pack(fill="both", expand=True)
    hint = tk.Label(card, font=("맑은 고딕", 15, "bold"), fg="#173c35", bg="white"); hint.pack(pady=(32, 10))
    entry = ttk.Entry(card, justify="center", font=("Yu Gothic", 28), width=18); entry.pack(pady=10)
    feedback = tk.Label(card, font=("맑은 고딕", 11), fg="#66776f", bg="white", wraplength=700); feedback.pack(pady=8)
    def render():
        word, reading, meaning, example = words[app.dictation_index]
        hint.config(text=f"뜻: {meaning}  ·  예문: {example}"); entry.delete(0, "end"); feedback.config(text="먼저 발음을 듣고 입력해 보세요.", fg="#66776f")
    def check():
        word, reading, meaning, _ = words[app.dictation_index]; guess = entry.get().strip()
        content_id = f"{app.selected_level}:dictation:{word}"
        if guess == word:
            app.db.record_answer(content_id, True); feedback.config(text=f"정답! {word} ({reading})", fg="#165b52")
        else:
            app.db.record_answer(content_id, False); feedback.config(text=f"정답: {word} ({reading})", fg="#b95140")
    controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
    ttk.Button(controls, text="느리게 듣기", command=lambda: app.speak_japanese(words[app.dictation_index][0], feedback, -3)).pack(side="left", padx=4)
    ttk.Button(controls, text="발음 듣기", command=lambda: app.speak_japanese(words[app.dictation_index][0], feedback)).pack(side="left", padx=4)
    ttk.Button(controls, text="입력 확인", command=check).pack(side="left", padx=4)
    ttk.Button(controls, text="다음", style="Accent.TButton", command=lambda: next_item()).pack(side="left", padx=4)
    def next_item(): app.dictation_index = (app.dictation_index + 1) % len(words); render()
    render()
