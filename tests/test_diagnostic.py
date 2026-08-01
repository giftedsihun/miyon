import random
import tempfile
import unittest
from pathlib import Path

from content import CONTENT
from study_logic import card_study_prompt as logic_card_study_prompt
from quiz_logic import (catalog_question_pool as logic_catalog_question_pool,
                         comprehension_study_tip as logic_comprehension_study_tip,
                         question_pool as logic_question_pool)
from progress_logic import (answer_explanation as logic_answer_explanation,
                            daily_course_items as logic_daily_course_items,
                            diagnostic_insights as logic_diagnostic_insights,
                            quiz_trend_insight as logic_quiz_trend_insight)
from app_info import APP_VERSION, RELEASE_NAME
from japanese_study import (JapaneseStudyApp, daily_course_items, diagnostic_insights,
                                answer_explanation, content_levels_from_ids, diagnostic_recommendation,
                                  mock_exam_insights, mock_section, normalized_study_plan, unique_questions_by_id,
                                   daily_reminder, tts_diagnostic_summary, weakness_recommendation,
                                   catalog_resume_index, display_scale, error_cause_recommendation,
                                    favorite_card_details, mock_exam_time_summary, normalized_mock_exam, normalized_text_scale,
                                    error_cause_learning_path, personal_word_import_rows, normalized_theme,
                                    card_study_prompt, quiz_trend_insight, study_plan_pace, tts_recovery_steps)
from japanese_study import comprehension_study_tip, mock_exam_comparison
from tts_service import (GPT_SOVITS_MODEL_REVISION, ZUNDAMON_MODEL_FILES,
                          ZUNDAMON_MODEL_REVISION, ZUNDAMON_REFERENCE_SHA256,
                          ZUNDAMON_REFERENCE_SOURCE,
                          ZUNDAMON_SPEECH_WEBUI_REVISION, ZUNDAMON_URL,
                          api_available, bundled_voice_directory, bundled_voice_status,
                          file_ready, runtime_environment, server_command)


