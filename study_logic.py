"""Small, UI-independent study helpers shared by the Haru Japanese app and tests."""


def card_study_prompt(category, item):
    """Give each catalog card one small active-recall action before moving on."""
    if category == "words":
        return f"「{item[0]}」를 보고 뜻을 말한 뒤 예문 「{item[3]}」을 소리 내어 읽어 보세요."
    if category == "kanji":
        return f"「{item[0]}」의 뜻을 떠올리고 핵심 어휘 「{item[3]}」를 한 번 써 보세요."
    return f"「{item[0]}」를 사용해 내 상황에 맞는 문장을 하나 바꿔 말해 보세요."


def study_plan_pace(plan, course_day, total_cards, stable_cards):
    """Turn a normalized course plan into a clear pace and completion message."""
    day = max(1, int(course_day))
    total_cards = max(0, int(total_cards))
    stable_cards = max(0, min(total_cards, int(stable_cards)))
    daily_words = max(1, int(plan["daily_words"]))
    plan_days = max(1, int(plan["days"]))
    planned_cards = min(total_cards, day * daily_words)
    remaining_days = max(0, plan_days - day + 1)
    remaining_cards = total_cards - stable_cards
    required_daily = (remaining_cards + max(1, remaining_days) - 1) // max(1, remaining_days)
    if stable_cards >= total_cards and total_cards:
        message = "목표 과정의 카드를 모두 안정적으로 기억하고 있어요. 복습과 모의고사로 유지해 보세요."
    elif stable_cards >= planned_cards:
        message = f"계획 속도를 잘 따라가고 있어요. 남은 카드는 하루 약 {required_daily}개씩 확인하면 됩니다."
    else:
        message = f"계획 기준 {planned_cards}개 중 안정적 암기 {stable_cards}개예요. 오늘은 복습을 먼저 해 보세요."
    return planned_cards, remaining_days, required_daily, message


def tts_recovery_steps(state, missing_commands):
    """Provide safe local-TTS recovery steps without changing the system."""
    missing_commands = tuple(missing_commands)
    if state == "ready":
        return ("테스트 음성으로 실제 재생을 확인하세요.",)
    if state == "stopped":
        return ("서버 시작을 눌러 로컬 API를 다시 실행하세요.", "계속 실패하면 서버 로그를 확인하세요.")
    if state == "prerequisite":
        steps = []
        if "ffmpeg" in missing_commands:
            steps.append("FFmpeg: winget install Gyan.FFmpeg")
        if "git" in missing_commands:
            steps.append("Git을 설치한 뒤 앱을 다시 시작하세요.")
        if "uv" in missing_commands:
            steps.append("uv를 설치한 뒤 앱을 다시 시작하세요.")
        return tuple(steps)
    return ("서버 시작을 누르면 필요한 파일을 준비합니다.", "대용량 모델 설치는 인터넷 연결과 디스크 여유 공간이 필요합니다.")
