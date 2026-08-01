"""SQLite persistence for local Haru Japanese learning records."""

import csv
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from content import CONTENT
from learning_services import (card_learning_state, catalog_progress_summary,
                               content_practice_type, error_cause,
                               favorite_card_details, level_mastery_summary,
                               normalized_review_limit)

DATA_DIR = Path(os.environ.get("HARU_DATA_DIR", Path.home() / ".haru_japanese"))
DB_PATH = DATA_DIR / "progress.db"
BACKUP_DIRECTORY = DATA_DIR / "backups"
SRS_DAYS = (1, 2, 4, 7, 14, 30, 60)


class Database:
    def __init__(self, path=DB_PATH, backup_directory=BACKUP_DIRECTORY):
        self.path = Path(path)
        self.backup_directory = Path(backup_directory)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.initialize()

    def close(self):
        try:
            self.connection.close()
        except sqlite3.Error:
            pass

    def initialize(self):
        self.connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS activity (day TEXT PRIMARY KEY, completed INTEGER NOT NULL DEFAULT 0, answers INTEGER NOT NULL DEFAULT 0)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS review (
            content_id TEXT PRIMARY KEY, correct INTEGER NOT NULL DEFAULT 0,
            wrong INTEGER NOT NULL DEFAULT 0, last_seen TEXT, due_date TEXT,
            interval_step INTEGER NOT NULL DEFAULT 0)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, taken_on TEXT NOT NULL, mode TEXT NOT NULL,
            level TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL)""")
        self.connection.execute("CREATE TABLE IF NOT EXISTS favorites (content_id TEXT PRIMARY KEY)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS practice_progress (content_id TEXT PRIMARY KEY, completed_at TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS study_notes (content_id TEXT PRIMARY KEY, note TEXT NOT NULL, updated_at TEXT NOT NULL)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS personal_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT NOT NULL, reading TEXT NOT NULL,
            meaning TEXT NOT NULL, example TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            UNIQUE(word, reading))""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS mock_exam_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT, taken_on TEXT NOT NULL, score INTEGER NOT NULL,
            total INTEGER NOT NULL, duration_seconds INTEGER NOT NULL DEFAULT 0, sections TEXT NOT NULL)""")
        # Migrate databases created by earlier builds.
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(review)")}
        for column, definition in (("due_date", "TEXT"), ("interval_step", "INTEGER NOT NULL DEFAULT 0")):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE review ADD COLUMN {column} {definition}")
        activity_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(activity)")}
        if "answers" not in activity_columns:
            self.connection.execute("ALTER TABLE activity ADD COLUMN answers INTEGER NOT NULL DEFAULT 0")
        self.connection.commit()

    def close(self):
        self.connection.close()

    def create_backup(self, destination=None):
        """Create a consistent SQLite snapshot without closing the app database."""
        if destination is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = self.backup_directory / f"progress-{timestamp}.db"
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.unlink(missing_ok=True)
        target = sqlite3.connect(temporary)
        try:
            self.connection.commit()
            self.connection.backup(target)
            target.close()
            temporary.replace(destination)
        except Exception:
            target.close()
            temporary.unlink(missing_ok=True)
            raise
        return destination

    def automatic_backup(self, keep=14):
        automatic_directory = self.backup_directory / "automatic"
        destination = automatic_directory / f"progress-{date.today():%Y%m%d}.db"
        if not destination.exists():
            self.create_backup(destination)
        backups = sorted(automatic_directory.glob("progress-*.db"), key=lambda item: item.name, reverse=True)
        for expired in backups[keep:]:
            expired.unlink(missing_ok=True)
        return destination

    def restore_backup(self, source):
        """Restore through a staged copy and keep a pre-restore recovery snapshot."""
        source = Path(source)
        if not source.is_file():
            raise OSError("선택한 백업 파일을 찾을 수 없습니다.")
        staging = self.path.with_suffix(self.path.suffix + ".restore.part")
        staging.unlink(missing_ok=True)
        source_connection = None
        staged_connection = None
        try:
            source_connection = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True)
            source_connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
            staged_connection = sqlite3.connect(staging)
            source_connection.backup(staged_connection)
            staged_connection.close()
            staged_connection = None
            source_connection.close()
            source_connection = None
            recovery_backup = self.create_backup()
            self.close()
            self.connection = None
            staging.replace(self.path)
            self.connection = sqlite3.connect(self.path)
            self.initialize()
            return recovery_backup
        except Exception:
            staging.unlink(missing_ok=True)
            if self.connection is None:
                self.connection = sqlite3.connect(self.path)
            raise
        finally:
            if staged_connection is not None:
                staged_connection.close()
            if source_connection is not None:
                source_connection.close()

    def get(self, key, default=None):
        row = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        self.connection.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))
        self.connection.commit()

    def catalog_resume_id(self, level, category):
        return self.get(f"catalog_resume:{level}:{category}")

    def save_catalog_resume(self, level, category, content_id):
        self.set(f"catalog_resume:{level}:{category}", content_id)

    def complete_today(self):
        self.connection.execute("INSERT INTO activity(day,completed) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET completed=1", (date.today().isoformat(),))
        self.connection.commit()

    def complete_course_day(self):
        """Advance the course at most once per calendar day."""
        today = date.today().isoformat()
        last_completed = self.get("course_last_completed")
        if last_completed == today:
            return False, max(1, int(self.get("course_day", 1)))
        current_day = max(1, int(self.get("course_day", 1)))
        self.connection.execute("INSERT INTO activity(day,completed) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET completed=1", (today,))
        for key, value in (("course_day", current_day + 1), ("course_last_completed", today)):
            self.connection.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))
        self.connection.commit()
        return True, current_day + 1

    def record_answer(self, content_id, correct, quality="normal"):
        current = self.connection.execute("SELECT interval_step FROM review WHERE content_id=?", (content_id,)).fetchone()
        # Preserve the former first-success interval (2 days) for a normal answer.
        previous_step = current[0] if current else 0
        if correct:
            step_change = {"hard": 0, "normal": 1, "easy": 2}.get(quality, 1)
            step = min(max(0, previous_step + step_change), len(SRS_DAYS) - 1)
        else:
            step = 0
        due = date.today() + timedelta(days=SRS_DAYS[step] if correct else 0)
        field = "correct" if correct else "wrong"
        self.connection.execute(
            f"INSERT INTO review(content_id,{field},last_seen,due_date,interval_step) VALUES(?,1,?,?,?) "
            f"ON CONFLICT(content_id) DO UPDATE SET {field}={field}+1,last_seen=excluded.last_seen,due_date=excluded.due_date,interval_step=excluded.interval_step",
            (content_id, date.today().isoformat(), due.isoformat(), step),
        )
        self.connection.execute("INSERT INTO activity(day,completed,answers) VALUES(?,0,1) ON CONFLICT(day) DO UPDATE SET answers=answers+1", (date.today().isoformat(),))
        self.complete_today()
        return step, due

    def due_items(self, limit=20):
        return self.connection.execute("SELECT content_id,correct,wrong,due_date,interval_step FROM review WHERE due_date <= ? ORDER BY due_date, wrong-correct DESC LIMIT ?", (date.today().isoformat(), limit)).fetchall()

    def upcoming_items(self, limit=8):
        return self.connection.execute("SELECT content_id,correct,wrong,due_date,interval_step FROM review WHERE due_date > ? ORDER BY due_date, wrong-correct DESC LIMIT ?", (date.today().isoformat(), limit)).fetchall()

    def review_session_items(self, limit):
        return self.due_items(normalized_review_limit(limit))

    def review_forecast(self, days=7, today=None):
        """Return due workload per day, assigning overdue work to the first day."""
        days = max(1, int(days))
        start = today or date.today()
        end = start + timedelta(days=days - 1)
        counts = {current.isoformat(): 0 for current in (start + timedelta(days=index) for index in range(days))}
        overdue = self.connection.execute(
            "SELECT COUNT(*) FROM review WHERE due_date <= ?", (start.isoformat(),)
        ).fetchone()[0]
        counts[start.isoformat()] = overdue
        for due_date, count in self.connection.execute(
            "SELECT due_date,COUNT(*) FROM review WHERE due_date > ? AND due_date <= ? GROUP BY due_date",
            (start.isoformat(), end.isoformat()),
        ):
            counts[due_date] = count
        return [(current.isoformat(), counts[current.isoformat()]) for current in
                (start + timedelta(days=index) for index in range(days))]

    def stats(self):
        correct, wrong = self.connection.execute("SELECT COALESCE(SUM(correct),0),COALESCE(SUM(wrong),0) FROM review").fetchone()
        days = self.connection.execute("SELECT COUNT(*) FROM activity WHERE completed=1").fetchone()[0]
        due = self.connection.execute("SELECT COUNT(*) FROM review WHERE due_date <= ?", (date.today().isoformat(),)).fetchone()[0]
        return days, correct, wrong, due

    def streak(self):
        days = {row[0] for row in self.connection.execute("SELECT day FROM activity WHERE completed=1")}
        value, cursor = 0, date.today()
        while cursor.isoformat() in days:
            value += 1; cursor -= timedelta(days=1)
        return value

    def weekly_activity(self, days=7, today=None):
        """Return one row per day, including zero-activity days, oldest first."""
        days = max(1, int(days))
        end = today or date.today()
        start = end - timedelta(days=days - 1)
        recorded = {
            row[0]: (row[1], row[2])
            for row in self.connection.execute(
                "SELECT day,completed,answers FROM activity WHERE day BETWEEN ? AND ?",
                (start.isoformat(), end.isoformat()),
            )
        }
        return [
            (current.isoformat(), *recorded.get(current.isoformat(), (0, 0)))
            for current in (start + timedelta(days=index) for index in range(days))
        ]

    def record_quiz_result(self, mode, level, score, total):
        self.connection.execute("INSERT INTO quiz_results(taken_on,mode,level,score,total) VALUES(?,?,?,?,?)", (date.today().isoformat(), mode, level, score, total))
        self.connection.commit()

    def category_results(self):
        return self.connection.execute("SELECT mode, SUM(score), SUM(total) FROM quiz_results GROUP BY mode").fetchall()

    def recent_results(self, mode, limit=5):
        return self.connection.execute("SELECT score,total FROM quiz_results WHERE mode=? ORDER BY id DESC LIMIT ?", (mode, limit)).fetchall()

    def recent_quiz_results(self, limit=6):
        rows = self.connection.execute(
            "SELECT taken_on,mode,score,total FROM quiz_results ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return list(reversed(rows))

    def quiz_history(self, limit=8):
        return self.connection.execute(
            "SELECT taken_on,mode,level,score,total FROM quiz_results ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    def level_results(self):
        return self.connection.execute("SELECT level, SUM(score), SUM(total) FROM quiz_results WHERE level IN ('N5','N4','N3','N2','N1') GROUP BY level ORDER BY CASE level WHEN 'N5' THEN 1 WHEN 'N4' THEN 2 WHEN 'N3' THEN 3 WHEN 'N2' THEN 4 WHEN 'N1' THEN 5 END").fetchall()

    def today_answers(self):
        row = self.connection.execute("SELECT answers FROM activity WHERE day=?", (date.today().isoformat(),)).fetchone()
        return row[0] if row else 0

    def toggle_favorite(self, content_id):
        if self.connection.execute("SELECT 1 FROM favorites WHERE content_id=?", (content_id,)).fetchone():
            self.connection.execute("DELETE FROM favorites WHERE content_id=?", (content_id,))
            saved = False
        else:
            self.connection.execute("INSERT INTO favorites(content_id) VALUES(?)", (content_id,))
            saved = True
        self.connection.commit()
        return saved

    def is_favorite(self, content_id):
        return bool(self.connection.execute("SELECT 1 FROM favorites WHERE content_id=?", (content_id,)).fetchone())

    def favorite_ids(self):
        return {row[0].replace(":words:", ":word:") for row in self.connection.execute("SELECT content_id FROM favorites")}

    def favorite_cards(self):
        return favorite_card_details(self.favorite_ids())

    def personal_words(self):
        return self.connection.execute(
            "SELECT id,word,reading,meaning,example,created_at FROM personal_words ORDER BY id DESC"
        ).fetchall()

    def personal_word(self, word_id):
        return self.connection.execute(
            "SELECT id,word,reading,meaning,example,created_at FROM personal_words WHERE id=?", (word_id,)
        ).fetchone()

    def save_personal_word(self, word, reading, meaning, example="", word_id=None):
        values = (word.strip(), reading.strip(), meaning.strip(), example.strip())
        if not all(values[:3]):
            raise ValueError("일본어, 읽기, 뜻은 모두 입력해야 합니다.")
        if word_id is None:
            cursor = self.connection.execute(
                "INSERT INTO personal_words(word,reading,meaning,example,created_at) VALUES(?,?,?,?,?)",
                (*values, datetime.now().isoformat(timespec="seconds")),
            )
            word_id = cursor.lastrowid
        else:
            self.connection.execute(
                "UPDATE personal_words SET word=?,reading=?,meaning=?,example=? WHERE id=?", (*values, word_id)
            )
        self.connection.commit()
        return word_id

    def record_mock_exam_details(self, score, total, duration_seconds, sections):
        self.connection.execute(
            "INSERT INTO mock_exam_details(taken_on,score,total,duration_seconds,sections) VALUES(?,?,?,?,?)",
            (date.today().isoformat(), score, total, max(0, int(duration_seconds)), json.dumps(sections, ensure_ascii=False)),
        )
        self.connection.commit()

    def recent_mock_exam_details(self, limit=3):
        rows = self.connection.execute(
            "SELECT taken_on,score,total,duration_seconds,sections FROM mock_exam_details ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [(taken_on, score, total, duration, json.loads(sections)) for taken_on, score, total, duration, sections in rows]

    def delete_personal_word(self, word_id):
        content_id = f"custom:word:{word_id}"
        self.connection.execute("DELETE FROM personal_words WHERE id=?", (word_id,))
        self.connection.execute("DELETE FROM review WHERE content_id=?", (content_id,))
        self.connection.execute("DELETE FROM favorites WHERE content_id=?", (content_id,))
        self.connection.execute("DELETE FROM study_notes WHERE content_id=?", (content_id,))
        self.connection.commit()

    def import_personal_words(self, rows):
        """Add or update personal words atomically from validated CSV rows."""
        inserted = updated = 0
        with self.connection:
            for word, reading, meaning, example in rows:
                existing = self.connection.execute(
                    "SELECT id FROM personal_words WHERE word=? AND reading=?", (word, reading)
                ).fetchone()
                if existing:
                    self.connection.execute(
                        "UPDATE personal_words SET meaning=?,example=? WHERE id=?",
                        (meaning, example, existing[0]),
                    )
                    updated += 1
                else:
                    self.connection.execute(
                        "INSERT INTO personal_words(word,reading,meaning,example,created_at) VALUES(?,?,?,?,?)",
                        (word, reading, meaning, example, datetime.now().isoformat(timespec="seconds")),
                    )
                    inserted += 1
        return inserted, updated

    def complete_practice_item(self, content_id):
        self.connection.execute(
            "INSERT INTO practice_progress(content_id,completed_at) VALUES(?,?) "
            "ON CONFLICT(content_id) DO UPDATE SET completed_at=excluded.completed_at",
            (content_id, date.today().isoformat()),
        )
        self.connection.commit()

    def completed_practice_ids(self, prefix=None):
        if prefix:
            rows = self.connection.execute("SELECT content_id FROM practice_progress WHERE content_id LIKE ?", (prefix + "%",))
        else:
            rows = self.connection.execute("SELECT content_id FROM practice_progress")
        return {row[0] for row in rows}

    def get_note(self, content_id):
        row = self.connection.execute("SELECT note FROM study_notes WHERE content_id=?", (content_id,)).fetchone()
        return row[0] if row else ""

    def note_ids(self):
        return {row[0] for row in self.connection.execute("SELECT content_id FROM study_notes")}

    def notes_by_id(self):
        return dict(self.connection.execute("SELECT content_id,note FROM study_notes"))

    def save_note(self, content_id, note):
        note = note.strip()
        if note:
            self.connection.execute(
                "INSERT INTO study_notes(content_id,note,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(content_id) DO UPDATE SET note=excluded.note,updated_at=excluded.updated_at",
                (content_id, note, datetime.now().isoformat(timespec="seconds")),
            )
        else:
            self.connection.execute("DELETE FROM study_notes WHERE content_id=?", (content_id,))
        self.connection.commit()
        return bool(note)

    def weak_items(self, limit=30):
        return self.connection.execute("SELECT content_id,correct,wrong,due_date,interval_step FROM review WHERE wrong > correct ORDER BY wrong-correct DESC, last_seen DESC LIMIT ?", (limit,)).fetchall()

    def weakness_categories(self):
        rows = self.connection.execute("SELECT content_id,correct,wrong FROM review WHERE correct + wrong > 0").fetchall()
        labels = {"kana": "문자", "word": "단어", "word-cloze": "단어 예문", "kanji": "한자", "grammar": "문법", "cloze": "문법 빈칸", "reading": "독해", "listening": "청해", "sentence": "문장 만들기", "dictation": "받아쓰기"}
        totals = {}
        for content_id, correct, wrong in rows:
            kind = content_id.split(":")[0] if content_id.startswith("kana:") else content_id.split(":")[1] if ":" in content_id else "other"
            label = labels.get(kind, kind)
            old_correct, old_wrong = totals.get(label, (0, 0)); totals[label] = (old_correct + correct, old_wrong + wrong)
        return sorted(((label, correct, wrong) for label, (correct, wrong) in totals.items()), key=lambda item: (item[1] / (item[1] + item[2]), -(item[1] + item[2])))

    def weakness_type_results(self):
        rows = self.connection.execute("SELECT content_id,correct,wrong FROM review WHERE correct + wrong > 0").fetchall()
        totals = {}
        for content_id, correct, wrong in rows:
            kind = content_practice_type(content_id)
            old_correct, old_wrong = totals.get(kind, (0, 0))
            totals[kind] = old_correct + correct, old_wrong + wrong
        return [(kind, correct, wrong) for kind, (correct, wrong) in totals.items()]

    def error_cause_results(self):
        return self.connection.execute(
            "SELECT content_id,correct,wrong FROM review WHERE wrong > 0"
        ).fetchall()

    def error_cause_item_ids(self, cause):
        rows = self.connection.execute(
            "SELECT content_id FROM review WHERE wrong > 0"
        ).fetchall()
        return {content_id for content_id, in rows if error_cause(content_id) == cause}

    def level_mastery(self):
        rows = self.connection.execute(
            "SELECT content_id,correct,wrong,interval_step FROM review WHERE content_id LIKE 'N_:%'"
        ).fetchall()
        return [(level, *level_mastery_summary(level, rows)) for level in ("N5", "N4", "N3", "N2", "N1")]

    def catalog_review_rows(self, level, category):
        identifier_category = "word" if category == "words" else category
        prefix = f"{level}:{identifier_category}:%"
        rows = self.connection.execute(
            "SELECT content_id,correct,wrong,interval_step FROM review WHERE content_id LIKE ?", (prefix,)
        ).fetchall()
        return {content_id: (correct, wrong, interval_step) for content_id, correct, wrong, interval_step in rows}

    def course_card_progress(self, level):
        content = CONTENT.get(level, {})
        return {
            category: catalog_progress_summary(content.get(category, []), level, category, self.catalog_review_rows(level, category))
            for category in ("words", "kanji", "grammar")
        }

    def unstarted_catalog_ids(self, level, category):
        return self.catalog_ids_for_state(level, category, "학습 전")

    def catalog_ids_for_state(self, level, category, state):
        content = CONTENT.get(level, {})
        items = content.get(category, [])
        identifier_category = "word" if category == "words" else category
        review_rows = self.catalog_review_rows(level, category)
        return {
            f"{level}:{identifier_category}:{item[0]}" for item in items
            if card_learning_state(review_rows.get(f"{level}:{identifier_category}:{item[0]}")) == state
        }

    def export_csv(self, destination):
        """Export activity, review, and quiz history in one Excel-safe UTF-8 CSV."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        def safe_cell(value):
            text = "" if value is None else str(value)
            return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text

        rows = [("record_type", "date", "content_id", "correct", "wrong", "due_date", "interval_days", "completed", "answers", "quiz_mode", "level", "score", "total")]
        rows.extend(
            ("activity", day, "", "", "", "", "", completed, answers, "", "", "", "")
            for day, completed, answers in self.connection.execute(
                "SELECT day,completed,answers FROM activity ORDER BY day"
            )
        )
        rows.extend(
            ("review", "", content_id, correct, wrong, due_date, SRS_DAYS[interval_step], "", "", "", "", "", "")
            for content_id, correct, wrong, due_date, interval_step in self.connection.execute(
                "SELECT content_id,correct,wrong,due_date,interval_step FROM review ORDER BY last_seen,content_id"
            )
        )
        rows.extend(
            ("quiz", taken_on, "", "", "", "", "", "", "", mode, level, score, total)
            for taken_on, mode, level, score, total in self.connection.execute(
                "SELECT taken_on,mode,level,score,total FROM quiz_results ORDER BY id"
            )
        )
        with open(destination, "w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerows([[safe_cell(value) for value in row] for row in rows])
        return destination

    def export_portable_record(self, destination):
        """Bundle every local-learning table into a portable, versioned ZIP archive."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_db = destination.with_suffix(".progress.db")
        temporary_db.unlink(missing_ok=True)
        try:
            self.create_backup(temporary_db)
            manifest = {
                "format": "haru-japanese-learning-record",
                "version": 1,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "files": ["progress.db"],
            }
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                archive.write(temporary_db, "progress.db")
        finally:
            temporary_db.unlink(missing_ok=True)
        return destination

    def restore_portable_record(self, source):
        """Validate a portable archive, then restore it through the normal safe path."""
        source = Path(source)
        if not source.is_file():
            raise OSError("선택한 학습 기록 파일을 찾을 수 없습니다.")
        with tempfile.TemporaryDirectory() as directory:
            extracted = Path(directory) / "progress.db"
            try:
                with zipfile.ZipFile(source) as archive:
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                    if manifest.get("format") != "haru-japanese-learning-record" or manifest.get("version") != 1:
                        raise OSError("하루 일본어 학습 기록 파일이 아닙니다.")
                    info = archive.getinfo("progress.db")
                    if info.file_size <= 0 or info.file_size > 100 * 1024 * 1024:
                        raise OSError("학습 기록 DB 파일 크기가 올바르지 않습니다.")
                    with archive.open(info) as input_file, open(extracted, "wb") as output_file:
                        shutil.copyfileobj(input_file, output_file)
            except (KeyError, json.JSONDecodeError, zipfile.BadZipFile, UnicodeDecodeError) as error:
                raise OSError("학습 기록 묶음 파일을 읽을 수 없습니다.") from error
            return self.restore_backup(extracted)
