"""UI-independent progress, feedback, and learning-insight helpers."""

from content import CONTENT
from learning_services import (content_practice_type, error_cause,
                               normalized_study_plan)


PRACTICE_TYPE_LABELS = {
    "kana": "문자", "word": "단어", "word-cloze": "단어 예문", "kanji": "한자",
    "grammar": "문법", "cloze": "문법 빈칸", "reading": "독해", "listening": "청해",
    "sentence": "문장 만들기", "dictation": "받아쓰기",
}
ERROR_CAUSE_LABELS = {
    "kana": "문자 읽기", "word": "단어 뜻", "word-cloze": "단어 문맥",
    "kanji": "한자 뜻", "grammar": "문법 설명", "cloze": "문법 빈칸",
    "sentence": "문장 어순", "dictation": "받아쓰기", "reading": "독해 근거",
    "listening": "청해 핵심 정보",
}
MOCK_SECTION_LABELS = {
    "kana": "문자", "word": "어휘", "word-cloze": "어휘", "dictation": "어휘",
    "kanji": "한자", "grammar": "문법·문장", "cloze": "문법·문장", "sentence": "문법·문장",
    "reading": "독해", "listening": "청해",
}


def catalog_resume_index(items, level, category, saved_content_id):
    """Find a saved catalog card in the current data, falling back to the first card."""
    identifier_category = "word" if category == "words" else category
    prefix = f"{level}:{identifier_category}:"
    if not saved_content_id or not str(saved_content_id).startswith(prefix):
        return 0
    key = str(saved_content_id)[len(prefix):]
    for index, item in enumerate(items):
        if item[0] == key:
            return index
    return 0


def course_progress_insight(progress):
    """Turn category progress into one focused next-learning recommendation."""
    total_new = sum(values[0] for values in progress.values())
    total_active = sum(values[1] for values in progress.values())
    total_stable = sum(values[2] for values in progress.values())
    if total_new:
        category = max(progress, key=lambda name: (progress[name][0], -("words", "kanji", "grammar").index(name)))
        labels = {"words": "단어", "kanji": "한자", "grammar": "문법"}
        return total_new, total_active, total_stable, f"아직 학습하지 않은 {labels[category]} 카드 {progress[category][0]}개부터 시작해 보세요."
    if total_active:
        return total_new, total_active, total_stable, f"학습 중인 카드가 {total_active}개 있어요. 예정 복습을 풀어 안정적 암기로 옮겨 보세요."
    return total_new, total_active, total_stable, "모든 카드를 안정적 암기 상태로 만들었어요. 복습과 모의고사로 유지해 보세요."


def daily_reminder(goal, answers, due, streak, dismissed=False):
    """Choose one gentle, actionable home-screen prompt for the current day."""
    if dismissed:
        return None
    goal = max(1, int(goal))
    answers = max(0, int(answers))
    due = max(0, int(due))
    if due:
        return "복습 먼저", f"오늘 예정된 복습이 {due}개 있어요. 짧게라도 먼저 끝내면 기억이 더 오래가요.", "복습 시작"
    if answers < goal:
        remaining = goal - answers
        streak_text = f"{streak}일 연속 학습 중이에요. " if streak else ""
        return "오늘의 작은 목표", f"{streak_text}목표까지 {remaining}문항 남았어요. 5분만 투자해도 충분해요.", "학습 시작"
    return None


def daily_course_items(plan, course_day):
    """Return the sequential word batch and rotating grammar item for one course day."""
    normalized = normalized_study_plan(plan)
    content = CONTENT[normalized["level"]]
    day = max(1, int(course_day))
    words = content["words"]
    start = ((day - 1) * normalized["daily_words"]) % len(words)
    word_count = min(normalized["daily_words"], len(words))
    selected_words = [words[(start + index) % len(words)] for index in range(word_count)]
    grammar = content["grammar"][(day - 1) % len(content["grammar"])]
    return normalized, selected_words, grammar


def diagnostic_recommendation(scores):
    """Choose a starting course from the balanced two-question level checks."""
    if scores.get("문자", 0) < 1:
        return "문자"
    for level in ("N5", "N4", "N3", "N2"):
        if scores.get(level, 0) < 2:
            return level
    return "N1"


