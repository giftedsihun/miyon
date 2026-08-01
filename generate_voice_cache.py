# -*- coding: utf-8 -*-
"""Pre-generate Zundamon wav files for every Japanese text the app can speak.

Writes into voice_cache/ as <sha1(text|speed)>.wav so speak_japanese can play
them instantly without the ttsclient server. Covers normal (1.0) and slow (0.85)
speed variants, matching the app's "발음 듣기" and "느리게 듣기" buttons.
"""
import io
import sys
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\games\Desktop\miyon")

from tts_service import voice_cache_path, ttsclient_generate_voice, api_available, TTS_CLIENT_URL
import content as c


def collect_texts():
    """Return a set of every Japanese string the app passes to speak_japanese."""
    texts = set()

    for lv, _desc, _d, _grp in c.LEVELS:
        if lv not in c.CONTENT:
            continue
        cat = c.CONTENT[lv]
        for w in cat["words"]:
            texts.add(w[0])           # 단어 발음 (쓰기/받아쓰기/내 단어)
            texts.add(w[3])           # 예문 듣기 (단어 카드)
        for k in cat["kanji"]:
            texts.add(k[0])           # 한자 쓰기 연습 발음
        for g in cat["grammar"]:
            texts.add(g[2])           # 문법 예문 듣기
        for p in c.READING_PASSAGES.get(lv, []):
            texts.add(p[1])           # 독해 지문 (듣기용)
        for d in c.LISTENING_DIALOGUES.get(lv, []):
            texts.add(d[0])           # 듣기 대화문

    for ch, _rd in c.KANA:
        texts.add(ch)                 # 가나 발음

    texts.add("こんにちは。音声テストです。")  # 설정 다이얼로그 테스트 음성
    return sorted(texts)


def generate_one(text, speed):
    path = voice_cache_path(text, speed)
    if path.is_file() and path.stat().st_size > 1024:
        return path, True
    try:
        audio = ttsclient_generate_voice(text, speed)
        if not audio.startswith(b"RIFF"):
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(audio)
        return path, True
    except Exception:
        return path, False


def main():
    texts = collect_texts()
    speeds = (1.0, 0.85)
    tasks = [(text, speed) for text in texts for speed in speeds]
    print(f"texts={len(texts)} tasks={len(tasks)}")

    if not api_available(TTS_CLIENT_URL, timeout=3):
        print("ttsclient server not running — start it first.")
        return 1

    skipped = sum(1 for text, speed in tasks if voice_cache_path(text, speed).is_file())
    print(f"already cached: {skipped}")
    done, failed = 0, []
    for text, speed in tasks:
        path, ok = generate_one(text, speed)
        done += 1
        if not ok:
            failed.append((text, speed))
        if done % 25 == 0 or not ok:
            print(f"[{done}/{len(tasks)}] {'OK' if ok else 'FAIL'} speed={speed} {text!r}")
    print(f"done={done} failed={len(failed)}")
    for text, speed in failed:
        print(f"  FAIL speed={speed} {text!r}")
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
