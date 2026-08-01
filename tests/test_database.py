import csv
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from japanese_study import (achievement_milestones, card_learning_state,
                             catalog_progress_summary, course_progress_insight,
                             error_cause_recommendation, error_cause_summary,
                             level_mastery_summary, practice_progress_summary,
                             quiz_trend_insight, review_workload_insight,
                             weakness_recommendation, weekly_activity_summary)
from learning_services import normalized_review_limit
from storage import Database, SRS_DAYS


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.database = Database(root / "progress.db", root / "backups")

    def tearDown(self):
        self.database.close()
        self.temporary_directory.cleanup()

    def review_row(self, content_id):
        return self.database.connection.execute(
            "SELECT correct, wrong, due_date, interval_step FROM review WHERE content_id=?",
            (content_id,),
        ).fetchone()

    def test_legacy_database_export_remains_compatible(self):
        from japanese_study import Database as legacy_database

        self.assertIs(legacy_database, Database)

    def test_difficulty_controls_review_interval(self):
        content_id = "N5:word:test"
        step, due = self.database.record_answer(content_id, True, "normal")
        self.assertEqual((step, due), (1, date.today() + timedelta(days=SRS_DAYS[1])))

        step, due = self.database.record_answer(content_id, True, "easy")
        self.assertEqual((step, due), (3, date.today() + timedelta(days=SRS_DAYS[3])))

        step, due = self.database.record_answer(content_id, True, "hard")
        self.assertEqual((step, due), (3, date.today() + timedelta(days=SRS_DAYS[3])))

        step, due = self.database.record_answer(content_id, False)
        self.assertEqual((step, due), (0, date.today()))
        self.assertEqual(self.review_row(content_id), (3, 1, date.today().isoformat(), 0))

    def test_due_and_upcoming_items_are_separated(self):
        self.database.record_answer("N5:word:due", False)
        self.database.record_answer("N5:word:later", True, "easy")

        self.assertEqual([row[0] for row in self.database.due_items()], ["N5:word:due"])
        upcoming = self.database.upcoming_items()
        self.assertEqual([row[0] for row in upcoming], ["N5:word:later"])
        self.assertEqual(upcoming[0][4], 2)

    def test_review_session_respects_configured_limit_and_due_priority(self):
        self.database.connection.executemany(
            "INSERT INTO review(content_id,correct,wrong,last_seen,due_date,interval_step) VALUES(?,?,?,?,?,?)",
            [
                ("N5:word:later", 0, 1, "2026-07-28", date.today().isoformat(), 0),
                ("N5:word:urgent", 0, 1, "2026-07-27", (date.today() - timedelta(days=2)).isoformat(), 0),
                ("N5:word:middle", 0, 3, "2026-07-28", (date.today() - timedelta(days=1)).isoformat(), 0),
            ],
        )
        self.database.connection.commit()

        session = self.database.review_session_items(5)

        self.assertEqual(normalized_review_limit("invalid"), 20)
        self.assertEqual(normalized_review_limit(2), 5)
        self.assertEqual(normalized_review_limit(99), 50)
        self.assertEqual([row[0] for row in session], ["N5:word:urgent", "N5:word:middle", "N5:word:later"])

    def test_review_forecast_groups_overdue_and_future_work_by_day(self):
        anchor = date(2026, 7, 29)
        self.database.connection.executemany(
            "INSERT INTO review(content_id,correct,wrong,last_seen,due_date,interval_step) VALUES(?,?,?,?,?,?)",
            [
                ("N5:word:overdue", 0, 1, "2026-07-27", "2026-07-27", 0),
                ("N5:word:today", 1, 0, "2026-07-29", "2026-07-29", 1),
                ("N5:word:tomorrow", 1, 0, "2026-07-29", "2026-07-30", 1),
                ("N5:word:later", 1, 0, "2026-07-29", "2026-08-01", 2),
            ],
        )
        self.database.connection.commit()

        forecast = self.database.review_forecast(days=4, today=anchor)

        self.assertEqual(forecast, [
            ("2026-07-29", 2), ("2026-07-30", 1), ("2026-07-31", 0), ("2026-08-01", 1),
        ])
        today_count, future_count, peak, message = review_workload_insight(forecast)
        self.assertEqual((today_count, future_count, peak), (2, 2, ("2026-07-29", 2)))
        self.assertIn("오늘 복습 2개", message)

    def test_review_workload_insight_handles_a_quiet_week(self):
        insight = review_workload_insight([("2026-07-29", 0), ("2026-07-30", 0)])

        self.assertEqual(insight[:3], (0, 0, ("2026-07-29", 0)))
        self.assertIn("새 카드", insight[3])

    def test_backup_restore_preserves_snapshot_and_current_recovery(self):
        self.database.set("level", "N4")
        self.database.record_answer("N4:word:snapshot", True)
        snapshot = self.database.create_backup()

        self.database.set("level", "N1")
        recovery = self.database.restore_backup(snapshot)

        self.assertTrue(snapshot.is_file())
        self.assertTrue(recovery.is_file())
        self.assertEqual(self.database.get("level"), "N4")
        self.assertIsNotNone(self.review_row("N4:word:snapshot"))

        restored_recovery = sqlite3.connect(recovery)
        level_value = restored_recovery.execute("SELECT value FROM settings WHERE key='level'").fetchone()[0]
        restored_recovery.close()
        self.assertEqual(level_value, '"N1"')

    def test_invalid_backup_does_not_replace_database(self):
        self.database.set("level", "N3")
        broken_backup = Path(self.temporary_directory.name) / "broken.db"
        broken_backup.write_text("not a sqlite database", encoding="ascii")

        with self.assertRaises(sqlite3.DatabaseError):
            self.database.restore_backup(broken_backup)

        self.assertEqual(self.database.get("level"), "N3")

    def test_automatic_backup_keeps_requested_number_of_files(self):
        backup_directory = self.database.backup_directory / "automatic"
        backup_directory.mkdir(parents=True)
        for index in range(5):
            (backup_directory / f"progress-2000010{index}.db").write_bytes(b"old")

        automatic = self.database.automatic_backup(keep=3)
        backups = sorted(backup_directory.glob("progress-*.db"))

        self.assertTrue(automatic.is_file())
        self.assertEqual(len(backups), 3)

    def test_portable_record_round_trip_restores_current_data_safely(self):
        self.database.set("level", "N4")
        self.database.record_answer("N4:word:準備", True)
        archive = Path(self.temporary_directory.name) / "record.zip"
        self.database.export_portable_record(archive)
        self.database.set("level", "N1")

        recovery = self.database.restore_portable_record(archive)

        self.assertTrue(archive.is_file())
        self.assertTrue(recovery.is_file())
        self.assertEqual(self.database.get("level"), "N4")

    def test_portable_record_rejects_invalid_archives(self):
        archive = Path(self.temporary_directory.name) / "broken.zip"
        archive.write_text("not a zip", encoding="ascii")
        self.database.set("level", "N3")

        with self.assertRaises(OSError):
            self.database.restore_portable_record(archive)

        self.assertEqual(self.database.get("level"), "N3")

    def test_mock_exam_details_keep_sections_and_duration(self):
        sections = {"어휘": [3, 4], "독해": [1, 2]}
        self.database.record_mock_exam_details(4, 6, 321, sections)

        details = self.database.recent_mock_exam_details()

        self.assertEqual(details[0], (date.today().isoformat(), 4, 6, 321, sections))

    def test_course_day_advances_only_once_per_day(self):
        advanced, next_day = self.database.complete_course_day()
        self.assertTrue(advanced)
        self.assertEqual(next_day, 2)
        self.assertEqual(self.database.get("course_day"), 2)

        advanced, next_day = self.database.complete_course_day()
        self.assertFalse(advanced)
        self.assertEqual(next_day, 2)
        self.assertEqual(self.database.get("course_day"), 2)

    def test_catalog_resume_id_is_saved_per_level_and_category(self):
        self.assertIsNone(self.database.catalog_resume_id("N5", "words"))
        self.database.save_catalog_resume("N5", "words", "N5:word:先生")
        self.database.save_catalog_resume("N5", "grammar", "N5:grammar:A は B です")

        self.assertEqual(self.database.catalog_resume_id("N5", "words"), "N5:word:先生")
        self.assertEqual(self.database.catalog_resume_id("N5", "grammar"), "N5:grammar:A は B です")

    def test_weakness_recommendation_groups_practice_by_content_type(self):
        self.database.record_answer("N5:word:water", True)
        self.database.record_answer("N5:word:water", False)
        self.database.record_answer("N5:grammar:te-form", False)
        self.database.record_answer("N5:grammar:te-form", False)

        recommendation = weakness_recommendation(self.database.weakness_type_results())

        self.assertEqual(recommendation, ("grammar", "문법", 0, 2))

    def test_error_cause_analysis_keeps_specific_question_causes_separate(self):
        self.database.record_answer("N5:word:私", True)
        self.database.record_answer("N5:word:私", False)
        self.database.record_answer("N5:cloze:これは___です", False)
        self.database.record_answer("N5:cloze:これは___です", False)
        self.database.record_answer("N5:listening:0", False)

        rows = self.database.error_cause_results()
        summary = error_cause_summary(rows)
        recommendation = error_cause_recommendation(rows)

        self.assertIn(("word", 1, 1), summary)
        self.assertIn(("cloze", 0, 2), summary)
        self.assertIn(("listening", 0, 1), summary)
        self.assertEqual(recommendation, ("cloze", "문법 빈칸", 0, 2))
        self.assertEqual(self.database.error_cause_item_ids("cloze"), {"N5:cloze:これは___です"})

    def test_favorite_cards_returns_resolved_saved_card_details(self):
        self.database.toggle_favorite("N3:grammar:V ばかり")
        self.database.toggle_favorite("N5:word:私")

        cards = self.database.favorite_cards()

        self.assertEqual([(level, category, title) for _, level, category, title, _, _ in cards], [
            ("N5", "words", "私"), ("N3", "grammar", "V ばかり"),
        ])

    def test_personal_words_support_edit_quiz_data_and_cleanup_review(self):
        word_id = self.database.save_personal_word("約束", "やくそく", "약속", "約束を守ります。")
        self.database.record_answer(f"custom:word:{word_id}", False)

        saved = self.database.personal_word(word_id)
        self.assertEqual(saved[1:5], ("約束", "やくそく", "약속", "約束を守ります。"))
        self.database.save_personal_word("約束", "やくそく", "약속", "약속을 지키다", word_id=word_id)
        self.assertEqual(self.database.personal_word(word_id)[4], "약속을 지키다")
        self.database.delete_personal_word(word_id)

        self.assertIsNone(self.database.personal_word(word_id))
        self.assertIsNone(self.review_row(f"custom:word:{word_id}"))

    def test_personal_word_import_inserts_and_updates_by_word_and_reading(self):
        inserted, updated = self.database.import_personal_words([
            ("約束", "やくそく", "약속", "약속을 지키다"),
            ("準備", "じゅんび", "준비", "미리 준비"),
        ])
        self.assertEqual((inserted, updated), (2, 0))

        inserted, updated = self.database.import_personal_words([
            ("約束", "やくそく", "약속", "約束を守る"),
        ])
        self.assertEqual((inserted, updated), (0, 1))
        saved = next(word for word in self.database.personal_words() if word[1] == "約束")
        self.assertEqual(saved[4], "約束を守る")

    def test_study_notes_can_be_saved_updated_and_deleted(self):
        content_id = "N5:word:私"

        self.assertFalse(self.database.save_note(content_id, "  "))
        self.assertEqual(self.database.get_note(content_id), "")
        self.assertTrue(self.database.save_note(content_id, " 나 자신을 말할 때 사용 "))
        self.assertEqual(self.database.get_note(content_id), "나 자신을 말할 때 사용")
        self.assertTrue(self.database.save_note(content_id, "격식 있는 상황에서도 사용"))
        self.assertEqual(self.database.get_note(content_id), "격식 있는 상황에서도 사용")
        self.assertFalse(self.database.save_note(content_id, ""))
        self.assertEqual(self.database.get_note(content_id), "")

    def test_note_ids_returns_only_cards_with_saved_notes(self):
        self.database.save_note("N5:word:私", "first person")
        self.database.save_note("N5:grammar:A は B です", "basic pattern")
        self.database.save_note("N5:word:学生", "")

        self.assertEqual(self.database.note_ids(), {"N5:word:私", "N5:grammar:A は B です"})

    def test_notes_by_id_returns_text_for_catalog_note_search(self):
        self.database.save_note("N5:word:私", "first-person formal pronoun")
        self.database.save_note("N5:grammar:A は B です", "basic identity sentence")

        self.assertEqual(self.database.notes_by_id(), {
            "N5:word:私": "first-person formal pronoun",
            "N5:grammar:A は B です": "basic identity sentence",
        })

    def test_reading_and_listening_progress_tracks_completed_items(self):
        reading_id = "N5:reading:0"
        listening_id = "N5:listening:0"
        self.database.complete_practice_item(reading_id)
        self.database.complete_practice_item(listening_id)

        self.assertEqual(self.database.completed_practice_ids("N5:reading:"), {reading_id})
        completed, total = practice_progress_summary(
            [reading_id, "N5:reading:1", "N5:reading:2"], self.database.completed_practice_ids(),
        )
        self.assertEqual((completed, total), (1, 3))

    def test_level_mastery_requires_positive_accuracy_and_four_day_interval(self):
        rows = [
            ("N5:word:私", 2, 0, 2),
            ("N5:kanji:日", 1, 1, 4),
            ("N5:grammar:A は B です", 1, 0, 1),
        ]
        reviewed, mastered, available = level_mastery_summary("N5", rows)

        self.assertEqual(reviewed, 3)
        self.assertEqual(mastered, 1)
        self.assertGreater(available, reviewed)

    def test_database_level_mastery_groups_review_records_by_jlpt_level(self):
        self.database.record_answer("N4:word:準備", True, "easy")
        self.database.record_answer("N5:word:私", False)

        mastery = dict((level, (reviewed, stable, available)) for level, reviewed, stable, available in self.database.level_mastery())
        self.assertEqual(mastery["N4"][:2], (1, 1))
        self.assertEqual(mastery["N5"][:2], (1, 0))

    def test_catalog_card_states_and_progress_distinguish_new_active_and_stable(self):
        items = [("새 카드", "x", "new", ""), ("학습 카드", "x", "active", ""), ("안정 카드", "x", "stable", "")]
        rows = {
            "N5:word:학습 카드": (1, 1, 1),
            "N5:word:안정 카드": (2, 0, 2),
        }

        self.assertEqual(card_learning_state(None), "학습 전")
        self.assertEqual(card_learning_state(rows["N5:word:학습 카드"]), "학습 중")
        self.assertEqual(card_learning_state(rows["N5:word:안정 카드"]), "안정적 암기")
        self.assertEqual(catalog_progress_summary(items, "N5", "words", rows), (1, 1, 1))

    def test_database_course_card_progress_uses_catalog_review_records(self):
        self.database.record_answer("N5:word:私", True, "easy")
        self.database.record_answer("N5:grammar:A は B です", True)

        progress = self.database.course_card_progress("N5")

        self.assertEqual(progress["words"][2], 1)
        self.assertEqual(progress["grammar"][1], 1)
        self.assertGreater(progress["words"][0], 0)

    def test_unstarted_catalog_ids_include_only_cards_without_review_history(self):
        self.database.record_answer("N5:word:私", True)
        self.database.record_answer("N5:word:学生", False)

        unstarted = self.database.unstarted_catalog_ids("N5", "words")

        self.assertNotIn("N5:word:私", unstarted)
        self.assertNotIn("N5:word:学生", unstarted)
        self.assertIn("N5:word:先生", unstarted)

    def test_catalog_ids_for_state_groups_active_and_stable_cards(self):
        self.database.record_answer("N5:word:私", True)
        self.database.record_answer("N5:word:学生", True, "easy")

        active = self.database.catalog_ids_for_state("N5", "words", "학습 중")
        stable = self.database.catalog_ids_for_state("N5", "words", "안정적 암기")

        self.assertIn("N5:word:私", active)
        self.assertNotIn("N5:word:学生", active)
        self.assertIn("N5:word:学生", stable)
        self.assertNotIn("N5:word:私", stable)

    def test_course_progress_insight_prefers_largest_new_category_then_review(self):
        progress = {"words": (3, 1, 0), "kanji": (5, 0, 0), "grammar": (1, 2, 1)}
        new, active, stable, message = course_progress_insight(progress)

        self.assertEqual((new, active, stable), (9, 3, 1))
        self.assertIn("한자 카드 5개", message)
        self.assertIn("예정 복습", course_progress_insight({"words": (0, 1, 1), "kanji": (0, 0, 1), "grammar": (0, 2, 0)})[3])

    def test_weekly_activity_includes_quiet_days_and_summarizes_answers(self):
        anchor = date(2026, 7, 29)
        self.database.connection.execute(
            "INSERT INTO activity(day,completed,answers) VALUES(?,?,?)",
            ((anchor - timedelta(days=2)).isoformat(), 1, 4),
        )
        self.database.connection.execute(
            "INSERT INTO activity(day,completed,answers) VALUES(?,?,?)",
            (anchor.isoformat(), 1, 7),
        )
        self.database.connection.commit()

        activity = self.database.weekly_activity(3, today=anchor)

        self.assertEqual(activity, [
            ((anchor - timedelta(days=2)).isoformat(), 1, 4),
            ((anchor - timedelta(days=1)).isoformat(), 0, 0),
            (anchor.isoformat(), 1, 7),
        ])
        self.assertEqual(weekly_activity_summary(activity), (2, 11, 7))

    def test_achievement_milestones_unlock_at_their_thresholds(self):
        milestones = achievement_milestones(study_days=30, answers=500, streak=7)
        self.assertTrue(all(achieved for _, _, achieved in milestones))
        starting = achievement_milestones(study_days=0, answers=0, streak=0)
        self.assertFalse(any(achieved for _, _, achieved in starting))

    def test_recent_quiz_trend_compares_newest_half_with_earlier_half(self):
        for score in (2, 2, 4, 5):
            self.database.record_quiz_result("words", "N5", score, 5)

        trend_rows = self.database.recent_quiz_results()
        rate, change, message = quiz_trend_insight(trend_rows)

        self.assertEqual(rate, 65)
        self.assertEqual(change, 50)
        self.assertIn("50%p 올랐", message)

    def test_quiz_trend_handles_short_history_without_comparison(self):
        rate, change, message = quiz_trend_insight([("2026-07-01", "words", 3, 5)])

        self.assertEqual((rate, change), (60, None))
        self.assertIn("더 풀면", message)

    def test_quiz_history_returns_most_recent_attempts_with_context(self):
        self.database.record_quiz_result("words", "N5", 2, 5)
        self.database.record_quiz_result("grammar", "N4", 4, 5)
        self.database.record_quiz_result("mock", "N3", 10, 12)

        history = self.database.quiz_history(limit=2)

        self.assertEqual([row[1:] for row in history], [
            ("mock", "N3", 10, 12), ("grammar", "N4", 4, 5),
        ])

    def test_csv_export_contains_all_learning_record_types(self):
        self.database.connection.execute(
            "INSERT INTO activity(day,completed,answers) VALUES(?,?,?)", ("2026-07-01", 1, 3)
        )
        self.database.record_answer("N5:word:=formula", False)
        self.database.record_quiz_result("words", "N5", 4, 5)
        destination = Path(self.temporary_directory.name) / "record.csv"

        exported = self.database.export_csv(destination)

        with open(exported, encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(exported, destination)
        self.assertEqual({row["record_type"] for row in rows}, {"activity", "review", "quiz"})
        review = next(row for row in rows if row["record_type"] == "review")
        self.assertEqual(review["content_id"], "N5:word:=formula")
        self.assertEqual(review["interval_days"], "1")


if __name__ == "__main__":
    unittest.main()