def diagnostic_insights(scores):
    labels = ("문자", "N5", "N4", "N3", "N2", "N1")
    breakdown = [(label, scores.get(label, 0), 2) for label in labels]
    weakest = min(breakdown, key=lambda item: (item[1] / item[2], labels.index(item[0])))
    if weakest[1] == 2:
        action = "모든 구간을 잘 풀었어요. 추천 과정에서 독해와 청해까지 넓혀 보세요."
    elif weakest[0] == "문자":
        action = "문자 읽기부터 다시 확인하면 이후 단어와 문법 학습이 더 편해져요."
    else:
        action = f"{weakest[0]} 영역의 단어와 문법 카드를 먼저 복습해 보세요."
    return diagnostic_recommendation(scores), breakdown, action


def error_cause_summary(rows):
    """Aggregate review rows into actionable, fine-grained error causes."""
    totals = {}
    for content_id, correct, wrong in rows:
        cause = error_cause(content_id)
        old_correct, old_wrong = totals.get(cause, (0, 0))
        totals[cause] = old_correct + correct, old_wrong + wrong
    return sorted(((cause, correct, wrong) for cause, (correct, wrong) in totals.items() if wrong),
                  key=lambda row: (row[1] / (row[1] + row[2]), -row[2], row[0]))


def error_cause_recommendation(rows):
    summary = error_cause_summary(rows)
    if not summary:
        return None
    cause, correct, wrong = summary[0]
    return cause, ERROR_CAUSE_LABELS.get(cause, cause), correct, wrong


def weakness_recommendation(rows):
    candidates = [row for row in rows if row[2] > 0]
    if not candidates:
        return None
    kind, correct, wrong = min(candidates, key=lambda row: (row[1] / (row[1] + row[2]), -(row[1] + row[2]), row[0]))
    return kind, PRACTICE_TYPE_LABELS.get(kind, kind), correct, wrong


def content_levels_from_ids(content_ids):
    return [level for level in CONTENT if any(content_id.startswith(f"{level}:") for content_id in content_ids)]


def unique_questions_by_id(questions):
    """Keep one retry prompt per learned item while preserving quiz order."""
    seen = set()
    return [question for question in questions if not (question[3] in seen or seen.add(question[3]))]


def practice_progress_summary(question_ids, completed_ids):
    total = len(question_ids)
    return sum(content_id in completed_ids for content_id in question_ids), total


def answer_explanation(content_id, answer):
    """Return a compact study hint from the bundled curriculum for quiz feedback."""
    if content_id.startswith("kana:"):
        return f"「{content_id.split(':', 1)[1]}」는 {answer}(으)로 읽습니다."
    parts = content_id.split(":", 2)
    if len(parts) < 3:
        return "정답과 문제의 핵심 표현을 함께 다시 확인해 보세요."
    level, kind, key = parts
    if level == "custom" and kind == "word":
        return f"내 단어장에 저장한 표현입니다. 뜻: {answer}"
    content = CONTENT.get(level, {})
    if kind in ("word", "dictation"):
        for word, reading, meaning, example in content.get("words", []):
            if word == key:
                return f"{word}({reading}) = {meaning}\n예문: {example}"
    if kind == "kanji":
        for char, reading, meaning, example_word in content.get("kanji", []):
            if char == key:
                return f"{char}({reading})는 '{meaning}'라는 뜻입니다. 예: {example_word}"
    if kind == "grammar":
        for pattern, explanation, example in content.get("grammar", []):
            if pattern == key:
                return f"{explanation}\n예문: {example}"
    if kind == "cloze":
        return f"빈칸에는 문맥에 맞는 「{answer}」가 들어갑니다. 앞뒤 문장과 함께 읽어 보세요."
    if kind == "word-cloze":
        return f"문맥에 맞는 단어는 「{answer}」입니다. 문장 전체를 소리 내어 읽어 보세요."
    if kind == "reading":
        return f"지문에서 근거를 다시 찾아 보세요. 정답: {answer}"
    if kind == "listening":
        return f"대화의 시간, 장소, 요청 표현을 다시 들어 보세요. 정답: {answer}"
    if kind == "sentence":
        return f"조사와 동사 위치를 기준으로 어순을 확인하세요. 정답: {answer}"
    return f"정답: {answer}"