class DiagnosticQuestionTestCase(unittest.TestCase):
    def test_tts_service_keeps_local_endpoint_and_cpu_server_command(self):
        command = server_command()

        self.assertEqual(ZUNDAMON_URL, "http://127.0.0.1:9880")
        self.assertIn("api.py", command)
        self.assertEqual(command[command.index("-d") + 1], "cpu")
        self.assertTrue(all("/resolve/main/" not in source for source, _, _ in ZUNDAMON_MODEL_FILES))
        self.assertTrue(all(ZUNDAMON_MODEL_REVISION in source or GPT_SOVITS_MODEL_REVISION in source for source, _, _ in ZUNDAMON_MODEL_FILES))
        self.assertIn(ZUNDAMON_SPEECH_WEBUI_REVISION, ZUNDAMON_REFERENCE_SOURCE)
        hex_chars = "0123456789abcdefABCDEF"
        self.assertTrue(all(len(sha256) == 64 and all(char in hex_chars for char in sha256) for _, _, sha256 in ZUNDAMON_MODEL_FILES))
        self.assertEqual(len(ZUNDAMON_REFERENCE_SHA256), 64)
        self.assertTrue(all(char in hex_chars for char in ZUNDAMON_REFERENCE_SHA256))
        self.assertFalse(api_available("http://127.0.0.1:1", timeout=0.01))

    def test_bundled_voice_paths_only_apply_to_frozen_adjacent_releases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "HaruJapanese.exe"
            executable.touch()
            self.assertIsNone(bundled_voice_directory(executable, frozen=False))
            self.assertIsNone(bundled_voice_directory(executable, frozen=True))
            voice = root / "zundamon-gpt-sovits-api"
            voice.mkdir()
            self.assertEqual(bundled_voice_directory(executable, frozen=True), voice)
            for relative_path in (
                "api.py", ".haru-runtime/Scripts/python.exe", "reference/reference.wav",
                "GPT_weights_v2/zudamon_style_1-e15.ckpt", "SoVITS_weights_v2/zudamon_style_1_e8_s96.pth",
            ):
                target = voice / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"x" * 2048)
            self.assertEqual(bundled_voice_status(voice), (True, ""))
            self.assertIn("PATH", runtime_environment({"PATH": "C:\\Windows"}))

    def test_tts_service_accepts_small_configuration_files_but_not_small_model_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.json"
            model = root / "model.bin"
            config.write_text("{}", encoding="ascii")
            model.write_bytes(b"x" * 1023)
            self.assertTrue(file_ready(config))
            self.assertFalse(file_ready(model))

    def test_diagnostic_has_twelve_balanced_questions(self):
        app = JapaneseStudyApp.__new__(JapaneseStudyApp)
        for seed in range(100):
            random.seed(seed)
            questions = app.question_pool("diagnostic")
            identifiers = [question[3] for question in questions]

            self.assertEqual(len(questions), 12)
            self.assertEqual(sum(identifier.startswith("kana:") for identifier in identifiers), 2)
            for level in ("N5", "N4", "N3", "N2", "N1"):
                self.assertEqual(sum(identifier.startswith(f"{level}:") for identifier in identifiers), 2)

            for prompt, answer, distractors, _ in questions:
                self.assertNotIn(answer, distractors)
                self.assertGreaterEqual(len(distractors), 3)

    def test_daily_course_is_sequential_and_rotates_after_content_end(self):
        plan = normalized_study_plan({"level": "N5", "days": 30, "daily_words": 3})
        _, first_words, first_grammar = daily_course_items(plan, 1)
        _, second_words, second_grammar = daily_course_items(plan, 2)
        _, wrapped_words, wrapped_grammar = daily_course_items(plan, 100)

        self.assertEqual([item[0] for item in first_words], ["私", "学生", "先生"])
        self.assertEqual([item[0] for item in second_words], ["日本", "今日", "明日"])
        self.assertNotEqual(first_grammar, second_grammar)
        self.assertEqual(len(wrapped_words), 3)
        self.assertIsNotNone(wrapped_grammar)

    def test_progress_logic_keeps_course_feedback_and_trends_independent_of_tkinter(self):
        plan = {"level": "N5", "days": 30, "daily_words": 3}
        scores = {"문자": 2, "N5": 2, "N4": 0, "N3": 2, "N2": 2, "N1": 2}
        history = [("words", "2026-01-01", 6, 10), ("words", "2026-01-02", 7, 10),
                   ("words", "2026-01-03", 9, 10), ("words", "2026-01-04", 10, 10)]

        self.assertEqual(logic_daily_course_items(plan, 2), daily_course_items(plan, 2))
        self.assertEqual(logic_diagnostic_insights(scores), diagnostic_insights(scores))
        self.assertEqual(logic_answer_explanation("N5:word:私", "나, 저"), answer_explanation("N5:word:私", "나, 저"))
        self.assertEqual(logic_quiz_trend_insight(history), quiz_trend_insight(history))

    def test_invalid_plan_uses_safe_level_and_limits(self):
        plan = normalized_study_plan({"level": "unknown", "days": -1, "daily_words": 999})
        self.assertEqual(plan, {"level": "N5", "days": 7, "daily_words": 50})

    def test_diagnostic_recommendation_requires_mastery_before_next_level(self):
        self.assertEqual(diagnostic_recommendation({"문자": 0}), "문자")
        self.assertEqual(diagnostic_recommendation({"문자": 2, "N5": 1}), "N5")
        self.assertEqual(diagnostic_recommendation({"문자": 2, "N5": 2, "N4": 2, "N3": 1}), "N3")
        self.assertEqual(diagnostic_recommendation({label: 2 for label in ("문자", "N5", "N4", "N3", "N2", "N1")}), "N1")

    def test_diagnostic_insights_include_each_balanced_segment(self):
        recommended, breakdown, action = diagnostic_insights({"문자": 2, "N5": 2, "N4": 0, "N3": 2, "N2": 1, "N1": 2})
        self.assertEqual(recommended, "N4")
        self.assertEqual(breakdown, [("문자", 2, 2), ("N5", 2, 2), ("N4", 0, 2), ("N3", 2, 2), ("N2", 1, 2), ("N1", 2, 2)])
        self.assertIn("N4", action)

    def test_catalog_quiz_uses_only_visible_cards_with_level_distractors(self):
        app = JapaneseStudyApp.__new__(JapaneseStudyApp)
        selected = CONTENT["N4"]["words"][:3]
        questions = app.catalog_question_pool("words", "N4", selected)

        self.assertEqual(len(questions), len(selected))
        self.assertEqual({question[3] for question in questions}, {f"N4:word:{item[0]}" for item in selected})
        for _, answer, distractors, _ in questions:
            self.assertNotIn(answer, distractors)
            self.assertGreaterEqual(len(distractors), 3)

    def test_quiz_logic_builds_diagnostic_and_catalog_pools_without_tkinter(self):
        random.seed(7)
        diagnostic = logic_question_pool("diagnostic", "N5")
        catalog = logic_catalog_question_pool("words", "N5", CONTENT["N5"]["words"][:3])

        self.assertEqual(len(diagnostic), 12)
        self.assertEqual(sum(question[3].startswith("kana:") for question in diagnostic), 2)
        self.assertEqual([question[3] for question in catalog], ["N5:word:私", "N5:word:学生", "N5:word:先生"])

    def test_personal_word_question_pool_uses_other_personal_meanings_as_distractors(self):
        class PersonalWords:
            def personal_words(self):
                return [
                    (1, "約束", "やくそく", "약속", "", ""),
                    (2, "準備", "じゅんび", "준비", "", ""),
                    (3, "会議", "かいぎ", "회의", "", ""),
                    (4, "予定", "よてい", "예정", "", ""),
                ]

        app = JapaneseStudyApp.__new__(JapaneseStudyApp)
        app.db = PersonalWords()
        questions = app.personal_word_question_pool()

        self.assertEqual({question[3] for question in questions}, {"custom:word:1", "custom:word:2", "custom:word:3", "custom:word:4"})
        self.assertTrue(all(answer not in distractors and len(distractors) >= 3 for _, answer, distractors, _ in questions))

    def test_catalog_resume_finds_saved_card_only_in_matching_level_and_category(self):
        items = CONTENT["N5"]["words"]
        saved_key = items[2][0]
        self.assertEqual(catalog_resume_index(items, "N5", "words", f"N5:word:{saved_key}"), 2)
        self.assertEqual(catalog_resume_index(items, "N5", "words", f"N4:word:{saved_key}"), 0)
        self.assertEqual(catalog_resume_index(items, "N5", "words", "N5:word:없는단어"), 0)

    def test_weakness_recommendation_prefers_lower_accuracy_then_more_attempts(self):
        recommendation = weakness_recommendation([
            ("word", 1, 1), ("grammar", 1, 3), ("kanji", 0, 0),
        ])
        self.assertEqual(recommendation, ("grammar", "문법", 1, 3))
        self.assertIsNone(weakness_recommendation([("word", 3, 0)]))

    def test_error_cause_recommendation_names_meaning_and_comprehension_causes(self):
        recommendation = error_cause_recommendation([
            ("N5:word:私", 1, 1), ("N5:reading:0", 0, 2), ("N5:listening:0", 0, 1),
        ])
        self.assertEqual(recommendation, ("reading", "독해 근거", 0, 2))

    def test_saved_content_levels_ignore_kana_and_keep_each_jlpt_level(self):
        levels = content_levels_from_ids({"kana:あ", "N5:word:私", "N3:grammar:V ばかり"})
        self.assertEqual(levels, ["N5", "N3"])

    def test_favorite_card_details_resolve_and_sort_cross_level_saved_cards(self):
        cards = favorite_card_details({"N3:grammar:V ばかり", "N5:word:私", "kana:あ", "N1:missing:item"})

        self.assertEqual([(level, category, title) for _, level, category, title, _, _ in cards], [
            ("N5", "words", "私"), ("N3", "grammar", "V ばかり"),
        ])

    def test_retry_questions_keep_first_mistake_for_each_content_id(self):
        questions = [
            ("첫 문제", "a", ["b", "c", "d"], "N5:word:私"),
            ("중복 문제", "a", ["b", "c", "d"], "N5:word:私"),
            ("둘째 문제", "b", ["a", "c", "d"], "N5:grammar:A は B です"),
        ]
        retry = unique_questions_by_id(questions)
        self.assertEqual([question[0] for question in retry], ["첫 문제", "둘째 문제"])

    def test_answer_explanations_use_curriculum_examples_and_question_kind_hints(self):
        word = answer_explanation("N5:word:私", "나, 저")
        grammar = answer_explanation("N5:grammar:A は B です", "기본 문장")
        listening = answer_explanation("N5:listening:0", "3시")

        self.assertIn("私は韓国人です", word)
        self.assertIn("소개하거나 단정", grammar)
        self.assertIn("대화", listening)

    def test_mock_exam_insights_group_question_types_and_target_weakest_section(self):
        scores = {"어휘": [2, 2], "문법·문장": [0, 2], "독해": [1, 1]}
        breakdown, action = mock_exam_insights(scores)

        self.assertEqual(breakdown, [("어휘", 2, 2), ("문법·문장", 0, 2), ("독해", 1, 1)])
        self.assertIn("문법·문장", action)
        self.assertEqual(mock_section("N5:word:私"), "어휘")
        self.assertEqual(mock_section("N5:reading:0"), "독해")

    def test_review_and_favorite_pools_survive_selected_level_changes(self):
        class SavedItems:
            def due_items(self, limit=20):
                return [("N5:word:私", 0, 1, "2000-01-01", 0)]

            def weak_items(self):
                return []

            def favorite_ids(self):
                return {"N5:grammar:A は B です"}

        app = JapaneseStudyApp.__new__(JapaneseStudyApp)
        app.selected_level = "N3"
        app.db = SavedItems()

        review_ids = {question[3] for question in app.question_pool("review")}
        favorite_ids = {question[3] for question in app.question_pool("favorites")}

        self.assertIn("N5:word:私", review_ids)
        self.assertIn("N5:grammar:A は B です", favorite_ids)

    def test_tts_diagnostics_prioritize_live_api_then_missing_tools(self):
        self.assertEqual(tts_diagnostic_summary(True, False, ["ffmpeg"])[0], "ready")
        state, message = tts_diagnostic_summary(False, False, ["ffmpeg", "uv"])
        self.assertEqual(state, "prerequisite")
        self.assertIn("ffmpeg", message)
        self.assertEqual(tts_diagnostic_summary(False, True, ())[0], "stopped")
        self.assertEqual(tts_diagnostic_summary(False, False, ())[0], "setup")

    def test_daily_reminder_prioritizes_due_reviews_then_goal_and_can_be_dismissed(self):
        self.assertEqual(daily_reminder(20, 0, 3, 2)[0], "복습 먼저")
        title, message, action = daily_reminder(20, 15, 0, 4)
        self.assertEqual((title, action), ("오늘의 작은 목표", "학습 시작"))
        self.assertIn("5문항", message)
        self.assertIsNone(daily_reminder(20, 0, 3, 0, dismissed=True))
        self.assertIsNone(daily_reminder(20, 20, 0, 0))

    def test_text_scale_uses_readable_limits_and_default(self):
        self.assertEqual(normalized_text_scale(None), 100)
        self.assertEqual(normalized_text_scale("75"), 80)
        self.assertEqual(normalized_text_scale(200), 140)
        self.assertEqual(normalized_text_scale(115), 115)
        self.assertEqual(display_scale("auto", 140), 100)
        self.assertEqual(display_scale("manual", 115), 115)

    def test_mock_exam_settings_and_time_summary_stay_within_safe_limits(self):
        self.assertEqual(normalized_mock_exam({"questions": 2, "minutes": 200}), {"questions": 12, "minutes": 90})
        self.assertEqual(normalized_mock_exam({"questions": "20", "minutes": "10"}), {"questions": 20, "minutes": 10})
        self.assertIn("소요 4분 30초", mock_exam_time_summary(8, 12, 630, 900))
        self.assertIn("시간 종료", mock_exam_time_summary(5, 12, 0, 900))

    def test_error_recovery_path_matches_question_cause(self):
        guidance, lesson = error_cause_learning_path("reading")
        self.assertIn("근거", guidance)
        self.assertEqual(lesson, "독해 연습")
        self.assertEqual(error_cause_learning_path("unknown")[1], "집중 연습")

    def test_personal_word_csv_import_requires_columns_and_trims_rows(self):
        rows = personal_word_import_rows("word,reading,meaning,example\n 約束 , やくそく , 약속 , 約束を守る \n")
        self.assertEqual(rows, [("約束", "やくそく", "약속", "約束を守る")])
        with self.assertRaises(ValueError):
            personal_word_import_rows("word,meaning\n約束,약속\n")

    def test_color_theme_uses_safe_default(self):
        self.assertEqual(normalized_theme("high-contrast"), "high-contrast")
        self.assertEqual(normalized_theme("unknown"), "standard")

    def test_card_prompts_and_plan_pace_keep_learning_actions_specific(self):
        self.assertEqual(logic_card_study_prompt("words", CONTENT["N5"]["words"][0]), card_study_prompt("words", CONTENT["N5"]["words"][0]))
        self.assertIn("예문", card_study_prompt("words", CONTENT["N5"]["words"][0]))
        self.assertIn("한 번 써", card_study_prompt("kanji", CONTENT["N5"]["kanji"][0]))
        self.assertIn("문장", card_study_prompt("grammar", CONTENT["N5"]["grammar"][0]))
        planned, remaining, daily, message = study_plan_pace({"level": "N5", "days": 30, "daily_words": 5}, 4, 40, 10)
        self.assertEqual((planned, remaining, daily), (20, 27, 2))
        self.assertIn("계획", message)

    def test_tts_recovery_steps_are_safe_and_actionable(self):
        self.assertIn("테스트 음성", tts_recovery_steps(True, False, ())[0])
        steps = tts_recovery_steps(False, False, ("ffmpeg", "uv"))
        self.assertIn("winget install Gyan.FFmpeg", steps[0])
        self.assertTrue(any("uv" in step for step in steps))

    def test_comprehension_tips_and_mock_comparison_are_specific(self):
        self.assertEqual(logic_comprehension_study_tip("N5:reading:0", "일요일"), comprehension_study_tip("N5:reading:0", "일요일"))
        self.assertIn("지문", comprehension_study_tip("N5:reading:0", "일요일"))
        self.assertIn("언제", comprehension_study_tip("N5:listening:0", "3시"))
        self.assertIn("첫 모의고사", mock_exam_comparison(8, 12, []))
        self.assertIn("올랐", mock_exam_comparison(9, 12, [("2026-01-01", 6, 12, 0, {})]))

    def test_release_metadata_has_a_user_facing_version(self):
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertTrue(RELEASE_NAME)


if __name__ == "__main__":
    unittest.main()
