"""UI-independent quiz feedback, result, and question-pool helpers."""

import random

from content import (CONTENT, GRAMMAR_CLOZE, KANA, LISTENING_DIALOGUES,
                     READING_PASSAGES, SENTENCE_BUILDING, WORD_CLOZE)


def catalog_question_pool(category, level, items):
    """Build questions from the cards currently visible in a catalog view."""
    content = CONTENT.get(level)
    if not content:
        return []
    pool = []
    if category == "words":
        for word, reading, meaning, _ in items:
            distractors = [candidate[2] for candidate in content["words"] if candidate[2] != meaning]
            pool.append((f"「{word}」({reading})의 뜻은 무엇인가요?", meaning, distractors, f"{level}:word:{word}"))
    elif category == "kanji":
        for char, _, meaning, _ in items:
            distractors = [candidate[2] for candidate in content["kanji"] if candidate[2] != meaning]
            pool.append((f"한자 「{char}」의 뜻은 무엇인가요?", meaning, distractors, f"{level}:kanji:{char}"))
    elif category == "grammar":
        for pattern, explanation, _ in items:
            distractors = [candidate[1] for candidate in content["grammar"] if candidate[1] != explanation]
            pool.append((f"「{pattern}」의 설명으로 알맞은 것은?", explanation, distractors, f"{level}:grammar:{pattern}"))
    return [question for question in pool if len(question[2]) >= 3]


def personal_word_question_pool(words, word_ids=None):
    """Build personal-word questions from database rows supplied by the caller."""
    pool = []
    for word_id, word, reading, meaning, _, _ in words:
        content_id = f"custom:word:{word_id}"
        if word_ids is not None and content_id not in word_ids:
            continue
        distractors = [candidate[3] for candidate in words if candidate[0] != word_id and candidate[3] != meaning]
        if len(distractors) >= 3:
            pool.append((f"[나의 단어장] 「{word}」({reading})의 뜻은 무엇인가요?", meaning, distractors, content_id))
    return pool


