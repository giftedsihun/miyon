"""Interactive catalog renderer with application-owned persistence callbacks."""

import tkinter as tk
from tkinter import messagebox, ttk

from content import CONTENT
from learning_services import card_learning_state, catalog_progress_summary
from progress_logic import catalog_resume_index
from study_logic import card_study_prompt


CATALOG_TITLES = {
    "words": "단어 카드",
    "kanji": "한자 카드",
    "grammar": "문법 학습",
}


def render_catalog(app, category, items=None, subtitle=None, content_level=None):
    """Render searchable cards while app methods retain navigation and side effects."""
    level = content_level or app.selected_level
    data = items or CONTENT.get(level, CONTENT["N5"])[category]
    resume_enabled = items is None
    app.catalog_index = catalog_resume_index(data, level, category, app.db.catalog_resume_id(level, category)) if resume_enabled else 0
    main = app.page("학습", CATALOG_TITLES[category], subtitle or f"{level} 과정 · 예문까지 읽고 다음 카드로 넘어가세요.")
    search_row = tk.Frame(main, bg="#f4f6f0"); search_row.pack(fill="x", pady=(0, 10))
    query = tk.StringVar()
    search = ttk.Entry(search_row, textvariable=query, width=34, font=("맑은 고딕", 10)); search.pack(side="left")
    tk.Label(search_row, text="일본어, 읽기, 뜻으로 검색", font=("맑은 고딕", 9), fg="#718078", bg="#f4f6f0").pack(side="left", padx=9)
    favorites_only, notes_only = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
    new_only, active_only, stable_only = tk.BooleanVar(value=False), tk.BooleanVar(value=False), tk.BooleanVar(value=False)
    tag = tk.StringVar(value="전체")
    ttk.Checkbutton(search_row, text="즐겨찾기만", variable=favorites_only, command=lambda: filter_cards()).pack(side="right")
    ttk.Checkbutton(search_row, text="메모만", variable=notes_only, command=lambda: filter_cards()).pack(side="right", padx=(0, 8))
    ttk.Checkbutton(search_row, text="학습 전만", variable=new_only, command=lambda: filter_cards()).pack(side="right", padx=(0, 8))
    ttk.Checkbutton(search_row, text="학습 중만", variable=active_only, command=lambda: filter_cards()).pack(side="right", padx=(0, 8))
    ttk.Checkbutton(search_row, text="안정만", variable=stable_only, command=lambda: filter_cards()).pack(side="right", padx=(0, 8))
    if category == "words":
        ttk.Combobox(search_row, textvariable=tag, values=("전체", "동사", "명사", "형용사·부사"), state="readonly", width=11).pack(side="right", padx=8)

    def item_id(item):
        return f"{level}:{'word' if category == 'words' else category}:{item[0]}"

    review_rows = app.db.catalog_review_rows(level, category)
    progress = catalog_progress_summary(data, level, category, review_rows)
    tk.Label(main, text=f"카드 진도 · 학습 전 {progress[0]} · 학습 중 {progress[1]} · 안정적 암기 {progress[2]}", font=("맑은 고딕", 10, "bold"), fg="#a2543e", bg="#f4f6f0").pack(anchor="w", pady=(0, 8))
    card = app.card(main); card.pack(fill="both", expand=True)
    title = tk.Label(card, font=("맑은 고딕", 33, "bold"), fg="#165b52", bg="white"); title.pack(pady=(55, 12))
    detail = tk.Label(card, font=("맑은 고딕", 16), fg="#173c35", bg="white", wraplength=760, justify="center"); detail.pack(padx=25)
    example = tk.Label(card, font=("맑은 고딕", 12), fg="#66776f", bg="white", wraplength=760, justify="center"); example.pack(pady=(15, 25))
    counter = tk.Label(card, font=("맑은 고딕", 10), fg="#718078", bg="white"); counter.pack()
    favorite = ttk.Button(card); favorite.pack(pady=(10, 0))
    note_status = tk.Label(card, font=("맑은 고딕", 9), fg="#718078", bg="white"); note_status.pack(pady=(6, 0))
    visible = list(data)

    def render():
        if not visible:
            title.config(text="검색 결과 없음", font=("맑은 고딕", 24, "bold")); detail.config(text="다른 검색어를 입력해 보세요.")
            example.config(text=""); counter.config(text=""); favorite.pack_forget(); note_status.config(text=""); return
        item = visible[app.catalog_index]
        if category == "words":
            title.config(text=item[0]); detail.config(text=f"{item[1]} · {item[2]}"); example.config(text=item[3])
        elif category == "kanji":
            title.config(text=item[0]); detail.config(text=f"읽기: {item[1]} · 뜻: {item[2]}"); example.config(text=f"핵심 어휘: {item[3]}")
        else:
            title.config(text=item[0], font=("맑은 고딕", 23, "bold")); detail.config(text=item[1]); example.config(text=item[2])
        resume_text = " · 이어서 학습 중" if resume_enabled else ""
        counter.config(text=f"{app.catalog_index + 1} / {len(visible)}{resume_text}")
        favorite.pack(pady=(10, 0)); favorite.config(text="즐겨찾기 해제" if app.db.is_favorite(item_id(item)) else "즐겨찾기 추가", command=lambda value=item: toggle_favorite(value))
        state = card_learning_state(review_rows.get(item_id(item)))
        note = " · 내 메모 있음" if app.db.get_note(item_id(item)) else ""
        note_status.config(text=f"{state}{note}\n{card_study_prompt(category, item)}", fg="#165b52" if state == "안정적 암기" else "#718078", wraplength=700, justify="center")

    def toggle_favorite(item):
        app.db.toggle_favorite(item_id(item)); render()

    def edit_note():
        if not visible:
            return
        item = visible[app.catalog_index]; identifier = item_id(item)
        dialog = tk.Toplevel(app); dialog.title("카드 메모"); dialog.configure(bg="white"); dialog.transient(app); dialog.grab_set()
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        tk.Label(dialog, text=f"{item[0]} 메모", font=("맑은 고딕", 15, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=24, pady=(22, 5))
        tk.Label(dialog, text="암기 팁, 헷갈리는 표현, 나만의 예문을 저장하세요. 빈 메모로 저장하면 삭제됩니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=430, justify="left").pack(anchor="w", padx=24)
        text = tk.Text(dialog, width=52, height=8, font=("맑은 고딕", 10), wrap="word")
        text.pack(padx=24, pady=(12, 8)); text.insert("1.0", app.db.get_note(identifier)); text.focus_set()
        status = tk.Label(dialog, text="", font=("맑은 고딕", 9), fg="#66776f", bg="white"); status.pack(anchor="w", padx=24)

        def save_note():
            saved = app.db.save_note(identifier, text.get("1.0", "end-1c"))
            status.config(text="메모를 저장했어요." if saved else "메모를 삭제했어요.", fg="#165b52")
            render()

        actions = tk.Frame(dialog, bg="white"); actions.pack(anchor="e", padx=24, pady=(8, 22))
        ttk.Button(actions, text="저장", style="Accent.TButton", command=save_note).pack(side="left", padx=4)
        ttk.Button(actions, text="닫기", command=dialog.destroy).pack(side="left", padx=4)

    def start_visible_quiz():
        pool = app.catalog_question_pool(category, level, visible)
        if not pool:
            messagebox.showinfo("카드 퀴즈", "퀴즈로 만들 수 있는 카드가 없어요.")
            return
        app.start_quiz(mode=category, title="현재 카드 확인 퀴즈", pool=pool)

    def filter_cards(*_):
        nonlocal visible
        text = query.get().strip().lower(); notes = app.db.notes_by_id(); noted_ids = set(notes)

        def matches_tag(item):
            if category != "words" or tag.get() == "전체": return True
            word = item[0]
            if tag.get() == "동사": return word.endswith(("る", "う", "く", "す", "む", "ぶ", "つ"))
            if tag.get() == "형용사·부사": return word.endswith(("い", "な", "に")) or word in ("特に", "最近", "具体的")
            return not (word.endswith(("る", "う", "く", "す", "む", "ぶ", "つ", "い", "な", "に")) or word in ("特に", "最近", "具体的"))

        visible = [item for item in data if (not text or text in (" ".join(item) + " " + notes.get(item_id(item), "")).lower()) and matches_tag(item) and (not favorites_only.get() or app.db.is_favorite(item_id(item))) and (not notes_only.get() or item_id(item) in noted_ids) and (not new_only.get() or card_learning_state(review_rows.get(item_id(item))) == "학습 전") and (not active_only.get() or card_learning_state(review_rows.get(item_id(item))) == "학습 중") and (not stable_only.get() or card_learning_state(review_rows.get(item_id(item))) == "안정적 암기")]
        app.catalog_index = 0; render()

    query.trace_add("write", filter_cards); tag.trace_add("write", filter_cards)
    controls = tk.Frame(main, bg="#f4f6f0"); controls.pack(pady=15)
    ttk.Button(controls, text="이전", command=lambda: move(-1)).pack(side="left", padx=4)
    if resume_enabled:
        ttk.Button(controls, text="처음부터", command=lambda: reset_catalog()).pack(side="left", padx=4)
    ttk.Button(controls, text="현재 카드 퀴즈", style="Accent.TButton", command=start_visible_quiz).pack(side="left", padx=4)
    ttk.Button(controls, text="내 메모", command=edit_note).pack(side="left", padx=4)
    if category in ("words", "grammar"):
        ttk.Button(controls, text="예문 듣기", command=lambda: app.speak_japanese(visible[app.catalog_index][3] if category == "words" else visible[app.catalog_index][2]) if visible else None).pack(side="left", padx=4)
    if category == "kanji":
        ttk.Button(controls, text="쓰기 연습", command=app.show_kanji_writing).pack(side="left", padx=4)
    ttk.Button(controls, text="다음", command=lambda: move(1)).pack(side="left", padx=4)

    def move(step):
        if visible:
            app.catalog_index = (app.catalog_index + step) % len(visible)
            if resume_enabled:
                app.db.save_catalog_resume(level, category, item_id(visible[app.catalog_index]))
            render()

    def reset_catalog():
        app.catalog_index = 0; app.db.save_catalog_resume(level, category, item_id(data[0])); render()

    if resume_enabled and data:
        app.db.save_catalog_resume(level, category, item_id(data[app.catalog_index]))
    render()
