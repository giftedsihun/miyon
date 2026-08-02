"""Focused Tkinter settings and record dialogs with application actions kept as callbacks."""

import json
import sqlite3
import threading
import urllib.error
import zipfile
from datetime import date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from learning_services import (DEFAULT_TEXT_SCALE, THEME_LABELS, display_scale,
                               normalized_text_scale, normalized_theme)
from storage import BACKUP_DIRECTORY, DATA_DIR
from study_logic import tts_recovery_steps
from tts_service import (ZUNDAMON_SETUP_LOG, ZUNDAMON_SERVER_LOG, ZUNDAMON_URL,
                         TTS_CLIENT_URL, endpoint_privacy_notice)


def show_display_settings(app):
    """Show text-size controls and retain the applied setting through the app database."""
    dialog = tk.Toplevel(app); dialog.title("화면 읽기 설정"); dialog.configure(bg="white")
    dialog.transient(app); dialog.grab_set(); dialog.resizable(False, False)
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    tk.Label(dialog, text="화면 읽기 설정", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=30, pady=(25, 6))
    tk.Label(dialog, text="기본값은 Windows DPI에 맞춰 자동 조절됩니다. 필요할 때만 직접 크기를 지정하세요.", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=420, justify="left").pack(anchor="w", padx=30)
    mode = tk.StringVar(value=app.db.get("text_scale_mode", "auto"))
    value = tk.IntVar(value=app.text_scale())
    preview = tk.Label(dialog, text="미리 보기: 日本語를 천천히 읽어 보세요.", font=("맑은 고딕", 12, "bold"), fg="#165b52", bg="#f4f6f0", padx=16, pady=14)
    preview.pack(fill="x", padx=30, pady=(18, 8))
    ttk.Radiobutton(dialog, text="자동 (Windows 화면 배율 사용)", variable=mode, value="auto").pack(anchor="w", padx=30)
    ttk.Radiobutton(dialog, text="직접 지정", variable=mode, value="manual").pack(anchor="w", padx=30, pady=(4, 0))
    row = tk.Frame(dialog, bg="white"); row.pack(fill="x", padx=30)
    tk.Label(row, text="화면 크기", font=("맑은 고딕", 10, "bold"), fg="#173c35", bg="white").pack(side="left")
    tk.Label(row, textvariable=value, font=("맑은 고딕", 10), fg="#66776f", bg="white").pack(side="right")
    slider = ttk.Scale(dialog, from_=80, to=140, orient="horizontal", variable=value)
    slider.pack(fill="x", padx=30, pady=(7, 5))
    tk.Label(dialog, text="80%는 화면을 더 넓게, 100%는 기본, 140%는 더 크게 표시합니다.", font=("맑은 고딕", 9), fg="#718078", bg="white").pack(anchor="w", padx=30)

    def update_preview(*_):
        scale = display_scale(mode.get(), value.get())
        preview.config(font=("맑은 고딕", max(10, round(12 * scale / 100)), "bold"))
        slider.state(["!disabled"] if mode.get() == "manual" else ["disabled"])

    def save():
        selected_mode = "manual" if mode.get() == "manual" else "auto"
        scale = normalized_text_scale(value.get())
        app.db.set("text_scale_mode", selected_mode)
        app.db.set("text_scale", scale)
        app.apply_text_scale(selected_mode, scale)
        dialog.destroy(); app.show_home()

    value.trace_add("write", update_preview); mode.trace_add("write", update_preview); update_preview()
    buttons = tk.Frame(dialog, bg="white"); buttons.pack(fill="x", padx=30, pady=(17, 26))
    ttk.Button(buttons, text="기본 크기", command=lambda: value.set(DEFAULT_TEXT_SCALE)).pack(side="left")
    ttk.Button(buttons, text="적용", style="Accent.TButton", command=save).pack(side="right")


