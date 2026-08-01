"""Pure learning configuration and import helpers, kept independent of Tkinter."""

import csv
import io

from content import CONTENT


DEFAULT_STUDY_PLAN = {"level": "N5", "days": 30, "daily_words": 10}
DEFAULT_REVIEW_LIMIT = 20
DEFAULT_TEXT_SCALE = 100
DEFAULT_MOCK_EXAM = {"questions": 12, "minutes": 15}
THEME_LABELS = {"standard": "기본 색상", "high-contrast": "고대비 색상"}


def normalized_study_plan(plan, fallback_level="N5"):
    source = plan if isinstance(plan, dict) else {}
    level = source.get("level", fallback_level)
    if level not in CONTENT:
        level = fallback_level if fallback_level in CONTENT else "N5"
    return {
        "level": level,
        "days": max(7, min(365, int(source.get("days", DEFAULT_STUDY_PLAN["days"])))),
        "daily_words": max(3, min(50, int(source.get("daily_words", DEFAULT_STUDY_PLAN["daily_words"])))),
    }


def normalized_review_limit(value, default=DEFAULT_REVIEW_LIMIT):
    """Keep a daily review workload within a manageable range."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(5, min(50, value))


def normalized_text_scale(value, default=DEFAULT_TEXT_SCALE):
    """Keep the interface readable without allowing unusable widget sizes."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(80, min(140, value))


def display_scale(mode, value=DEFAULT_TEXT_SCALE):
    """Use Windows DPI scaling by default; only apply a multiplier on request."""
    return DEFAULT_TEXT_SCALE if mode != "manual" else normalized_text_scale(value)


def normalized_mock_exam(settings):
    """Keep the JLPT-style practice session short enough for an offline study app."""
    source = settings if isinstance(settings, dict) else {}
    try:
        questions = int(source.get("questions", DEFAULT_MOCK_EXAM["questions"]))
        minutes = int(source.get("minutes", DEFAULT_MOCK_EXAM["minutes"]))
    except (TypeError, ValueError):
        questions, minutes = DEFAULT_MOCK_EXAM.values()
    return {"questions": max(12, min(40, questions)), "minutes": max(5, min(90, minutes))}


def mock_exam_time_summary(score, total, remaining_seconds, initial_seconds):
    """Return an exam result line that makes elapsed time clear without official-score claims."""
    total = max(1, int(total))
    initial_seconds = max(1, int(initial_seconds))
    remaining_seconds = max(0, min(initial_seconds, int(remaining_seconds)))
    elapsed = initial_seconds - remaining_seconds
    minutes, seconds = divmod(elapsed, 60)
    rate = round(score * 100 / total)
    timing = "시간 종료" if remaining_seconds == 0 else f"소요 {minutes}분 {seconds:02d}초"
    readiness = "좋은 출발" if rate >= 70 else "복습 권장"
    return f"{score}/{total} ({rate}%) · {timing} · {readiness}"


def error_cause_learning_path(cause):
    """Give an error type a concrete study action before another quiz attempt."""
    paths = {
        "kana": ("문자표를 소리 내어 읽고 문자 퀴즈로 확인하세요.", "문자 학습"),
        "word": ("단어 카드의 예문을 읽고 뜻과 장면을 함께 연결해 보세요.", "단어 카드"),
        "word-cloze": ("예문 전체를 읽어 단어가 쓰인 문맥을 먼저 확인하세요.", "단어 카드"),
        "kanji": ("한자 뜻과 대표 단어를 함께 보고 직접 써 보세요.", "한자 카드"),
        "grammar": ("문법 설명과 예문을 한 번 읽은 뒤 빈칸 문제를 풀어 보세요.", "문법 카드"),
        "cloze": ("문장 앞뒤의 연결과 뉘앙스를 먼저 확인해 보세요.", "문법 카드"),
        "sentence": ("조각의 역할을 찾아 문장 끝 동사부터 순서를 정리해 보세요.", "문장 만들기"),
        "dictation": ("읽기를 들으며 글자 단위로 나눠 적은 뒤 다시 들어 보세요.", "받아쓰기"),
        "reading": ("질문의 핵심어를 표시하고 지문에서 같은 근거를 찾아 보세요.", "독해 연습"),
        "listening": ("느린 속도로 핵심 숫자·시간·의도를 먼저 잡아 보세요.", "청해 연습"),
    }
    return paths.get(cause, ("오답 설명을 다시 읽고 집중 문제로 확인해 보세요.", "집중 연습"))


