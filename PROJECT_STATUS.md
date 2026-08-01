# Project Status And File Guide

## Purpose

`하루 일본어` is a Windows desktop application for offline Japanese study from beginner material through JLPT N1-oriented self-authored content. It uses Tkinter for the UI and SQLite for local learning history. The ordinary study flow does not require an online account or API key.

This document records the repository layout, completed work, and planned work. It intentionally does not include generated EXEs, downloaded Zundamon models, local study records, build caches, or user credentials.

## Repository Files

| Path | Role |
| --- | --- |
| `.gitignore` | Excludes generated builds, downloaded voice files, local databases, caches, and editor files. |
| `.github/workflows/release.yml` | Tag-triggered release workflow: tests, EXE build, Inno Setup installer, checksum manifest, and GitHub Release assets. |
| `README.md` | User guide, feature list, build instructions, and offline voice bundle instructions. |
| `PROJECT_STATUS.md` | This file: inventory, completed work, and roadmap. |
| `RELEASE_NOTES.md` | User-facing release changes and validation notes. |
| `THIRD_PARTY_NOTICES.md` | Third-party component licenses for the standard EXE and the optional voice bundle. |
| `requirements-dev.txt` | Development-only PyInstaller dependency range. Runtime learning features use the standard library. |
| `app_info.py` | Application version and release label. |
| `content.py` | Bundled Japanese curriculum: kana, N5-N1 cards, passages, grammar, and writing guides. |
| `japanese_study.py` | Tkinter application shell, app state, navigation callbacks, quiz/review flow, and local voice process orchestration. |
| `learning_services.py` | Pure validation and formatting helpers for plans, display settings, imports, card state, and mock-exam settings. |
| `progress_logic.py` | Pure course, diagnostic, feedback, weekly activity, milestone, and error-analysis helpers. |
| `quiz_logic.py` | Pure question-pool creation and comprehension/mock-exam result helpers. |
| `quiz_session.py` | Testable quiz-attempt state: ordering, score, retries, diagnostic/mock aggregates, and timer. |
| `storage.py` | SQLite persistence, SRS scheduling, backup/restore, CSV/portable export, personal words, notes, favorites, and statistics queries. |
| `study_logic.py` | Pure study prompts, plan pace guidance, and TTS recovery instructions. |
| `tts_service.py` | Zundamon path discovery, pinned source URLs, setup checks, download safety, local endpoint privacy, and server helpers. |
| `ui_catalog.py` | Searchable word/kanji/grammar card renderer with favorites, notes, filters, resume position, and catalog quizzes. |
| `ui_dialogs.py` | Display, contrast, backup/restore, and voice-settings dialogs. |
| `ui_quiz.py` | Quiz screen, question, listening controls, and answer-quality controls. |
| `ui_practice.py` | Kana/kanji writing canvases, stroke-step dialog, sentence-building, and dictation renderers extracted from `japanese_study.py`. |
| `ui_screens.py` | Home, learning, level, plan, kana, personal-word, favorites, review, and statistics renderers. |
| `build_exe.ps1` | Runs tests and produces the standard one-file Windows executable. |
| `build_installer.ps1` | Optional code signing and Inno Setup installer creation with `Get-AuthenticodeSignature` verification and a checksum manifest. |
| `build_offline_voice_bundle.ps1` | Produces a portable folder containing the EXE, prepared Zundamon runtime/models, optional FFmpeg, and a SHA-256 manifest. |
| `packaging/harujapanese_installer.iss` | Inno Setup 6 installer script (multi-language, x64, file association, shortcuts). |
| `gui_smoke_test.py` | Desktop-session smoke test that renders every main screen and exits non-zero on any Tcl error. |
| `tests/test_database.py` | Storage, backup, SRS, import/export, favorites, notes, and statistics tests. |
| `tests/test_diagnostic.py` | Curriculum, pure logic, TTS source/path, and configuration tests. |
| `tests/test_quiz_session.py` | Quiz-session state and headless UI module import-contract tests. |

## Completed Implementation

- Offline Tkinter learning app with beginner kana and N5-N1 self-authored curriculum.
- SQLite-backed SRS at 1, 2, 4, 7, 14, 30, and 60 day intervals, review forecasts, quiz history, and learning statistics.
- Daily course plan, balanced 12-question diagnostic, time-limited mock exam, error-cause practice, reading/listening completion tracking, and retry quizzes.
- Personal word CSV import/edit/delete, card notes, favorites across levels, safe automatic/manual backups, portable record transfer, and CSV analytics export.
- Refactored monolithic behavior into focused persistence, logic, quiz, TTS, and UI modules while preserving the public app callbacks.
- Local Zundamon GPT-SoVITS integration with revision-pinned model sources, temporary-file downloads, retries, optional SHA-256 validation, local/remote endpoint privacy messaging, and CPU server startup.
- Optional offline voice release layout: an EXE next to `zundamon-gpt-sovits-api`, optional bundled FFmpeg, and `VOICE-SHA256SUMS.txt` for the prepared bundle.
- Automated verification: 73 unit tests, module compilation, whitespace diff check, standard PyInstaller build, offline bundle layout validation, and a real local Zundamon API WAV-response smoke test.
- Extracted the interaction-heavy kana writing, kanji writing, sentence-building, and dictation renderers from `japanese_study.py` into `ui_practice.py`, keeping the public app callbacks.
- Added an automated Windows GUI smoke-test strategy: headless-safe module import-contract tests plus `gui_smoke_test.py` for a desktop session or a CI runner with a display.
- Added a signed-installer workflow: `build_installer.ps1` (signtool resolution, SHA-256 signing with timestamp, Inno Setup compile, signature verification, checksum manifest) and `packaging/harujapanese_installer.iss`.
- Added a tag-triggered release workflow (`.github/workflows/release.yml`) that runs tests, builds the EXE and installer, generates a checksum manifest, and attaches artifacts to a GitHub Release.
- Accessibility review: keyboard scrolling on every page, Escape-to-close on all modal dialogs, and dynamic window titles for screen readers.
- Added `THIRD_PARTY_NOTICES.md` documenting the standard-library-only main app and the licensed third-party components in the optional voice bundle.