def mock_section(content_id):
    return MOCK_SECTION_LABELS.get(content_practice_type(content_id), "기타")


def mock_exam_insights(scores):
    order = ("문자", "어휘", "한자", "문법·문장", "독해", "청해", "기타")
    breakdown = [(label, *scores[label]) for label in order if scores.get(label, [0, 0])[1]]
    if not breakdown:
        return breakdown, "각 영역을 한 문제씩 풀면 영역별 안내를 받을 수 있어요."
    weakest = min(breakdown, key=lambda row: (row[1] / row[2], -row[2], order.index(row[0])))
    if weakest[1] == weakest[2]:
        return breakdown, "모든 출제 영역을 잘 풀었어요. 다음 모의고사에서 실력을 다시 확인해 보세요."
    return breakdown, f"{weakest[0]} 영역이 가장 약해요. 홈의 집중 연습 또는 해당 학습 메뉴로 이어가 보세요."


def weekly_activity_summary(rows):
    return sum(completed for _, completed, _ in rows), sum(answer_count for _, _, answer_count in rows), max((answer_count for _, _, answer_count in rows), default=0)


def review_workload_insight(rows):
    if not rows:
        return 0, 0, None, "예정된 복습이 아직 없어요. 새 카드를 가볍게 시작해 보세요."
    today_count = rows[0][1]
    upcoming_count = sum(count for _, count in rows[1:])
    peak_date, peak_count = max(rows, key=lambda row: row[1])
    if today_count:
        message = f"오늘 복습 {today_count}개를 먼저 끝내면 이후 일정이 한결 가벼워져요."
    elif upcoming_count:
        message = f"오늘은 여유가 있어요. 다음 복습은 {peak_date}에 {peak_count}개 예정되어 있어요."
    else:
        message = "앞으로 일주일은 예정된 복습이 없어요. 새 카드를 가볍게 시작해 보세요."
    return today_count, upcoming_count, (peak_date, peak_count), message


def achievement_milestones(study_days, answers, streak):
    return (("첫 발걸음", "학습한 날 1일", study_days >= 1),
            ("일주일 습관", "연속 학습 7일", streak >= 7),
            ("한 달의 힘", "학습한 날 30일", study_days >= 30),
            ("문제 해결사", "누적 100문제", answers >= 100),
            ("꾸준한 도전자", "누적 500문제", answers >= 500))


def quiz_trend_insight(rows):
    if not rows:
        return None
    recent_score = sum(score for _, _, score, _ in rows)
    recent_total = sum(total for _, _, _, total in rows)
    recent_rate = round(recent_score * 100 / recent_total) if recent_total else 0
    if len(rows) < 4:
        return recent_rate, None, "최근 퀴즈를 더 풀면 정확도 변화도 함께 알려드려요."
    midpoint = len(rows) // 2
    earlier, latest = rows[:midpoint], rows[midpoint:]
    earlier_score = sum(score for _, _, score, _ in earlier)
    earlier_total = sum(total for _, _, _, total in earlier)
    latest_score = sum(score for _, _, score, _ in latest)
    latest_total = sum(total for _, _, _, total in latest)
    change = (round(latest_score * 100 / latest_total) if latest_total else 0) - (round(earlier_score * 100 / earlier_total) if earlier_total else 0)
    if change >= 5:
        message = f"최근 정확도가 이전 기록보다 {change}%p 올랐어요. 좋은 흐름을 이어가 보세요."
    elif change <= -5:
        message = f"최근 정확도가 이전 기록보다 {abs(change)}%p 낮아요. 오답 복습으로 감각을 다시 잡아 보세요."
    else:
        message = "최근 정확도가 안정적이에요. 어려운 유형을 한 가지 더 도전해 보세요."
    return recent_rate, change, message