def personal_word_import_rows(text):
    """Parse a small CSV word list without accepting malformed study records."""
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV 첫 줄에 word, reading, meaning 열이 필요합니다.")
    fields = {field.strip().lower(): field for field in reader.fieldnames if field}
    required = ("word", "reading", "meaning")
    if any(field not in fields for field in required):
        raise ValueError("CSV에는 word, reading, meaning 열이 모두 필요합니다.")
    example_field = fields.get("example")
    rows = []
    for row in reader:
        values = tuple((row.get(fields[field]) or "").strip() for field in required)
        example = (row.get(example_field) or "").strip() if example_field else ""
        if not any(values) and not example:
            continue
        if not all(values):
            raise ValueError("각 행에는 word, reading, meaning을 모두 입력해야 합니다.")
        rows.append((*values, example))
    return rows


def normalized_theme(value):
    return value if value in THEME_LABELS else "standard"

LEVEL_ORDER = ["초보", "문자", "N5", "N4", "N3", "N2", "N1"]

def card_learning_state(review_row):
    """Classify a catalog card from its answer history and current SRS interval."""
    if review_row is None:
        return "학습 전"
    correct, wrong, interval_step = review_row
    if correct > wrong and interval_step >= 2:
        return "안정적 암기"
    return "학습 중"

def catalog_progress_summary(items, level, category, review_rows):
    """Count new, active, and stable cards for one catalog category."""
    identifier_category = "word" if category == "words" else category
    counts = {"학습 전": 0, "학습 중": 0, "안정적 암기": 0}
    for item in items:
        content_id = f"{level}:{identifier_category}:{item[0]}"
        counts[card_learning_state(review_rows.get(content_id))] += 1
    return counts["학습 전"], counts["학습 중"], counts["안정적 암기"]

def content_practice_type(content_id):
    if content_id.startswith("kana:"):
        return "kana"
    parts = content_id.split(":")
    return parts[1] if len(parts) > 1 else "other"

def error_cause(content_id):
    """Classify an item by the skill that likely caused the missed answer."""
    return content_practice_type(content_id)

def favorite_card_details(content_ids):
    """Resolve saved catalog IDs into displayable cards across every course level."""
    details = []
    for content_id in content_ids:
        parts = content_id.split(":", 2)
        if len(parts) != 3:
            continue
        level, category, key = parts
        content = CONTENT.get(level, {})
        if category == "word":
            for word, reading, meaning, example in content.get("words", []):
                if word == key:
                    details.append((content_id, level, "words", word, f"{reading} · {meaning}", example))
                    break
        elif category == "kanji":
            for char, reading, meaning, example_word in content.get("kanji", []):
                if char == key:
                    details.append((content_id, level, "kanji", char, f"{reading} · {meaning}", f"핵심 어휘: {example_word}"))
                    break
        elif category == "grammar":
            for pattern, explanation, example in content.get("grammar", []):
                if pattern == key:
                    details.append((content_id, level, "grammar", pattern, explanation, example))
                    break
    category_order = {"words": 0, "kanji": 1, "grammar": 2}
    return sorted(details, key=lambda row: (LEVEL_ORDER.index(row[1]) if row[1] in LEVEL_ORDER else 99, category_order[row[2]], row[3]))

def level_mastery_summary(level, review_rows):
    """Measure catalog coverage and stable recall from review records for one level."""
    content = CONTENT.get(level, {})
    card_ids = {
        *(f"{level}:word:{word}" for word, _, _, _ in content.get("words", [])),
        *(f"{level}:kanji:{char}" for char, _, _, _ in content.get("kanji", [])),
        *(f"{level}:grammar:{pattern}" for pattern, _, _ in content.get("grammar", [])),
    }
    reviewed = {content_id for content_id, _, _, _ in review_rows if content_id in card_ids}
    mastered = {
        content_id for content_id, correct, wrong, interval_step in review_rows
        if content_id in card_ids and correct > wrong and interval_step >= 2
    }
    return len(reviewed), len(mastered), len(card_ids)
