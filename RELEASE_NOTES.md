# Haru Japanese 1.0.0 - Learning Journey

## Highlights

- Offline N5-N1 curriculum with card-based learning, reading, listening, writing, and timed practice exams.
- Difficulty-aware spaced repetition, daily planning, workload forecasting, learning-state progress, and targeted recovery paths.
- Personal vocabulary, notes, favorites, CSV analytics export, backups, and portable learning-record transfer.
- Local Zundamon GPT-SoVITS setup diagnostics, optional high-contrast colors, and Windows-DPI-aware display scaling.

## Known Setup Notes

- Local AI speech is optional. Its first setup requires Git, uv, FFmpeg, internet access, free disk space, and a multi-GB model download.
- The packaged app should be checked on a clean Windows machine before distributing it.
- This app uses original educational material; it is not an official JLPT product or score service.

## Packaging & Accessibility

- New Inno Setup installer script and code-signing workflow (`build_installer.ps1`).
- Tag-triggered GitHub release workflow that runs tests, builds the EXE/installer, and attaches checksums.
- Accessibility pass: keyboard scrolling, Escape-to-close on dialogs, and dynamic window titles.
- Third-party license notices added in `THIRD_PARTY_NOTICES.md`.
- AI voice model downloads are now integrity-checked: all 8 model files carry expected SHA-256 values in `tts_service.py` (official HuggingFace metadata for large LFS files; digests computed from pinned revisions where the publisher publishes none), and the reference audio has a documented computed digest.
- The installer was built and validated in this workspace with Inno Setup 6.7.3 (`dist\installer\HaruJapaneseSetup-1.0.0.exe`, 14.36 MB, with `SHA256SUMS.txt`). The sign-then-verify flow was validated with a self-signed test certificate; production signing requires a commercial code-signing certificate.
- A standalone first-run smoke check of the packaged EXE passed (launched from a fresh folder with an empty data directory; process stayed alive and created `progress.db`).