## Current Release Outputs

Generated release outputs are intentionally ignored by Git because they are large and reproducible:

- Standard EXE: `dist\HaruJapanese.exe`.
- Inno Setup installer: `dist\installer\HaruJapaneseSetup-{version}.exe` with `dist\installer\SHA256SUMS.txt`.
- Offline voice folder: `dist\HaruJapanese-offline\`.
- Offline voice archive: `dist\HaruJapanese-offline.zip` (large binary release artifact).
- Downloaded setup source/runtime/models: `%USERPROFILE%\.haru_japanese\zundamon-gpt-sovits-api\`.

Publish the ZIP through GitHub Releases or another binary-download host. Do not commit it to the repository: GitHub rejects individual files over 100 MB, and the voice archive is substantially larger. Keep `HaruJapanese.exe` and `zundamon-gpt-sovits-api\` together after extraction. The `.github/workflows/release.yml` workflow runs the test suite and attaches the EXE, installer, and checksums automatically when a `v*` tag is pushed.

## Planned Work

### Before A Public Release

- Manually smoke-test the standard and offline bundles on a clean Windows 10/11 account without developer tools installed. — Proxy run done: the packaged EXE was launched standalone from a fresh folder with an empty `HARU_DATA_DIR`, stayed alive, and created a first-run `progress.db` plus an automatic backup. A true clean-account pass remains a manual release step.
- Confirm the offline bundle starts the local voice server and plays audio from the extracted release folder, not the build machine's user profile.
- Publish the offline ZIP as a GitHub Release asset with its SHA-256 value and release notes.
- Review upstream Zundamon, GPT-SoVITS, PyTorch, FFmpeg, and bundled dependency licenses/notices for the exact release payload; include required attribution/license files in the release archive.

### Product And Engineering Backlog

- Extract the remaining interaction-heavy kana writing, kanji writing, sentence-building, and dictation renderers from `japanese_study.py` if continued UI modularization is valuable. — Done: moved to `ui_practice.py`.
- Add an automated Windows GUI smoke-test strategy appropriate for a desktop session or CI runner with a display. — Done: `gui_smoke_test.py` plus headless import-contract tests.
- Add a signed installer and code-signing workflow for public distribution. — Done: `build_installer.ps1` and `packaging/harujapanese_installer.iss`. The installer was actually built with Inno Setup 6.7.3 (`dist\installer\HaruJapaneseSetup-1.0.0.exe`, 14.36 MB) and the sign-then-verify flow was validated with a self-signed test certificate (`Set-AuthenticodeSignature`/`Get-AuthenticodeSignature`). Production signing still needs a commercial code-signing certificate and `signtool`.
- Add verified upstream model SHA-256 values only if an authoritative publisher source becomes available; do not invent hashes. — Done: `ZUNDAMON_MODEL_FILES` in `tts_service.py` now carries `expected_sha256` for all 8 model files. Large LFS files use the official SHA-256 published in the HuggingFace repository metadata (ETag); the small non-LFS JSON/tokenizer files and the reference audio have no publisher-published SHA-256, so their digests were computed from the pinned revisions and documented as such. `download_file` verifies every download against these digests.
- Add accessibility review with keyboard-only flows, screen-reader labels, high-DPI manual testing, and localized error messages. — Mostly done: keyboard scrolling, Escape-to-close dialogs, dynamic window titles. High-DPI and localized-error pass remain manual items on a clean machine.
- Consider a release workflow that creates checksums and attaches standard/offline artifacts automatically after tests pass. — Done: `.github/workflows/release.yml`.

## Verification Commands

```powershell
python -m unittest discover -s tests -v
python -m py_compile japanese_study.py learning_services.py progress_logic.py quiz_logic.py quiz_session.py storage.py study_logic.py tts_service.py ui_catalog.py ui_dialogs.py ui_quiz.py ui_screens.py ui_practice.py
python gui_smoke_test.py
.\build_exe.ps1
.\build_installer.ps1 -SkipExeBuild   # requires Inno Setup 6; optional -CertificatePath for signing
.\build_offline_voice_bundle.ps1 -FfmpegDirectory "C:\path\to\ffmpeg\bin"
```
