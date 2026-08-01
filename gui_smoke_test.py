"""Desktop-session smoke test for the Tkinter app.

Renders every top-level screen and the interactive practice screens inside a real
Tk root, then destroys it. It needs a Windows desktop session (a display) and a
temporary data directory; it never contacts the network or starts the voice server.

Run it directly:

    python gui_smoke_test.py

The script exits with code 0 on success and prints each rendered screen.
"""

import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HARU_DATA_DIR"] = tmp
        import japanese_study

        app = japanese_study.JapaneseStudyApp()
        try:
            app.withdraw()
            app.db.set("zundamon_auto_start", False)
            screens = [
                app.show_home,
                app.show_learning,
                app.show_level_select,
                app.show_kana_menu,
                lambda: app.show_kana("hiragana"),
                lambda: app.show_kana_writing("hiragana"),
                app.show_kana_notes,
                app.show_study_plan,
                app.show_daily_words,
                app.show_daily_grammar,
                app.show_personal_words,
                app.show_favorites_library,
                lambda: app.show_catalog("words"),
                lambda: app.show_catalog("kanji"),
                lambda: app.show_catalog("grammar"),
                app.show_kanji_writing,
                app.show_sentence_building,
                app.show_dictation,
                app.show_review,
                app.show_wrong_notebook,
                app.show_stats,
            ]
            for index, screen in enumerate(screens, start=1):
                screen()
                app.update()
                print(f"[{index:02d}/{len(screens)}] {screen.__name__} OK")
        finally:
            app.destroy()
            app.db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