def question_pool(mode, selected_level, kana_set=None, content_levels=None,
                  favorite_ids=None, due_ids=None, weak_ids=None, personal_words=()):
    """Build a complete quiz pool without coupling question generation to Tkinter."""
    pool = []
    if mode == "personal-words":
        return personal_word_question_pool(personal_words)
    if mode == "diagnostic":
        chars = kana_set or KANA
        for char, reading in random.sample(chars, 2):
            pool.append((f"「{char}」의 발음은 무엇인가요?", reading, [x[1] for x in chars if x[1] != reading], f"kana:{char}"))
        for level in ("N5", "N4", "N3", "N2", "N1"):
            word, reading, meaning, _ = random.choice(CONTENT[level]["words"])
            pattern, explanation, _ = random.choice(CONTENT[level]["grammar"])
            grammar_prompt, grammar_answer, grammar_distractors = random.choice(GRAMMAR_CLOZE[level])
            word_prompt, word_answer, word_distractors = random.choice(WORD_CLOZE[level])
            question_types = (
                (f"「{word}」({reading})의 뜻은 무엇인가요?", meaning, [x[2] for x in CONTENT[level]["words"] if x[2] != meaning], f"{level}:word:{word}"),
                (f"「{pattern}」의 설명으로 알맞은 것은?", explanation, [x[1] for x in CONTENT[level]["grammar"] if x[1] != explanation], f"{level}:grammar:{pattern}"),
                (f"[문법 빈칸] {grammar_prompt}", grammar_answer, grammar_distractors, f"{level}:cloze:{grammar_prompt}"),
                (f"[단어 예문 빈칸] {word_prompt}", word_answer, word_distractors, f"{level}:word-cloze:{word_prompt}"),
            )
            pool.extend(random.sample(question_types, 2))
        return pool
    if mode == "kana":
        chars = kana_set or KANA
        for char, reading in chars:
            pool.append((f"「{char}」의 발음은 무엇인가요?", reading, [x[1] for x in chars if x[1] != reading], f"kana:{char}"))
    levels = content_levels or [selected_level]
    if mode in ("reading", "mock"):
        for level in levels:
            for index, (title, passage, question, answer, options) in enumerate(READING_PASSAGES.get(level, [])):
                pool.append((f"[독해 · {title}]\n{passage}\n\n{question}", answer, [option for option in options if option != answer], f"{level}:reading:{index}"))
    if mode in ("listening", "mock"):
        for level in levels:
            for index, (dialogue, question, answer, options) in enumerate(LISTENING_DIALOGUES.get(level, [])):
                pool.append((f"[청해 연습 · 대화문]\n{dialogue}\n\n{question}", answer, [option for option in options if option != answer], f"{level}:listening:{index}"))
    for level in levels:
        if level not in CONTENT:
            continue
        content = CONTENT[level]
        if mode in ("words", "mixed", "review", "weak", "diagnostic", "mock"):
            for word, reading, meaning, _ in content["words"]:
                pool.append((f"「{word}」({reading})의 뜻은 무엇인가요?", meaning, [x[2] for x in content["words"] if x[2] != meaning], f"{level}:word:{word}"))
            for prompt, answer, distractors in WORD_CLOZE[level]:
                pool.append((f"[단어 예문 빈칸] {prompt}", answer, distractors, f"{level}:word-cloze:{prompt}"))
        if mode in ("kanji", "mixed", "diagnostic", "mock"):
            for char, _, meaning, _ in content["kanji"]:
                pool.append((f"한자 「{char}」의 뜻은 무엇인가요?", meaning, [x[2] for x in content["kanji"] if x[2] != meaning], f"{level}:kanji:{char}"))
        if mode in ("grammar", "mixed", "diagnostic", "mock"):
            for pattern, explanation, _ in content["grammar"]:
                pool.append((f"「{pattern}」의 설명으로 알맞은 것은?", explanation, [x[1] for x in content["grammar"] if x[1] != explanation], f"{level}:grammar:{pattern}"))
            for prompt, answer, distractors in GRAMMAR_CLOZE[level]:
                pool.append((f"[문법 빈칸] {prompt}", answer, distractors, f"{level}:cloze:{prompt}"))
        if mode in ("sentence", "mixed", "mock"):
            for korean, chunks, _ in SENTENCE_BUILDING[level]:
                answer = " ".join(chunks)
                alternatives = set()
                while len(alternatives) < 3:
                    candidate = " ".join(random.sample(chunks, len(chunks)))
                    if candidate != answer:
                        alternatives.add(candidate)
                pool.append((f"[문장 만들기] {korean}\n알맞은 문장 순서는?", answer, list(alternatives), f"{level}:sentence:{'|'.join(chunks)}"))
        if mode == "dictation":
            for word, reading, _, _ in content["words"]:
                pool.append((f"[받아쓰기] 「{reading}」의 일본어 표기는?", word, [item[0] for item in content["words"] if item[0] != word], f"{level}:dictation:{word}"))
    if mode == "favorites":
        ids = favorite_ids or set()
        levels = [level for level in CONTENT if any(content_id.startswith(f"{level}:") for content_id in ids)]
        base_pool = (question_pool("mixed", selected_level, content_levels=levels) +
                     question_pool("kanji", selected_level, content_levels=levels) +
                     question_pool("grammar", selected_level, content_levels=levels))
        pool = [item for item in base_pool if item[3] in ids]
    if mode in ("review", "weak"):
        ids = due_ids if mode == "review" else weak_ids
        ids = ids or set()
        levels = [level for level in CONTENT if any(content_id.startswith(f"{level}:") for content_id in ids)]
        all_items = (question_pool("mixed", selected_level, content_levels=levels) + question_pool("kana", selected_level) +
                     question_pool("reading", selected_level, content_levels=levels) + question_pool("listening", selected_level, content_levels=levels) +
                     question_pool("dictation", selected_level, content_levels=levels) + personal_word_question_pool(personal_words, ids))
        pool = [item for item in all_items if item[3] in ids]
    return pool


def comprehension_study_tip(content_id, answer):
    """Give a repeatable evidence-finding routine for comprehension prompts."""
    if ":reading:" in content_id:
        return f"독해 순서: 질문의 핵심어를 먼저 찾고, 지문에서 이유·시간·조건을 확인하세요. 근거를 찾은 뒤 정답 「{answer}」를 고르세요."
    if ":listening:" in content_id:
        return f"청해 순서: 누가·언제·무엇을 할지를 먼저 메모하고, 바뀐 조건이나 요청을 확인하세요. 핵심 답: 「{answer}」"
    return "문제의 핵심어와 예문을 함께 확인한 뒤 답을 고르세요."


def mock_exam_comparison(current_score, current_total, previous):
    """Compare a mock result with the most recent prior attempt, when available."""
    current_rate = round(current_score * 100 / max(1, current_total))
    if not previous:
        return "첫 모의고사 기록이에요. 다음 응시부터 점수 변화를 알려드려요."
    _, score, total, _, _ = previous[0]
    previous_rate = round(score * 100 / max(1, total))
    difference = current_rate - previous_rate
    if difference > 0:
        return f"지난 모의고사보다 {difference}%p 올랐어요."
    if difference < 0:
        return f"지난 모의고사보다 {abs(difference)}%p 낮아요. 약한 영역을 다시 확인해 보세요."
    return "지난 모의고사와 같은 정확도예요. 제한 시간 안에서 풀이 순서를 다듬어 보세요."