def show_theme_settings(app):
    """Show the color-contrast selector and apply the app-owned ttk style update."""
    dialog = tk.Toplevel(app); dialog.title("색상 대비 설정"); dialog.configure(bg="white")
    dialog.transient(app); dialog.grab_set(); dialog.resizable(False, False)
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    tk.Label(dialog, text="색상 대비 설정", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=30, pady=(25, 6))
    tk.Label(dialog, text="고대비 색상은 주요 버튼과 진행 막대를 더 선명하게 표시합니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=400, justify="left").pack(anchor="w", padx=30)
    theme = tk.StringVar(value=normalized_theme(app.db.get("color_theme", "standard")))
    for key, label in THEME_LABELS.items():
        ttk.Radiobutton(dialog, text=label, variable=theme, value=key).pack(anchor="w", padx=30, pady=(16 if key == "standard" else 5, 0))

    def save():
        app.db.set("color_theme", normalized_theme(theme.get()))
        app.configure_styles(); dialog.destroy(); app.show_home()

    ttk.Button(dialog, text="적용", style="Accent.TButton", command=save).pack(anchor="e", padx=30, pady=24)


def show_backup_restore(app):
    """Show record backup, restore, and portable-transfer controls."""
    dialog = tk.Toplevel(app); dialog.title("학습 기록 백업 및 복원"); dialog.configure(bg="white")
    dialog.transient(app); dialog.grab_set(); dialog.resizable(False, False)
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    tk.Label(dialog, text="학습 기록 백업 및 복원", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(padx=30, pady=(26, 7), anchor="w")
    tk.Label(dialog, text="백업 파일은 이 PC에만 저장됩니다. 복원 전 현재 기록은 자동으로 별도 백업됩니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white", wraplength=460, justify="left").pack(padx=30, anchor="w")
    tk.Label(dialog, text=f"자동 백업 위치: {BACKUP_DIRECTORY}", font=("맑은 고딕", 9), fg="#718078", bg="white", wraplength=460, justify="left").pack(padx=30, pady=(8, 18), anchor="w")
    actions = tk.Frame(dialog, bg="white"); actions.pack(fill="x", padx=30, pady=(0, 28))

    def create_backup():
        try:
            backup = app.db.create_backup()
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("백업 실패", f"학습 기록을 백업하지 못했어요.\n{error}", parent=dialog); return
        messagebox.showinfo("백업 완료", f"학습 기록을 안전하게 저장했어요.\n{backup}", parent=dialog)

    def restore_backup():
        source = filedialog.askopenfilename(parent=dialog, title="복원할 학습 기록 백업 선택", initialdir=BACKUP_DIRECTORY, filetypes=(("SQLite 백업", "*.db"), ("모든 파일", "*.*")))
        if not source or not messagebox.askyesno("학습 기록 복원", "현재 학습 기록이 선택한 백업으로 바뀝니다.\n현재 기록은 복원 전에 자동 백업됩니다. 계속할까요?", parent=dialog):
            return
        try:
            recovery_backup = app.db.restore_backup(source)
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("복원 실패", f"백업 파일을 복원하지 못했어요.\n{error}", parent=dialog); return
        app.selected_level = app.db.get("level", "초보")
        messagebox.showinfo("복원 완료", f"학습 기록을 복원했어요.\n이전 기록 백업: {recovery_backup}", parent=dialog)
        dialog.destroy(); app.show_home()

    def export_portable():
        destination = filedialog.asksaveasfilename(parent=dialog, title="학습 기록 묶음 내보내기", initialdir=BACKUP_DIRECTORY, initialfile=f"haru-japanese-record-{date.today():%Y%m%d}.zip", defaultextension=".zip", filetypes=(("하루 일본어 기록", "*.zip"),))
        if not destination:
            return
        try:
            archive = app.db.export_portable_record(destination)
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            messagebox.showerror("내보내기 실패", f"학습 기록 묶음을 만들지 못했어요.\n{error}", parent=dialog); return
        messagebox.showinfo("내보내기 완료", f"다른 PC로 옮길 수 있는 학습 기록 묶음을 만들었어요.\n{archive}", parent=dialog)

    def import_portable():
        source = filedialog.askopenfilename(parent=dialog, title="학습 기록 묶음 가져오기", initialdir=BACKUP_DIRECTORY, filetypes=(("하루 일본어 기록", "*.zip"), ("모든 파일", "*.*")))
        if not source or not messagebox.askyesno("학습 기록 가져오기", "현재 학습 기록을 가져온 기록으로 바꿉니다.\n현재 기록은 자동 백업됩니다. 계속할까요?", parent=dialog):
            return
        try:
            recovery_backup = app.db.restore_portable_record(source)
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            messagebox.showerror("가져오기 실패", f"학습 기록을 가져오지 못했어요.\n{error}", parent=dialog); return
        app.selected_level = app.db.get("level", "초보")
        messagebox.showinfo("가져오기 완료", f"학습 기록을 가져왔어요.\n이전 기록 백업: {recovery_backup}", parent=dialog)
        dialog.destroy(); app.show_home()

    ttk.Button(actions, text="기록 내보내기", command=export_portable).pack(side="left", padx=2)
    ttk.Button(actions, text="기록 가져오기", command=import_portable).pack(side="left", padx=2)
    ttk.Button(actions, text="지금 백업 만들기", command=create_backup).pack(side="left", padx=2)
    ttk.Button(actions, text="백업에서 복원", style="Accent.TButton", command=restore_backup).pack(side="right")


def show_voice_settings(app, start=False):
    """Render voice settings while server lifecycle operations remain app methods."""
    dialog = tk.Toplevel(app); dialog.title("로컬 AI 음성 설정"); dialog.configure(bg="white"); dialog.transient(app); dialog.grab_set()
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    tk.Label(dialog, text="ずんだもん 로컬 AI 음성", font=("맑은 고딕", 16, "bold"), fg="#173c35", bg="white").pack(anchor="w", padx=28, pady=(24, 4))
    tk.Label(dialog, text="서버 시작을 누르면 Python 3.9 환경, 필요한 패키지와 모델을 자동으로 준비합니다.\n처음에는 대용량 파일을 내려받아 시간이 걸리며, 진행 오류는 설정 로그에 저장됩니다.", font=("맑은 고딕", 10), fg="#66776f", bg="white", justify="left").pack(anchor="w", padx=28, pady=(0, 8))
    values = {}
    backend = tk.StringVar(value=str(app.db.get("zundamon_backend", "ttsclient")))
    backend_row = tk.Frame(dialog, bg="white"); backend_row.pack(fill="x", padx=28, pady=4)
    tk.Label(backend_row, text="음성 엔진", width=18, anchor="w", font=("맑은 고딕", 10), fg="#173c35", bg="white").pack(side="left")
    ttk.Combobox(backend_row, textvariable=backend, state="readonly", width=30, values=("ttsclient", "gpt_sovits"), font=("맑은 고딕", 10)).pack(side="left", fill="x", expand=True)
    url_row = tk.Frame(dialog, bg="white"); url_row.pack(fill="x", padx=28, pady=4)
    tk.Label(url_row, text="API 서버 주소", width=18, anchor="w", font=("맑은 고딕", 10), fg="#173c35", bg="white").pack(side="left")
    value = tk.StringVar(value=str(app.db.get("zundamon_url", ZUNDAMON_URL))); values["zundamon_url"] = value
    url_entry = ttk.Entry(url_row, textvariable=value, width=32, font=("맑은 고딕", 10)); url_entry.pack(side="left", fill="x", expand=True)
    speed_row = tk.Frame(dialog, bg="white"); speed_row.pack(fill="x", padx=28, pady=4)
    tk.Label(speed_row, text="기본 속도 (0.5~2.0)", width=18, anchor="w", font=("맑은 고딕", 10), fg="#173c35", bg="white").pack(side="left")
    value = tk.StringVar(value=str(app.db.get("zundamon_speed", "1.0"))); values["zundamon_speed"] = value
    ttk.Entry(speed_row, textvariable=value, width=32, font=("맑은 고딕", 10)).pack(side="left", fill="x", expand=True)

    def refresh_backend(*_):
        is_ttsclient = backend.get() == "ttsclient"
        url_row.pack_forget()
        if is_ttsclient:
            backend_hint.config(text="번들된 ttsclient 서버(port 19000)를 사용해요. 주소를 따로 입력할 필요가 없어요.")
        else:
            url_row.pack(fill="x", padx=28, pady=4)
            backend_hint.config(text="GPT-SoVITS API 서버 주소를 입력해요 (예: http://127.0.0.1:9880).")

    backend_hint = tk.Label(dialog, font=("맑은 고딕", 9), fg="#66776f", bg="white", wraplength=430, justify="left"); backend_hint.pack(anchor="w", padx=28, pady=(2, 0))
    backend.trace_add("write", refresh_backend); refresh_backend()

    privacy = tk.Label(dialog, font=("맑은 고딕", 9), fg="#718078", bg="white", wraplength=430, justify="left"); privacy.pack(anchor="w", padx=28, pady=(3, 0))

    def privacy_url():
        if backend.get() == "ttsclient":
            return TTS_CLIENT_URL
        return values["zundamon_url"].get().strip() or ZUNDAMON_URL

    def refresh_privacy(*_):
        url = privacy_url()
        external = url and not endpoint_privacy_notice(url).startswith("로컬")
        privacy.config(text=endpoint_privacy_notice(url), fg="#b95140" if external else "#718078")

    values["zundamon_url"].trace_add("write", refresh_privacy)
    backend.trace_add("write", refresh_privacy); refresh_privacy()
    status = tk.Label(dialog, text="", font=("맑은 고딕", 9), fg="#66776f", bg="white", wraplength=430, justify="left"); status.pack(anchor="w", padx=28, pady=(10, 0))
    diagnostics = tk.Label(dialog, text="", font=("맑은 고딕", 9), fg="#718078", bg="white", wraplength=430, justify="left"); diagnostics.pack(anchor="w", padx=28, pady=(5, 0))
    recovery = tk.Label(dialog, text="", font=("맑은 고딕", 9), fg="#66776f", bg="white", wraplength=430, justify="left"); recovery.pack(anchor="w", padx=28, pady=(5, 0))
    auto_start = tk.BooleanVar(value=app.db.get("zundamon_auto_start", True))
    ttk.Checkbutton(dialog, text="앱 시작 시 AI 서버가 꺼져 있으면 자동으로 시작", variable=auto_start).pack(anchor="w", padx=28, pady=(8, 0))

    def settings():
        try:
            speed = max(0.5, min(2.0, float(values["zundamon_speed"].get())))
        except ValueError:
            raise ValueError("속도는 0.5~2.0 사이의 숫자로 입력해 주세요.")
        if backend.get() == "ttsclient":
            return TTS_CLIENT_URL, speed
        return values["zundamon_url"].get().strip().rstrip("/"), speed

    def save():
        try:
            url, speed = settings()
        except ValueError as error:
            status.config(text=str(error), fg="#b95140"); return
        if backend.get() != "ttsclient" and not url.startswith(("http://", "https://")):
            status.config(text="서버 주소는 http:// 또는 https://로 시작해야 합니다.", fg="#b95140"); return
        if backend.get() != "ttsclient" and not endpoint_privacy_notice(url).startswith("로컬") and not messagebox.askyesno("외부 AI 서버 경고", endpoint_privacy_notice(url) + "\n\n이 주소를 저장할까요?", parent=dialog):
            return
        for key, value in (("zundamon_backend", backend.get()), ("zundamon_url", url), ("zundamon_speed", speed), ("zundamon_auto_start", auto_start.get())):
            app.db.set(key, value)
        status.config(text="저장했어요. 앱은 준비된 ずんだもん AI 서버만 사용합니다.", fg="#165b52")

    def test():
        save()
        if status.cget("fg") == "#b95140":
            return
        status.config(text="ずんだもん API 서버 연결을 확인하고 있어요...", fg="#66776f")
        def run():
            try:
                url, _ = settings()
                if not app.zundamon_api_available(url):
                    raise OSError("API 서버가 응답하지 않았습니다.")
                engine = "번들 ttsclient" if backend.get() == "ttsclient" else "GPT-SoVITS"
                app.after(0, lambda: status.config(text=f"연결됨: ずんだもん {engine} 서버를 찾았어요.", fg="#165b52"))
            except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as error:
                app.after(0, lambda: status.config(text=f"연결할 수 없어요. API 서버 실행과 주소를 확인해 주세요. ({error})", fg="#b95140"))
        threading.Thread(target=run, daemon=True).start()

    def refresh_status():
        message, color = app.zundamon_status()
        status.config(text=message, fg=color)
        missing = app.zundamon_missing_commands()
        if backend.get() == "ttsclient":
            required_total, required_ready, model_total, model_ready = app.zundamon_installation_summary()
            diagnostics.config(text=("검사: 번들 ttsclient" + f"\n실행 파일: {required_ready}/{required_total} · 모델 파일: {model_ready}/{model_total}\n서버 로그: {TTS_CLIENT_URL}"), fg="#718078")
            api_connected = app.zundamon_api_available(TTS_CLIENT_URL, timeout=2)
            state = "ready" if api_connected else "stopped" if app.zundamon_ready() else "setup"
            steps = tts_recovery_steps(state, ())
        else:
            required_total, required_ready, model_total, model_ready = app.zundamon_installation_summary()
            diagnostics.config(text=("검사: " + ("필수 도구 모두 확인됨" if not missing else "누락: " + ", ".join(missing)) + f"\n실행 파일: {required_ready}/{required_total} · 모델 파일: {model_ready}/{model_total}\n설정 로그: {ZUNDAMON_SETUP_LOG}\n서버 로그: {ZUNDAMON_SERVER_LOG}"), fg="#b95140" if missing else "#718078")
            api_connected = app.zundamon_api_available(str(app.db.get("zundamon_url", ZUNDAMON_URL)), timeout=2)
            state = "ready" if api_connected else "stopped" if app.zundamon_ready() else "prerequisite" if missing else "setup"
            steps = tts_recovery_steps(state, missing)
        recovery.config(text="다음 단계: " + "\n".join(f"- {step}" for step in steps))

    controls = tk.Frame(dialog, bg="white"); controls.pack(anchor="e", padx=28, pady=(14, 24))
    ttk.Button(controls, text="상태 새로고침", command=refresh_status).pack(side="left", padx=4)
    ttk.Button(controls, text="연결 확인", command=test).pack(side="left", padx=4)
    def start_server():
        save()
        if status.cget("fg") != "#b95140":
            app.start_zundamon_api(status)
    ttk.Button(controls, text="서버 시작", command=start_server).pack(side="left", padx=4)
    ttk.Button(controls, text="테스트 음성", command=lambda: app.speak_japanese("こんにちは。音声テストです。", status)).pack(side="left", padx=4)
    ttk.Button(controls, text="저장", style="Accent.TButton", command=save).pack(side="left", padx=4)
    refresh_status()
    if start:
        dialog.after(100, start_server)
