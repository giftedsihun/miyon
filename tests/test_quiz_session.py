import random
import unittest

from quiz_session import QuizSession
from tts_service import endpoint_privacy_notice, is_local_endpoint
from ui_dialogs import (show_backup_restore, show_display_settings, show_theme_settings,
                        show_voice_settings)
from ui_catalog import render_catalog
from ui_practice import (make_writing_canvas, render_dictation, render_kana_writing,
                         render_kanji_writing, render_sentence_building, render_stroke_steps)
from ui_quiz import build_quiz_screen, render_question, show_quality_controls
from ui_screens import (render_favorites_library, render_home, render_learning,
                        render_kana_menu, render_kana_notes, render_level_select,
                        render_personal_words, render_review, render_stats,
                        render_stats_details, render_study_plan)


class QuizSessionTestCase(unittest.TestCase):
    def test_correct_answer_waits_for_quality_before_advancing(self):
        pool = [("질문", "정답", ["오답1", "오답2", "오답3"], "N5:word:私")]
        session = QuizSession("words", pool, 1, randomizer=random.Random(4))

        self.assertTrue(session.answer("정답", lambda _: "어휘")["correct"])
        self.assertEqual(session.score, 1)
        self.assertEqual(session.position, 0)
        self.assertEqual(session.confirm_quality(), "N5:word:私")
        self.assertTrue(session.complete)

    def test_incorrect_answer_tracks_retry_and_mock_section(self):
        pool = [("질문", "정답", ["오답1", "오답2", "오답3"], "N5:word:私")]
        session = QuizSession("mock", pool, 1, randomizer=random.Random(4))

        outcome = session.answer("오답1", lambda _: "어휘")

        self.assertFalse(outcome["correct"])
        self.assertTrue(session.complete)
        self.assertEqual(session.mock_scores, {"어휘": [0, 1]})
        self.assertEqual(session.incorrect_questions, pool)

    def test_timer_expires_after_displaying_zero(self):
        session = QuizSession("mock", [("q", "a", ["b", "c", "d"], "N5:word:私")], 1, time_limit=1)

        self.assertFalse(session.tick())
        self.assertEqual(session.time_remaining, 0)
        self.assertTrue(session.tick())

    def test_endpoint_privacy_distinguishes_loopback_from_remote_servers(self):
        self.assertTrue(is_local_endpoint("http://127.0.0.1:9880"))
        self.assertTrue(is_local_endpoint("https://localhost/api"))
        self.assertFalse(is_local_endpoint("https://voice.example.com"))
        self.assertIn("이 PC", endpoint_privacy_notice("http://127.0.0.1:9880"))
        self.assertIn("전송", endpoint_privacy_notice("https://voice.example.com"))

    def test_ui_modules_expose_renderers_without_creating_a_tk_root(self):
        self.assertTrue(callable(build_quiz_screen))
        self.assertTrue(callable(render_question))
        self.assertTrue(callable(show_quality_controls))
        self.assertTrue(callable(render_catalog))
        self.assertTrue(callable(render_kana_writing))
        self.assertTrue(callable(render_kanji_writing))
        self.assertTrue(callable(render_sentence_building))
        self.assertTrue(callable(render_dictation))
        self.assertTrue(callable(render_stroke_steps))
        self.assertTrue(callable(make_writing_canvas))
        self.assertTrue(callable(render_home))
        self.assertTrue(callable(render_learning))
        self.assertTrue(callable(render_review))
        self.assertTrue(callable(render_stats))
        self.assertTrue(callable(render_stats_details))
        self.assertTrue(callable(render_personal_words))
        self.assertTrue(callable(render_favorites_library))
        self.assertTrue(callable(render_level_select))
        self.assertTrue(callable(render_study_plan))
        self.assertTrue(callable(render_kana_menu))
        self.assertTrue(callable(render_kana_notes))
        self.assertTrue(callable(show_display_settings))
        self.assertTrue(callable(show_theme_settings))
        self.assertTrue(callable(show_backup_restore))
        self.assertTrue(callable(show_voice_settings))


if __name__ == "__main__":
    unittest.main()
