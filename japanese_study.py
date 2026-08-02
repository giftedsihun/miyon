import ctypes
import csv
import json
import os
import shutil
import sqlite3
import subprocess
import threading
import tkinter as tk
import tempfile
import urllib.error
import urllib.request
import winsound
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from content import (CONTENT, HIRAGANA, HIRAGANA_EXTRA, HIRAGANA_ROWS, KANA_NOTES,
                        KATAKANA, KATAKANA_EXTRA, KATAKANA_ROWS, KOREAN_ROWS, LEVELS, ROMAJI_ROWS)
from study_logic import card_study_prompt, study_plan_pace, tts_recovery_steps as _tts_recovery_steps
from quiz_logic import (catalog_question_pool as _catalog_question_pool,
                        comprehension_study_tip as _comprehension_study_tip,
                        mock_exam_comparison as _mock_exam_comparison,
                        personal_word_question_pool as _personal_word_question_pool,
                         question_pool as _question_pool)
from progress_logic import (achievement_milestones, answer_explanation, catalog_resume_index,
                            content_levels_from_ids, course_progress_insight, daily_course_items,
                            daily_reminder, diagnostic_insights, diagnostic_recommendation,
                            error_cause_recommendation, error_cause_summary, mock_exam_insights,
                            mock_section, practice_progress_summary, quiz_trend_insight,
                            review_workload_insight, unique_questions_by_id, weakness_recommendation,
                             weekly_activity_summary)
from quiz_session import QuizSession
from ui_quiz import build_quiz_screen, render_question, show_quality_controls
from ui_catalog import render_catalog
from ui_practice import (render_dictation as _render_dictation,
                         render_kana_writing as _render_kana_writing,
                         render_kanji_writing as _render_kanji_writing,
                         render_sentence_building as _render_sentence_building,
                         render_stroke_steps as _render_stroke_steps)
from ui_dialogs import (show_backup_restore as _show_backup_restore,
                        show_display_settings as _show_display_settings,
                        show_theme_settings as _show_theme_settings,
                        show_voice_settings as _show_voice_settings)
from ui_screens import (render_favorites_library, render_home, render_learning,
                        render_kana_menu, render_kana_notes, render_level_select,
                        render_personal_words, render_review, render_stats, render_study_plan)
from app_info import APP_VERSION, RELEASE_NAME
from learning_services import (DEFAULT_MOCK_EXAM, DEFAULT_REVIEW_LIMIT, DEFAULT_STUDY_PLAN,
                               DEFAULT_TEXT_SCALE, THEME_LABELS, card_learning_state,
                               catalog_progress_summary, content_practice_type, display_scale,
                               error_cause, error_cause_learning_path, favorite_card_details,
                               level_mastery_summary, mock_exam_time_summary, normalized_mock_exam,
                               normalized_review_limit, normalized_study_plan, normalized_text_scale,
                               normalized_theme, personal_word_import_rows)
from storage import BACKUP_DIRECTORY, DB_PATH, SRS_DAYS, Database
from tts_service import (ZUNDAMON_API_DIRECTORY, ZUNDAMON_DIRECTORY, ZUNDAMON_GPT_MODEL,
                         ZUNDAMON_MODEL_FILES, ZUNDAMON_PYTHON_PACKAGES,
                         ZUNDAMON_READY_CONTENT, ZUNDAMON_READY_MARKER,
                          ZUNDAMON_REFERENCE_AUDIO, ZUNDAMON_REFERENCE_SOURCE,
                          ZUNDAMON_REFERENCE_SHA256, ZUNDAMON_REFERENCE_TEXT, ZUNDAMON_REPOSITORY,
                          ZUNDAMON_REVISION, ZUNDAMON_RUNTIME, ZUNDAMON_SERVER_LOG,
                          ZUNDAMON_SETUP_LOG, ZUNDAMON_SOVITS_MODEL, ZUNDAMON_URL,
                           BUNDLED_ZUNDAMON_DIRECTORY, api_available, download_file, file_ready, installation_summary,
                          endpoint_privacy_notice, missing_commands, prerequisite_error, run_command,
                          runtime_environment, runtime_python, server_command, ready, speak_windows_native,
                           TTS_CLIENT_DIRECTORY, TTS_CLIENT_RUNTIME, TTS_CLIENT_SERVER_LOG, TTS_CLIENT_URL,
                           ttsclient_generate_voice, ttsclient_ready, ttsclient_server_command, kana_speech_text,
                          cached_voice)

APP_TITLE = "하루 일본어"
DATA_DIR = Path(os.environ.get("HARU_DATA_DIR", Path.home() / ".haru_japanese"))
LEVEL_ORDER = ["초보", "문자", "N5", "N4", "N3", "N2", "N1"]


def _safe_int_value(variable, default):
    try:
        return int(variable.get())
    except (tk.TclError, ValueError):
        return default


def mock_exam_comparison(current_score, current_total, previous):
    return _mock_exam_comparison(current_score, current_total, previous)


QUIZ_MODE_LABELS = {
    "words": "단어", "kanji": "한자", "grammar": "문법", "reading": "독해",
    "listening": "청해", "sentence": "문장 만들기", "dictation": "받아쓰기",
    "favorites": "즐겨찾기", "mock": "모의고사", "mixed": "혼합", "kana": "문자",
    "review": "예정 복습", "weak": "오답 노트", "diagnostic": "진단", "retry": "오답 다시 풀기",
    "error-focus": "오답 원인 집중 연습",
    "personal-words": "나의 단어장",
}






def comprehension_study_tip(content_id, answer):
    return _comprehension_study_tip(content_id, answer)




def tts_diagnostic_summary(api_connected, ready, missing_commands):
    """Turn local TTS checks into an actionable, UI-safe diagnostic result."""
    missing_commands = tuple(missing_commands)
    if api_connected:
        return "ready", "연결됨: ずんだもん AI 서버가 응답합니다. 테스트 음성을 재생할 수 있어요."
    if ready:
        return "stopped", "AI 음성 파일은 준비됐어요. 서버 시작 또는 테스트 음성 재생을 눌러 보세요."
    if missing_commands:
        return "prerequisite", "AI 음성 준비 전 필요한 항목: " + ", ".join(missing_commands)
    return "setup", "AI 음성 설치가 아직 필요해요. 서버 시작을 누르면 필요한 파일을 준비합니다."


def tts_recovery_steps(api_connected, ready, missing_commands):
    """Keep the app-facing diagnostic signature while delegating pure recovery logic."""
    state, _ = tts_diagnostic_summary(api_connected, ready, missing_commands)
    return _tts_recovery_steps(state, missing_commands)


def enable_high_dpi():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass




class JapaneseStudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.base_tk_scaling = self.winfo_fpixels("1i") / 72.0
        self.tk.call("tk", "scaling", self.base_tk_scaling)
        self.title(APP_TITLE); self.geometry("1120x760"); self.minsize(720, 500); self.configure(bg="#f4f6f0")
        self.db = Database(); self.selected_level = self.db.get("level", "초보")
        self.apply_text_scale(self.db.get("text_scale_mode", "auto"), self.db.get("text_scale", DEFAULT_TEXT_SCALE))
        try:
            self.db.automatic_backup()
        except (OSError, sqlite3.Error):
            pass
        self.zundamon_start_lock = threading.Lock()
        self.zundamon_install_lock = threading.Lock()
        self.speech_lock = threading.Lock()
        self.zundamon_process = None
        self.speech_audio_path = None
        self.speech_generation = 0
        self.configure_styles(); self.show_home()
        self.after(250, self.show_first_run_guide)
        self.after(500, self.auto_start_zundamon)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.stop_speech()
        process = self.zundamon_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass
        self.destroy()

    def configure_styles(self):
        style = ttk.Style(self); style.theme_use("clam")
        theme = normalized_theme(self.db.get("color_theme", "standard"))
        accent, active, progress = ("#165b52", "#10463f", "#e17a55") if theme == "standard" else ("#003b5c", "#00263b", "#c74700")
        style.configure("TButton", font=("맑은 고딕", 10), padding=(13, 8), background="#ffffff")
        style.configure("Accent.TButton", font=("맑은 고딕", 10, "bold"), foreground="#ffffff", background=accent)
        style.map("Accent.TButton", background=[("active", active)])
        style.configure("TProgressbar", troughcolor="#e3e8df", background=progress, thickness=11)

    def text_scale(self):
        return normalized_text_scale(self.db.get("text_scale", DEFAULT_TEXT_SCALE))

    def apply_text_scale(self, mode="auto", value=DEFAULT_TEXT_SCALE):
        scale = display_scale(mode, value)
        self.tk.call("tk", "scaling", self.base_tk_scaling * scale / 100)
        return scale

    def clear(self):
        for widget in self.winfo_children(): widget.destroy()

    def header(self, active="홈"):
        bar = tk.Frame(self, bg="#165b52", height=68); bar.pack(fill="x")
        tk.Label(bar, text="하루 일본어", font=("맑은 고딕", 20, "bold"), fg="white", bg="#165b52").pack(side="left", padx=32, pady=16)
        tk.Label(bar, text=f"v{APP_VERSION}", font=("맑은 고딕", 8), fg="#d8e9e2", bg="#165b52").pack(side="left", padx=(0, 14))
        for label, command in (("홈", self.show_home), ("학습", self.show_learning), ("복습", self.show_review), ("통계", self.show_stats)):
            tk.Button(bar, text=label, command=command, relief="flat", cursor="hand2", font=("맑은 고딕", 10, "bold" if active == label else "normal"), fg="#ffe0ae" if active == label else "#d8e9e2", bg="#165b52", activebackground="#165b52", activeforeground="white").pack(side="left", padx=10)

    def page(self, active, title, subtitle):
        self.clear_quiz_shortcuts()
        self.clear(); self.header(active)
        self.title(f"{APP_TITLE} - {title}")
        outer = tk.Frame(self, bg="#f4f6f0"); outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg="#f4f6f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        main = tk.Frame(canvas, bg="#f4f6f0")
        window = canvas.create_window((0, 0), window=main, anchor="nw")
        def resize_content(event): canvas.configure(scrollregion=canvas.bbox("all"))
        def resize_canvas(event): canvas.itemconfigure(window, width=event.width)
        main.bind("<Configure>", resize_content); canvas.bind("<Configure>", resize_canvas)
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))

        def key_scroll(event):
            focused = self.focus_get()
            if focused is not None and focused.winfo_class() in ("Entry", "Text", "TEntry", "TCombobox", "TSpinbox", "Scale", "TScale"):
                return
            step = {"Prior": -3, "Next": 3, "Home": -9999, "End": 9999, "Up": -1, "Down": 1}.get(event.keysym)
            if step:
                canvas.yview_scroll(step, "units")
            if event.keysym in ("Prior", "Next", "Home", "End"):
                return "break"

        for keysym in ("Prior", "Next", "Home", "End", "Up", "Down"):
            canvas.bind_all(f"<{keysym}>", key_scroll)

        content = tk.Frame(main, bg="#f4f6f0"); content.pack(fill="both", expand=True, padx=58, pady=32)
        tk.Label(content, text=title, font=("맑은 고딕", 27, "bold"), fg="#173c35", bg="#f4f6f0").pack(anchor="w")
        tk.Label(content, text=subtitle, font=("맑은 고딕", 11), fg="#66776f", bg="#f4f6f0").pack(anchor="w", pady=(6, 22))
        return content

    def card(self, parent):
        return tk.Frame(parent, bg="white", highlightbackground="#dde5dc", highlightthickness=1)

    def show_first_run_guide(self):
        if self.db.get("first_run_version") == APP_VERSION:
            return
        dialog = tk.Toplevel(self); dialog.title("하루 일본어 시작하기"); dialog.configure(bg="white")
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        tk.Label(dialog, text="하루 일본어에 오신 것을 환영해요", font=("맑은 고딕", 17, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=30, pady=(26, 7))
        tk.Label(dialog, text=("1. 과정 선택 또는 12문항 진단으로 시작점을 고르세요.\n"
                               "2. 오늘의 단어·문법을 살펴본 뒤 짧은 퀴즈를 풀어 보세요.\n"
                               "3. AI 음성은 선택 기능이며, 나중에 홈의 설정에서 준비할 수 있어요.\n\n"
                               "학습 기록은 이 PC에 저장되며 통계 화면에서 내보낼 수 있습니다."),
                 font=("맑은 고딕", 10), fg="#66776f", bg="white", justify="left", wraplength=470).pack(anchor="w", padx=30)
        def close():
            self.db.set("first_run_version", APP_VERSION)
            dialog.destroy()
        ttk.Button(dialog, text="학습 시작", style="Accent.TButton", command=close).pack(anchor="e", padx=30, pady=25)

    def show_display_settings(self):
        return _show_display_settings(self)

    def show_theme_settings(self):
        return _show_theme_settings(self)

    def current_content(self):
        return CONTENT.get(self.selected_level, CONTENT["N5"])

    def study_plan(self):
        return normalized_study_plan(self.db.get("study_plan", DEFAULT_STUDY_PLAN), self.selected_level)

    def course_day(self):
        return max(1, int(self.db.get("course_day", 1)))

    def study_recommendation(self):
        recommendation = error_cause_recommendation(self.db.error_cause_results())
        if recommendation:
            _, label, correct, wrong = recommendation
            total = correct + wrong
            return f"{label}에서 {wrong}번 틀렸고 정확도는 {round(correct * 100 / total)}%예요. 원인별 집중 연습으로 바로 확인해 보세요."
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

    def start_recommended_practice(self):
        recommendation = error_cause_recommendation(self.db.error_cause_results())
        if not recommendation:
            self.show_learning()
            return
        cause, label, _, _ = recommendation
        self.start_error_cause_quiz(cause, label)

    def show_home(self):
        return render_home(self)

    def change_daily_goal(self):
        dialog = tk.Toplevel(self); dialog.title("오늘의 목표"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        tk.Label(dialog, text="하루 학습량", font=("맑은 고딕", 14, "bold"), fg="#173c35", bg="white").pack(padx=32, pady=(24, 10))
        tk.Label(dialog, text="하루에 풀 문항 수", font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=32)
        value = tk.IntVar(value=self.db.get("daily_goal", 20))
        ttk.Spinbox(dialog, from_=5, to=100, increment=5, textvariable=value, width=8, justify="center", font=("맑은 고딕", 12)).pack(pady=4)
        tk.Label(dialog, text="한 번에 진행할 복습 상한", font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=32, pady=(10, 0))
        review_limit = tk.IntVar(value=normalized_review_limit(self.db.get("review_limit", DEFAULT_REVIEW_LIMIT)))
        ttk.Spinbox(dialog, from_=5, to=50, increment=5, textvariable=review_limit, width=8, justify="center", font=("맑은 고딕", 12)).pack(pady=4)
        def save():
            self.db.set("daily_goal", max(5, min(100, _safe_int_value(value, self.db.get("daily_goal", 20)))))
            self.db.set("review_limit", normalized_review_limit(_safe_int_value(review_limit, self.db.get("review_limit", DEFAULT_REVIEW_LIMIT))))
            dialog.destroy(); self.show_home()
        ttk.Button(dialog, text="저장", style="Accent.TButton", command=save).pack(pady=(14, 24))

    def show_study_plan(self):
        return render_study_plan(self)

    def edit_study_plan(self):
        dialog = tk.Toplevel(self); dialog.title("학습 계획 설정"); dialog.configure(bg="white"); dialog.transient(self); dialog.grab_set()
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        current = self.study_plan()
        tk.Label(dialog, text="목표 과정", font=("맑은 고딕", 11, "bold"), bg="white").pack(padx=28, pady=(22, 3), anchor="w")
        level = tk.StringVar(value=current.get("level", "N5")); ttk.Combobox(dialog, textvariable=level, values=("N5", "N4", "N3", "N2", "N1"), state="readonly", width=12).pack(padx=28)
        tk.Label(dialog, text="목표 기간(일)", font=("맑은 고딕", 11, "bold"), bg="white").pack(padx=28, pady=(14, 3), anchor="w")
        days = tk.IntVar(value=current.get("days", 30)); ttk.Spinbox(dialog, from_=7, to=365, textvariable=days, width=10).pack(padx=28, anchor="w")
        tk.Label(dialog, text="하루 새 단어 수", font=("맑은 고딕", 11, "bold"), bg="white").pack(padx=28, pady=(14, 3), anchor="w")
        daily_words = tk.IntVar(value=current.get("daily_words", 10)); ttk.Spinbox(dialog, from_=3, to=50, textvariable=daily_words, width=10).pack(padx=28, anchor="w")
        def save():
            plan = normalized_study_plan({"level": level.get(), "days": _safe_int_value(days, current.get("days", 30)), "daily_words": _safe_int_value(daily_words, current.get("daily_words", 10))})
            if plan["level"] != current["level"]:
                self.db.set("course_day", 1)
                self.db.set("course_last_completed", None)
            self.db.set("study_plan", plan); dialog.destroy(); self.show_study_plan()
        ttk.Button(dialog, text="저장", style="Accent.TButton", command=save).pack(padx=28, pady=24, anchor="e")

    def zundamon_backend(self):
        return str(self.db.get("zundamon_backend", "ttsclient"))

    def zundamon_api_available(self, url, timeout=5):
        return api_available(url, timeout)

    def zundamon_runtime_python(self):
        return runtime_python()

    def zundamon_ready(self):
        if self.zundamon_backend() == "ttsclient":
            return ttsclient_ready()
        return ready()

    def zundamon_installation_summary(self):
        return installation_summary()

    @staticmethod
    def zundamon_file_ready(path):
        return file_ready(path)

    def zundamon_prerequisite_error(self):
        return prerequisite_error()

    @staticmethod
    def zundamon_missing_commands():
        return missing_commands()

    def zundamon_status(self):
        if self.zundamon_backend() == "ttsclient":
            api_connected = self.zundamon_api_available(TTS_CLIENT_URL, timeout=2)
            state, message = tts_diagnostic_summary(api_connected, self.zundamon_ready(), ())
            return message, "#165b52" if state == "ready" else "#b95140" if state == "prerequisite" else "#66776f"
        api_connected = self.zundamon_api_available(str(self.db.get("zundamon_url", ZUNDAMON_URL)), timeout=2)
        state, message = tts_diagnostic_summary(api_connected, self.zundamon_ready(), self.zundamon_missing_commands())
        return message, "#165b52" if state == "ready" else "#b95140" if state == "prerequisite" else "#66776f"

    def zundamon_command(self):
        if self.zundamon_backend() == "ttsclient":
            return ttsclient_server_command()
        return server_command()

    def run_zundamon_command(self, arguments, log_file, timeout, set_status):
        return run_command(arguments, log_file, timeout, set_status)

    def download_zundamon_file(self, source, destination, expected_sha256=None):
        return download_file(source, destination, expected_sha256)

    def auto_start_zundamon(self):
        if self.db.get("zundamon_auto_start", True):
            self.start_zundamon_api(getattr(self, "voice_status", None))
        elif hasattr(self, "voice_status") and self.voice_status.winfo_exists():
            message, color = self.zundamon_status()
            self.voice_status.config(text=message, fg=color)

    def start_zundamon_api(self, status=None):
        url = str(self.db.get("zundamon_url", ZUNDAMON_URL)).strip().rstrip("/")
        backend = self.zundamon_backend()

        def set_status(message, color):
            if status:
                self.after(0, lambda: status.winfo_exists() and status.config(text=message, fg=color))

        def run():
            if not self.zundamon_start_lock.acquire(blocking=False):
                set_status("ずんだもん AI 서버를 이미 시작하고 있어요...", "#66776f")
                return
            try:
                if backend == "ttsclient":
                    self._start_ttsclient_server(set_status, url=TTS_CLIENT_URL)
                    return
                self._start_gpt_sovits_server(set_status, url)
            except OSError as error:
                set_status(f"AI 서버를 시작할 수 없어요. ({error})", "#b95140")
            finally:
                self.zundamon_start_lock.release()

        threading.Thread(target=run, daemon=True).start()

    def _start_ttsclient_server(self, set_status, url):
        """Launch the bundled ttsclient REST API server on port 19000."""
        if self.zundamon_api_available(url):
            set_status("연결됨: ずんだもん AI 서버가 이미 실행 중이에요.", "#165b52")
            return
        if not ttsclient_ready():
            set_status("ttsclient 실행 파일이 준비되지 않았어요. 배포 폴더의 ttsclient를 확인해 주세요.", "#b95140")
            return
        set_status("ずんだもん AI 서버를 시작하고 있어요. 모델을 읽는 동안 잠시 기다려 주세요...", "#66776f")
        with open(TTS_CLIENT_SERVER_LOG, "a", encoding="utf-8") as server_log:
            self.zundamon_process = subprocess.Popen(self.zundamon_command(), cwd=str(TTS_CLIENT_DIRECTORY),
                                                     stdout=server_log, stderr=subprocess.STDOUT,
                                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(600):
            if self.zundamon_api_available(url, timeout=2):
                set_status("시작 완료: ずんだもん AI 음성을 사용할 수 있어요.", "#165b52")
                return
            if self.zundamon_process.poll() is not None:
                set_status("AI 서버가 바로 종료됐어요. 오류는 " + str(TTS_CLIENT_SERVER_LOG) + "에서 확인할 수 있어요.", "#b95140")
                return
            threading.Event().wait(1)
        set_status("서버 시작 시간이 초과됐어요. 로그를 확인해 주세요: " + str(TTS_CLIENT_SERVER_LOG), "#b95140")

    def _start_gpt_sovits_server(self, set_status, url):
        if self.zundamon_api_available(url):
            set_status("연결됨: ずんだもん AI 서버가 이미 실행 중이에요.", "#165b52")
            return
        if not self.zundamon_ready():
            if not self.install_zundamon_api(set_status):
                return
        set_status("ずんだもん AI 서버를 시작하고 있어요. 모델을 읽는 동안 잠시 기다려 주세요...", "#66776f")
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        with open(ZUNDAMON_SERVER_LOG, "a", encoding="utf-8") as server_log:
            self.zundamon_process = subprocess.Popen(self.zundamon_command(), cwd=ZUNDAMON_API_DIRECTORY,
                                                     stdout=server_log, stderr=subprocess.STDOUT,
                                                     creationflags=flags, env=runtime_environment(os.environ))
        for _ in range(180):
            if self.zundamon_api_available(url, timeout=2):
                set_status("시작 완료: ずんだもん AI 음성을 사용할 수 있어요.", "#165b52")
                return
            if self.zundamon_process.poll() is not None:
                set_status("AI 서버가 바로 종료됐어요. 오류는 " + str(ZUNDAMON_SERVER_LOG) + "에서 확인할 수 있어요.", "#b95140")
                return
            threading.Event().wait(1)
        set_status("서버 시작 시간이 초과됐어요. 로그를 확인해 주세요: " + str(ZUNDAMON_SERVER_LOG), "#b95140")

    def install_zundamon_api(self, set_status):
        """Prepare the compatible runtime, models, and local Zundamon API on first use."""
        if not self.zundamon_install_lock.acquire(blocking=False):
            set_status("ずんだもん AI 파일을 이미 내려받고 있어요...", "#66776f")
            return False
        try:
            if self.zundamon_ready():
                return True
            if BUNDLED_ZUNDAMON_DIRECTORY:
                set_status("포함된 AI 음성 파일이 불완전합니다. 배포 폴더의 zundamon-gpt-sovits-api를 다시 받아 주세요.", "#b95140")
                return False
            prerequisite_error = self.zundamon_prerequisite_error()
            if prerequisite_error:
                set_status(prerequisite_error, "#b95140")
                return False
            if not (ZUNDAMON_API_DIRECTORY / "api.py").is_file():
                if ZUNDAMON_DIRECTORY.exists():
                    set_status("AI 프로젝트 복구를 위해 다시 내려받고 있어요...", "#66776f")
                    shutil.rmtree(ZUNDAMON_DIRECTORY)
                set_status("ずんだもん AI 프로젝트를 처음 내려받고 있어요...", "#66776f")
                if not self.run_zundamon_command(
                    ["git", "clone", "--recursive", ZUNDAMON_REPOSITORY, str(ZUNDAMON_DIRECTORY)],
                    ZUNDAMON_SETUP_LOG, 900, set_status,
                ) or not self.run_zundamon_command(
                    ["git", "-C", str(ZUNDAMON_DIRECTORY), "checkout", "--detach", ZUNDAMON_REVISION],
                    ZUNDAMON_SETUP_LOG, 300, set_status,
                ) or not self.run_zundamon_command(
                    ["git", "-C", str(ZUNDAMON_DIRECTORY), "submodule", "update", "--init", "--recursive"],
                    ZUNDAMON_SETUP_LOG, 900, set_status,
                ) or not (ZUNDAMON_API_DIRECTORY / "api.py").is_file():
                    return False
            runtime_python = self.zundamon_runtime_python()
            if not runtime_python.is_file():
                set_status("AI 음성용 Python 3.9 환경을 준비하고 있어요. 처음 한 번만 필요합니다...", "#66776f")
                if not self.run_zundamon_command(
                    ["uv", "venv", "--python", "3.9", str(ZUNDAMON_RUNTIME)], ZUNDAMON_SETUP_LOG, 900, set_status,
                ):
                    return False
            if not ZUNDAMON_READY_MARKER.is_file():
                set_status("AI 음성 실행 패키지를 설치하고 있어요. 몇 분 걸릴 수 있어요...", "#66776f")
                if not self.run_zundamon_command(
                    ["uv", "pip", "install", "--python", str(runtime_python), "torch==2.1.2+cpu", "torchaudio==2.1.2+cpu", "--index-url", "https://download.pytorch.org/whl/cpu"],
                    ZUNDAMON_SETUP_LOG, 1800, set_status,
                ) or not self.run_zundamon_command(
                    ["uv", "pip", "install", "--python", str(runtime_python), "setuptools<81", "torch==2.1.2+cpu", "torchaudio==2.1.2+cpu", *ZUNDAMON_PYTHON_PACKAGES], ZUNDAMON_SETUP_LOG, 1800, set_status,
                ):
                    return False
            # Recreate compatibility files on later launches too, in case a package update restored them.
            # The upstream source imports extensions that are impractical to compile on a bare Windows PC.
            # For this Japanese-only app, these pure-Python compatibility modules provide the used API.
            compatibility_file = ZUNDAMON_RUNTIME / "Lib" / "site-packages" / "jieba_fast.py"
            compatibility_file.write_text(
                "import sys\nimport jieba as _jieba\nfrom jieba import *\nsys.modules[__name__] = _jieba\n",
                encoding="ascii",
            )
            shutil.rmtree(ZUNDAMON_RUNTIME / "Lib" / "site-packages" / "LangSegment", ignore_errors=True)
            langsegment_file = ZUNDAMON_RUNTIME / "Lib" / "site-packages" / "LangSegment.py"
            langsegment_file.write_text(
                "filters = None\n"
                "def setfilters(value):\n"
                "    global filters\n"
                "    filters = value\n"
                "def getTexts(text):\n"
                "    language = filters[0] if filters and len(filters) == 1 else 'ja'\n"
                "    return [{'text': text, 'lang': language}]\n"
                "class LangSegment:\n"
                "    setfilters = staticmethod(setfilters)\n"
                "    getTexts = staticmethod(getTexts)\n",
                encoding="ascii",
            )
            for index, (source, destination, expected_sha256) in enumerate(ZUNDAMON_MODEL_FILES, start=1):
                if self.zundamon_file_ready(destination):
                    continue
                set_status(f"AI 음성 모델을 내려받고 있어요 ({index}/{len(ZUNDAMON_MODEL_FILES)})...", "#66776f")
                try:
                    self.download_zundamon_file(source, destination, expected_sha256)
                except (OSError, urllib.error.URLError) as error:
                    set_status(f"AI 모델 다운로드에 실패했어요. 인터넷 연결을 확인해 주세요. ({error})", "#b95140")
                    return False
            if not self.zundamon_file_ready(ZUNDAMON_REFERENCE_AUDIO):
                set_status("ずんだもん 기준 음성을 내려받고 있어요...", "#66776f")
                try:
                    self.download_zundamon_file(ZUNDAMON_REFERENCE_SOURCE, ZUNDAMON_REFERENCE_AUDIO, ZUNDAMON_REFERENCE_SHA256)
                except (OSError, urllib.error.URLError) as error:
                    set_status(f"기준 음성 다운로드에 실패했어요. 인터넷 연결을 확인해 주세요. ({error})", "#b95140")
                    return False
            try:
                self.after(0, lambda: self.db.set("zundamon_api_directory", str(ZUNDAMON_API_DIRECTORY)))
                self.after(0, lambda: self.db.set("zundamon_auto_start", True))
            except RuntimeError:
                pass
            ZUNDAMON_READY_MARKER.write_text(ZUNDAMON_READY_CONTENT, encoding="ascii")
            set_status("ずんだもん AI 음성 준비가 끝났어요. 서버를 시작합니다...", "#165b52")
            return True
        except (OSError, subprocess.TimeoutExpired) as error:
            set_status(f"AI 파일을 내려받을 수 없어요. Git과 인터넷 연결을 확인해 주세요. ({error})", "#b95140")
            return False
        finally:
            self.zundamon_install_lock.release()


    def show_level_select(self):
        return render_level_select(self, LEVELS)

    def select_level(self, level):
        self.selected_level = level; self.db.set("level", level); self.show_home()

    def show_learning(self):
        return render_learning(self)

    def start_practice_quiz(self, mode, pool):
        completed = self.db.completed_practice_ids(f"{self.selected_level}:{mode}:")
        remaining = [item for item in pool if item[3] not in completed]
        if not remaining and pool:
            if not messagebox.askyesno("모든 연습 완료", f"{mode == 'reading' and '독해' or '청해'} 문제를 모두 완료했어요. 처음부터 다시 풀까요?"):
                return
            remaining = pool
        self.start_quiz(mode=mode, pool=remaining)

    def complete_lesson(self):
        advanced, next_day = self.db.complete_course_day()
        if advanced:
            messagebox.showinfo("오늘의 학습", f"Day {next_day - 1:03d} 학습을 기록했어요. 내일은 Day {next_day:03d}부터 이어가세요.")
        else:
            messagebox.showinfo("오늘의 학습", "오늘의 코스는 이미 완료했어요. 내일 다음 Day가 열립니다.")
        self.show_learning()

    def show_kana_menu(self):
        return render_kana_menu(self)

    def show_kana(self, script):
        hira = script == "hiragana"; title = "히라가나" if hira else "가타카나"; accent = "#df7654" if hira else "#165b52"
        rows, extras = (HIRAGANA_ROWS, HIRAGANA_EXTRA) if hira else (KATAKANA_ROWS, KATAKANA_EXTRA)
        main = self.page("학습", title, "한 줄씩 소리 내어 읽고, 글자를 누르면 바로 ずんだもん 발음이 재생됩니다.")
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
        # A one-line button height keeps all ten kana rows visible on smaller windows.
        tk.Button(parent, text=f"{char}\n{reading}", command=lambda: self.speak_japanese(char), relief="flat", cursor="hand2", font=("맑은 고딕", 15, "bold"), fg=accent, bg="#f5f8f3", activebackground="#fff2e6", width=7, height=1).grid(row=row, column=column, sticky="nsew", padx=3, pady=3)

    def show_kana_writing(self, script):
        return _render_kana_writing(self, script)

    def show_kana_notes(self):
        return render_kana_notes(self, KANA_NOTES)

    def show_daily_words(self):
        plan, items, _ = daily_course_items(self.study_plan(), self.course_day())
        self.show_catalog("words", items, f"{plan['level']} Day {self.course_day():03d} · 오늘의 새 단어 {len(items)}개를 예문과 함께 익혀 보세요.", plan["level"])

    def show_daily_grammar(self):
        plan, _, grammar = daily_course_items(self.study_plan(), self.course_day())
        self.show_catalog("grammar", [grammar], f"{plan['level']} Day {self.course_day():03d} · 오늘의 핵심 문법을 예문과 함께 익혀 보세요.", plan["level"])

    def show_personal_words(self):
        return render_personal_words(self)

    def show_favorites_library(self):
        return render_favorites_library(self)

    def show_catalog(self, category, items=None, subtitle=None, content_level=None):
        return render_catalog(self, category, items, subtitle, content_level)

    def catalog_question_pool(self, category, level, items):
        """Build a quiz from the cards currently visible in a catalog view."""
        return _catalog_question_pool(category, level, items)

    def speak_japanese(self, text, status=None, rate=0):
        self.stop_speech()
        try:
            speed = float(self.db.get("zundamon_speed", 1.0)) * (1 + rate / 20)
        except (TypeError, ValueError):
            speed = 1.0
        cached = cached_voice(text, max(0.5, min(2.0, speed)))
        if cached:
            try:
                winsound.PlaySound(str(cached), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except RuntimeError:
                pass
            if status:
                self.after(0, lambda: status.winfo_exists() and status.config(text="사전 생성된 ずんだもん 음성으로 재생 중이에요.", fg="#165b52"))
            return
        self.speak_with_zundamon(text, status, rate)

    def speak_with_zundamon(self, text, status=None, rate=0):
        """Request WAV audio from the local Zundamon voice server (ttsclient or GPT-SoVITS API)."""
        if self.zundamon_backend() == "ttsclient":
            self._speak_with_ttsclient(text, status, rate)
            return
        self._speak_with_gpt_sovits(text, status, rate)

    def _speak_with_ttsclient(self, text, status=None, rate=0):
        url = TTS_CLIENT_URL
        try:
            speed = float(self.db.get("zundamon_speed", 1.0)) * (1 + rate / 20)
        except (TypeError, ValueError):
            if status: status.config(text="AI 음성 설정 값이 올바르지 않습니다. 홈의 AI 음성 설정을 확인해 주세요.", fg="#b95140")
            return
        if status: status.config(text="ずんだもん AI 서버와 음성을 준비하고 있어요...", fg="#66776f")
        def run():
            with self.speech_lock:
                self.speech_generation += 1
                generation = self.speech_generation
            try:
                if not self.zundamon_api_available(url, timeout=2):
                    if ttsclient_ready():
                        def server_status(message, color):
                            if status: self.after(0, lambda: status.config(text=message, fg=color) if status.winfo_exists() else None)
                        if self.zundamon_start_lock.acquire(blocking=False):
                            try:
                                self._start_ttsclient_server(server_status, url=TTS_CLIENT_URL)
                            finally:
                                self.zundamon_start_lock.release()
                        for _ in range(600):
                            if self.zundamon_api_available(url, timeout=2):
                                break
                            threading.Event().wait(1)
                        else:
                            raise OSError("AI 서버 준비 시간이 초과됐습니다.")
                    else:
                        if status: self.after(0, lambda: status.config(text="Windows 내장 음성으로 재생 중이에요.", fg="#165b52") if status.winfo_exists() else None)
                        speak_windows_native(text, rate)
                        return
                if status: self.after(0, lambda: status.winfo_exists() and status.config(text="ずんだもん AI 음성이 발음을 만들고 있어요...", fg="#66776f"))
                audio = ttsclient_generate_voice(text, max(0.5, min(2.0, speed)))
                if not audio.startswith(b"RIFF"):
                    raise OSError("ずんだもん API가 WAV 오디오를 반환하지 않았습니다.")
                path = tempfile.NamedTemporaryFile(prefix="haru_japanese_", suffix=".wav", delete=False).name
                with open(path, "wb") as audio_file: audio_file.write(audio)
                if not self._set_speech_audio_path(path, generation):
                    try:
                        Path(path).unlink(missing_ok=True)
                    except OSError:
                        pass
                    return
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.after(int(max(1, len(audio) / 32000) * 1000) + 1000, lambda p=path, g=generation: self._cleanup_played_speech(p, g))
                if status: self.after(0, lambda: status.config(text="ずんだもん AI 음성으로 재생 중이에요.", fg="#165b52"))
            except Exception:
                if self._speech_is_current(generation):
                    if status: self.after(0, lambda: status.config(text="Windows 내장 음성으로 재생 중이에요.", fg="#165b52") if status and status.winfo_exists() else None)
                    speak_windows_native(text, rate)
        threading.Thread(target=run, daemon=True).start()

    def _speak_with_gpt_sovits(self, text, status=None, rate=0):
        """Request WAV audio from the user-run Zundamon GPT-SoVITS API server."""
        url = str(self.db.get("zundamon_url", ZUNDAMON_URL)).rstrip("/")
        try:
            speed = float(self.db.get("zundamon_speed", 1.0)) * (1 + rate / 20)
        except (TypeError, ValueError):
            if status: status.config(text="AI 음성 설정 값이 올바르지 않습니다. 홈의 AI 음성 설정을 확인해 주세요.", fg="#b95140")
            return
        payload = json.dumps({
            "text": kana_speech_text(text), "text_language": "ja", "speed": max(0.5, min(2.0, speed)),
        }).encode("utf-8")
        if status: status.config(text="ずんだもん AI 서버와 음성을 준비하고 있어요...", fg="#66776f")
        def run():
            with self.speech_lock:
                self.speech_generation += 1
                generation = self.speech_generation
            try:
                if not self.zundamon_api_available(url, timeout=2):
                    if ready():
                        def kick_off():
                            try:
                                self.start_zundamon_api(status)
                            except Exception:
                                pass
                        try:
                            self.after(0, kick_off)
                        except RuntimeError:
                            pass
                        for _ in range(180):
                            if self.zundamon_api_available(url, timeout=2):
                                break
                            threading.Event().wait(1)
                        else:
                            raise OSError("AI 서버 준비 시간이 초과됐습니다.")
                    else:
                        if status: self.after(0, lambda: status.config(text="Windows 내장 음성으로 재생 중이에요.", fg="#165b52") if status.winfo_exists() else None)
                        speak_windows_native(text, rate)
                        return
                if status: self.after(0, lambda: status.winfo_exists() and status.config(text="ずんだもん AI 음성이 발음을 만들고 있어요...", fg="#66776f"))
                request = urllib.request.Request(url + "/", data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=90) as response:
                    audio = response.read()
                if not audio.startswith(b"RIFF"):
                    raise OSError("ずんだもん API가 WAV 오디오를 반환하지 않았습니다.")
                path = tempfile.NamedTemporaryFile(prefix="haru_japanese_", suffix=".wav", delete=False).name
                with open(path, "wb") as audio_file: audio_file.write(audio)
                if not self._set_speech_audio_path(path, generation):
                    try:
                        Path(path).unlink(missing_ok=True)
                    except OSError:
                        pass
                    return
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.after(int(max(1, len(audio) / 32000) * 1000) + 1000, lambda p=path, g=generation: self._cleanup_played_speech(p, g))
                if status: self.after(0, lambda: status.config(text="ずんだもん AI 음성으로 재생 중이에요.", fg="#165b52"))
            except Exception:
                if self._speech_is_current(generation):
                    if status: self.after(0, lambda: status.config(text="Windows 내장 음성으로 재생 중이에요.", fg="#165b52") if status and status.winfo_exists() else None)
                    speak_windows_native(text, rate)
        threading.Thread(target=run, daemon=True).start()


    def _set_speech_audio_path(self, path, generation):
        """Register this speech's temp file if it is still the current generation."""
        with self.speech_lock:
            if generation != self.speech_generation:
                return False
            previous = self.speech_audio_path
            self.speech_audio_path = path
        if previous and previous != path:
            try:
                Path(previous).unlink(missing_ok=True)
            except OSError:
                pass
        return True

    def _speech_is_current(self, generation):
        with self.speech_lock:
            return generation == self.speech_generation

    def _cleanup_played_speech(self, path, generation):
        with self.speech_lock:
            if generation == self.speech_generation and self.speech_audio_path == path:
                self.speech_audio_path = None
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass

    def stop_speech(self):
        winsound.PlaySound(None, winsound.SND_PURGE)
        with self.speech_lock:
            self.speech_generation += 1
            path = self.speech_audio_path
            self.speech_audio_path = None
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass

    def show_kanji_writing(self):
        return _render_kanji_writing(self)

    def show_stroke_steps(self, char):
        return _render_stroke_steps(self, char)

    def show_sentence_building(self):
        return _render_sentence_building(self)

    def show_dictation(self):
        return _render_dictation(self)

    def start_diagnostic(self):
        self.start_quiz(mode="diagnostic", title="12문항 실력 진단")

    def start_mock_exam(self):
        settings = normalized_mock_exam(self.db.get("mock_exam", DEFAULT_MOCK_EXAM))
        dialog = tk.Toplevel(self); dialog.title("시간 제한 모의고사"); dialog.configure(bg="white")
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        tk.Label(dialog, text="JLPT 스타일 모의고사", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=28, pady=(24, 5))
        tk.Label(dialog, text="공식 시험 점수나 합격을 판정하지 않는 학습용 연습입니다. 시작하면 제한 시간이 바로 흐릅니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=440, justify="left").pack(anchor="w", padx=28)
        questions = tk.IntVar(value=settings["questions"]); minutes = tk.IntVar(value=settings["minutes"])
        for label, value, minimum, maximum in (("문항 수", questions, 12, 40), ("제한 시간(분)", minutes, 5, 90)):
            row = tk.Frame(dialog, bg="white"); row.pack(fill="x", padx=28, pady=(14, 0))
            tk.Label(row, text=label, font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(side="left")
            ttk.Spinbox(row, from_=minimum, to=maximum, increment=1, textvariable=value, width=7, justify="center").pack(side="right")
        def start():
            chosen = normalized_mock_exam({"questions": _safe_int_value(questions, settings["questions"]), "minutes": _safe_int_value(minutes, settings["minutes"])})
            self.db.set("mock_exam", chosen); dialog.destroy()
            self.start_quiz(mode="mock", title="시간 제한 모의고사", quiz_limit=chosen["questions"], time_limit=chosen["minutes"] * 60)
        ttk.Button(dialog, text="시험 시작", style="Accent.TButton", command=start).pack(anchor="e", padx=28, pady=24)

    def start_review_session(self):
        limit = normalized_review_limit(self.db.get("review_limit", DEFAULT_REVIEW_LIMIT))
        ids = {row[0] for row in self.db.review_session_items(limit)}
        pool = [question for question in self.question_pool("review") if question[3] in ids]
        if not pool:
            messagebox.showinfo("복습", "지금 예정된 복습이 없어요. 새 학습을 진행해 보세요.")
            return
        self.start_quiz(mode="review", title=f"오늘의 복습 · 최대 {limit}개", pool=pool)

    def start_error_cause_quiz(self, cause, label=None):
        ids = self.db.error_cause_item_ids(cause)
        levels = content_levels_from_ids(ids)
        pool = (
            self.question_pool("mixed", content_levels=levels) + self.question_pool("kana") +
            self.question_pool("reading", content_levels=levels) + self.question_pool("listening", content_levels=levels) +
            self.question_pool("dictation", content_levels=levels)
        )
        pool = [question for question in pool if question[3] in ids]
        if not pool:
            messagebox.showinfo("오답 원인 집중 연습", "이 원인에 맞는 문제를 아직 만들 수 없어요. 오답 노트에서 다시 확인해 보세요.")
            return
        title = f"오답 원인 집중 연습 · {label or ERROR_CAUSE_LABELS.get(cause, cause)}"
        self.start_quiz(mode="error-focus", title=title, pool=pool)

    def show_error_cause_path(self, cause, label=None):
        label = label or ERROR_CAUSE_LABELS.get(cause, cause)
        guidance, lesson = error_cause_learning_path(cause)
        dialog = tk.Toplevel(self); dialog.title("오답 회복 경로"); dialog.configure(bg="white")
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        tk.Label(dialog, text=f"{label} 회복 경로", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=28, pady=(24, 5))
        tk.Label(dialog, text=guidance, font=("맑은 고딕", 11), fg="#66776f", bg="white", wraplength=440, justify="left").pack(anchor="w", padx=28)
        tk.Label(dialog, text="자료를 먼저 확인한 뒤, 같은 원인의 오답만 다시 풀어 보세요.", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=28, pady=(10, 16))

        def open_lesson():
            dialog.destroy()
            routes = {
                "kana": self.show_kana_menu, "word": lambda: self.show_catalog("words"), "word-cloze": lambda: self.show_catalog("words"),
                "kanji": lambda: self.show_catalog("kanji"), "grammar": lambda: self.show_catalog("grammar"), "cloze": lambda: self.show_catalog("grammar"),
                "sentence": self.show_sentence_building, "dictation": self.show_dictation,
                "reading": lambda: self.start_practice_quiz("reading", self.question_pool("reading")),
                "listening": lambda: self.start_practice_quiz("listening", self.question_pool("listening")),
            }
            routes.get(cause, self.show_learning)()

        actions = tk.Frame(dialog, bg="white"); actions.pack(fill="x", padx=28, pady=(0, 24))
        ttk.Button(actions, text=f"{lesson} 열기", command=open_lesson).pack(side="left")
        ttk.Button(actions, text="집중 문제 시작", style="Accent.TButton", command=lambda: (dialog.destroy(), self.start_error_cause_quiz(cause, label))).pack(side="right")

    def start_unstarted_catalog_quiz(self, category, level):
        self.start_catalog_state_quiz(category, level, "학습 전")

    def start_catalog_state_quiz(self, category, level, state):
        ids = self.db.catalog_ids_for_state(level, category, state)
        pool = [question for question in self.question_pool(category, content_levels=[level]) if question[3] in ids]
        labels = {"words": "단어", "kanji": "한자", "grammar": "문법"}
        if not pool:
            next_step = "예정 복습을 이어가 보세요." if state == "학습 중" else "학습 중인 카드의 복습을 이어가 보세요."
            messagebox.showinfo("카드 학습", f"이 과정의 {labels[category]} {state} 카드가 없어요. {next_step}")
            return
        title = f"{level} · {'새 ' if state == '학습 전' else ''}{labels[category]} {state} 확인"
        self.start_quiz(mode=category, title=title, pool=pool)

    def personal_word_question_pool(self, word_ids=None):
        words = self.db.personal_words() if hasattr(self.db, "personal_words") else []
        return _personal_word_question_pool(words, word_ids)

    def question_pool(self, mode, kana_set=None, content_levels=None):
        database = self.__dict__.get("db")
        favorite_ids = database.favorite_ids() if mode == "favorites" and database else None
        due_ids = {row[0] for row in database.due_items(50)} if mode == "review" and database else None
        weak_ids = {row[0] for row in database.weak_items()} if mode == "weak" and database else None
        personal_words = database.personal_words() if database and hasattr(database, "personal_words") else []
        selected_level = self.__dict__.get("selected_level", "N5")
        return _question_pool(mode, selected_level, kana_set, content_levels,
                              favorite_ids, due_ids, weak_ids, personal_words)

    def start_quiz(self, mode="mixed", kana_set=None, title=None, pool=None, quiz_limit=None, time_limit=None):
        if mode in ("reading", "listening", "mock") and self.selected_level not in CONTENT:
            messagebox.showinfo("시험 대비", "독해·청해·모의고사는 N5 과정을 선택한 뒤 시작할 수 있어요.")
            self.select_level("N5")
            return
        pool = list(pool) if pool is not None else self.question_pool(mode, kana_set)
        if not pool:
            if mode in ("reading", "listening", "mock"):
                messagebox.showinfo("시험 대비", "독해·청해·모의고사는 N5 과정을 선택한 뒤 시작할 수 있어요.")
                self.select_level("N5")
            elif mode == "favorites":
                messagebox.showinfo("즐겨찾기 퀴즈", "저장된 카드가 없어요. 학습 화면에서 카드를 즐겨찾기에 추가해 보세요.")
            elif mode in ("review", "weak"):
                messagebox.showinfo("복습", "지금 예정된 복습이 없어요. 새 학습을 진행해 보세요.")
            else:
                messagebox.showinfo("퀴즈", "풀 수 있는 문제가 없어요. 다른 과정이나 유형을 선택해 보세요.")
            return
        default_limit = 12 if mode in ("diagnostic", "mock") else min(10, len(pool))
        self.quiz_session = QuizSession(mode, pool, quiz_limit or default_limit, time_limit)
        self.quiz_mode, self.quiz_pool = mode, self.quiz_session.pool
        self.quiz_limit, self.quiz_time_limit = self.quiz_session.limit, time_limit
        self.quiz_score = 0
        self.quiz_time_remaining = self.quiz_session.time_remaining
        self.quiz_answered = False; self.quiz_quality_pending = False; self.quiz_after_id = None; self.quiz_option_values = []
        self.quiz_incorrect_questions = self.quiz_session.incorrect_questions
        self.diagnostic_scores, self.mock_scores = self.quiz_session.diagnostic_scores, self.quiz_session.mock_scores
        self.quiz_timer_after_id = None
        is_review = mode in ("review", "weak")
        default_title = "예정 복습" if mode == "review" else "오답 노트 복습" if mode == "weak" else "즐겨찾기 퀴즈" if mode == "favorites" else "오늘의 퀴즈"
        build_quiz_screen(self, "복습" if is_review else "학습", title or default_title, f"{self.quiz_limit}문항 · 1~4번 답 선택 · Enter 다음 문제 · Space 청해 다시 듣기")
        if self.quiz_time_limit:
            self.update_quiz_timer()
        self.bind("<Key-1>", lambda event: self.quiz_key_answer(0))
        self.bind("<Key-2>", lambda event: self.quiz_key_answer(1))
        self.bind("<Key-3>", lambda event: self.quiz_key_answer(2))
        self.bind("<Key-4>", lambda event: self.quiz_key_answer(3))
        self.bind("<Return>", self.quiz_key_next)
        self.bind("<space>", self.quiz_key_listen)
        self.next_question()

    def update_quiz_timer(self):
        if not self.quiz_time_limit or not hasattr(self, "quiz_timer"):
            return
        self.quiz_time_remaining = self.quiz_session.time_remaining
        minutes, seconds = divmod(max(0, self.quiz_time_remaining), 60)
        self.quiz_timer.config(text=f"남은 시간 {minutes:02d}:{seconds:02d}")
        if self.quiz_session.tick():
            if self.quiz_quality_pending and self.quiz_answered:
                content_id = self.quiz_session.confirm_quality()
                if content_id:
                    self.db.record_answer(content_id, True, "normal")
                    if ":reading:" in content_id or ":listening:" in content_id:
                        self.db.complete_practice_item(content_id)
            self.finish_quiz(); return
        self.quiz_time_remaining = self.quiz_session.time_remaining
        self.quiz_timer_after_id = self.after(1000, self.update_quiz_timer)

    def next_question(self):
        self.quiz_position = self.quiz_session.position
        if self.quiz_session.complete:
            self.finish_quiz(); return
        prompt, answer, distractors, content_id = self.quiz_session.current
        options = self.quiz_session.options()
        self.quiz_answered = self.quiz_session.answered; self.quiz_quality_pending = self.quiz_session.quality_pending; self.quiz_option_values = options
        self.current_question = (prompt, answer, content_id)
        self.current_explanation = answer_explanation(content_id, answer)
        self.current_dialogue = render_question(self, prompt, answer, content_id, options, self.current_explanation,
                                                comprehension_study_tip(content_id, answer) if ":reading:" in content_id else None)
        if self.current_dialogue:
            self.after(250, lambda dialogue=self.current_dialogue: self.speak_japanese(dialogue, self.quiz_feedback, -3))

    def reveal_dialogue(self):
        if self.current_dialogue:
            self.quiz_prompt.config(text="[청해 연습 · 대본]\n" + self.current_dialogue + "\n\n" + self.current_question[0].split("\n\n", 1)[1])

    def check_answer(self, choice):
        outcome = self.quiz_session.answer(choice, mock_section)
        if outcome is None:
            return
        self.quiz_answered = True
        self.stop_speech()
        for child in self.quiz_options.winfo_children():
            if isinstance(child, ttk.Button):
                child.configure(state="disabled")
            for nested in child.winfo_children():
                if isinstance(nested, ttk.Button): nested.configure(state="disabled")
        prompt, answer, content_id = self.current_question
        correct = outcome["correct"]
        if not correct:
            self.db.record_answer(content_id, False)
            self.quiz_position = self.quiz_session.position
            self.quiz_feedback.config(text=f"정답: {answer}\n{self.current_explanation}\n오늘 다시 복습 목록에 추가했어요.", fg="#b95140")
            self.quiz_after_id = self.after(1500, self.next_question)
            return
        self.quiz_score = self.quiz_session.score
        self.quiz_quality_pending = self.quiz_session.quality_pending
        self.quiz_feedback.config(text=f"정답이에요!\n{self.current_explanation}\n\n기억 난이도를 골라 다음 복습일을 정해 주세요.", fg="#165b52")
        show_quality_controls(self)

    def finish_correct_answer(self, quality):
        if not self.quiz_answered or not self.quiz_quality_pending:
            return
        content_id = self.quiz_session.confirm_quality()
        if content_id is None:
            return
        self.quiz_quality_pending = False
        step, due = self.db.record_answer(content_id, True, quality)
        if ":reading:" in content_id or ":listening:" in content_id:
            self.db.complete_practice_item(content_id)
        interval = SRS_DAYS[step]
        self.quiz_feedback.config(text=f"{self.current_explanation}\n다음 복습: {due.isoformat()} ({interval}일 뒤)", fg="#165b52")
        for child in self.quiz_options.winfo_children():
            for nested in child.winfo_children():
                if isinstance(nested, ttk.Button): nested.configure(state="disabled")
        self.quiz_position = self.quiz_session.position
        self.quiz_after_id = self.after(850, self.next_question)

    def quiz_key_answer(self, index):
        if not self.quiz_answered and index < len(self.quiz_option_values):
            self.check_answer(self.quiz_option_values[index])
        return "break"

    def quiz_key_next(self, event=None):
        if self.quiz_quality_pending:
            return "break"
        if self.quiz_answered:
            if self.quiz_after_id:
                self.after_cancel(self.quiz_after_id); self.quiz_after_id = None
            self.next_question()
        return "break"

    def quiz_key_listen(self, event=None):
        if self.current_dialogue:
            self.speak_japanese(self.current_dialogue, self.quiz_feedback, -3)
        return "break"

    def clear_quiz_shortcuts(self):
        if getattr(self, "quiz_timer_after_id", None):
            self.after_cancel(self.quiz_timer_after_id); self.quiz_timer_after_id = None
        if getattr(self, "quiz_after_id", None):
            self.after_cancel(self.quiz_after_id); self.quiz_after_id = None
        for sequence in ("<Key-1>", "<Key-2>", "<Key-3>", "<Key-4>", "<Return>", "<space>"):
            self.unbind(sequence)

    def finish_quiz(self):
        self.stop_speech()
        self.clear_quiz_shortcuts()
        if self.quiz_timer_after_id:
            self.after_cancel(self.quiz_timer_after_id); self.quiz_timer_after_id = None
        rate = round(self.quiz_score * 100 / self.quiz_limit)
        self.db.record_quiz_result(self.quiz_mode, self.selected_level, self.quiz_score, self.quiz_limit)
        if self.quiz_mode == "diagnostic":
            recommended, breakdown, action = diagnostic_insights(self.diagnostic_scores)
            self.selected_level = recommended; self.db.set("level", recommended)
            details = " · ".join(f"{label} {score}/{total}" for label, score, total in breakdown)
            messagebox.showinfo("진단 결과", f"{self.quiz_limit}문항 중 {self.quiz_score}문항 정답 ({rate}%)\n추천 시작 과정: {recommended}\n\n구간별 결과\n{details}\n\n다음 학습: {action}\n\n진단은 학습 시작점을 돕는 간단한 참고 결과입니다.")
            self.show_home()
            return
        retry_questions = unique_questions_by_id(self.quiz_incorrect_questions)
        if self.quiz_mode == "mock":
            breakdown, action = mock_exam_insights(self.mock_scores)
            details = " · ".join(f"{label} {correct}/{total}" for label, correct, total in breakdown)
            elapsed = max(0, (self.quiz_time_limit or 0) - (self.quiz_time_remaining or 0))
            previous = self.db.recent_mock_exam_details(limit=1)
            comparison = mock_exam_comparison(self.quiz_score, self.quiz_limit, previous)
            self.db.record_mock_exam_details(self.quiz_score, self.quiz_limit, elapsed, self.mock_scores)
            result_line = (mock_exam_time_summary(self.quiz_score, self.quiz_limit, self.quiz_time_remaining or 0, self.quiz_time_limit)
                           if self.quiz_time_limit else f"{self.quiz_limit}문항 중 {self.quiz_score}문항 정답 ({rate}%)")
            if retry_questions:
                retry = messagebox.askyesno(
                    "모의고사 결과",
                    f"{result_line}\n\n"
                    f"영역별 결과\n{details}\n\n{comparison}\n다음 학습: {action}\n\n"
                    f"틀린 {len(retry_questions)}문항을 지금 다시 풀어볼까요?",
                )
                if retry:
                    self.start_quiz(mode="retry", title="모의고사 오답 다시 풀기", pool=retry_questions, quiz_limit=len(retry_questions))
                    return
            else:
                messagebox.showinfo(
                    "모의고사 결과",
                    f"{result_line}\n\n"
                    f"영역별 결과\n{details}\n\n{comparison}\n다음 학습: {action}",
                )
            self.show_home()
            return
        if retry_questions:
            retry = messagebox.askyesno(
                "퀴즈 완료",
                f"{self.quiz_limit}문항 중 {self.quiz_score}문항 정답 ({rate}%)\n"
                f"틀린 {len(retry_questions)}문항은 자동으로 간격 복습에 등록했습니다.\n\n"
                "지금 바로 틀린 문제를 다시 풀어볼까요?",
            )
            if retry:
                self.start_quiz(mode="retry", title="방금 틀린 문제 다시 풀기", pool=retry_questions, quiz_limit=len(retry_questions))
                return
        else:
            messagebox.showinfo("퀴즈 완료", f"{self.quiz_limit}문항 중 {self.quiz_score}문항 정답 ({rate}%)\n모든 문제를 맞혔어요. 훌륭합니다!")
        self.show_home()

    def show_review(self):
        return render_review(self)

    def readable_content_id(self, content_id):
        return (content_id.replace("kana:", "문자 · ").replace(":word:", " · 단어 · ")
                .replace(":word-cloze:", " · 단어 예문 빈칸 · ")
                .replace(":kanji:", " · 한자 · ").replace(":grammar:", " · 문법 · ")
                .replace(":cloze:", " · 문법 빈칸 · ")
                .replace(":sentence:", " · 문장 만들기 · ").replace(":dictation:", " · 받아쓰기 · ")
                .replace(":reading:", " · 독해 · ").replace(":listening:", " · 청해 · "))

    def show_wrong_notebook(self):
        main = self.page("복습", "오답 노트", "정답보다 오답이 많은 항목입니다. 약한 부분부터 다시 퀴즈로 확인하세요.")
        rows = self.db.weak_items()
        if not rows:
            tk.Label(main, text="아직 쌓인 오답이 없어요. 퀴즈를 풀면 약한 항목이 여기에 표시됩니다.", font=("맑은 고딕", 12), fg="#66776f", bg="#f4f6f0", wraplength=700).pack(pady=55)
            return
        for content_id, correct, wrong, due_date, interval_step in rows:
            row = self.card(main); row.pack(fill="x", pady=4)
            tk.Label(row, text=self.readable_content_id(content_id), font=("맑은 고딕", 11, "bold"), fg="#173c35", bg="white").pack(side="left", padx=16, pady=14)
            tk.Label(row, text=f"오답 {wrong} · 정답 {correct} · {SRS_DAYS[min(max(0, interval_step), len(SRS_DAYS) - 1)]}일 간격", font=("맑은 고딕", 10, "bold"), fg="#b95140", bg="white").pack(side="right", padx=16)
        ttk.Button(main, text="오답 다시 풀기", style="Accent.TButton", command=lambda: self.start_quiz(mode="weak")).pack(anchor="e", pady=18)


    def export_learning_record(self):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        destination = filedialog.asksaveasfilename(
            parent=self, title="학습 기록 CSV 내보내기", initialdir=DATA_DIR,
            initialfile=f"haru-japanese-progress-{timestamp}.csv", defaultextension=".csv",
            filetypes=(("CSV 파일", "*.csv"),),
        )
        if not destination:
            return
        try:
            exported = self.db.export_csv(destination)
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("내보내기 실패", f"학습 기록을 CSV로 저장하지 못했어요.\n{error}", parent=self)
            return
        messagebox.showinfo("내보내기 완료", f"학습 기록을 CSV 파일로 저장했어요.\n{exported}", parent=self)

    def show_voice_settings(self, start=False):
        return _show_voice_settings(self, start)

    def show_backup_restore(self):
        return _show_backup_restore(self)

    def show_stats(self):
        return render_stats(self)




if __name__ == "__main__":
    enable_high_dpi()
    JapaneseStudyApp().mainloop()
