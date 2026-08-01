"""State transitions for one quiz attempt, independent of Tkinter and storage."""

import random


class QuizSession:
    """Own question order, answers, and optional countdown for a quiz screen."""

    def __init__(self, mode, pool, limit, time_limit=None, randomizer=None):
        self.mode = mode
        self.pool = list(pool)
        self.limit = min(len(self.pool), max(0, int(limit)))
        self.time_limit = time_limit
        self.time_remaining = time_limit
        self.position = 0
        self.score = 0
        self.answered = False
        self.quality_pending = False
        self.incorrect_questions = []
        self.diagnostic_scores = {label: 0 for label in ("문자", "N5", "N4", "N3", "N2", "N1")} if mode == "diagnostic" else None
        self.mock_scores = {} if mode == "mock" else None
        self._random = randomizer or random
        self._random.shuffle(self.pool)

    @property
    def complete(self):
        return self.position >= self.limit

    @property
    def current(self):
        return None if self.complete else self.pool[self.position]

    def options(self):
        """Return shuffled answer choices for the current question."""
        if not self.current:
            return []
        _, answer, distractors, _ = self.current
        values = self._random.sample(distractors, min(3, len(distractors))) + [answer]
        self._random.shuffle(values)
        return values

    def answer(self, choice, section_for_id):
        """Apply one answer once and return its persistence and UI-relevant outcome."""
        if self.answered or not self.current:
            return None
        self.answered = True
        prompt, answer, distractors, content_id = self.current
        correct = choice == answer
        if self.mock_scores is not None:
            section = section_for_id(content_id)
            values = self.mock_scores.setdefault(section, [0, 0])
            values[1] += 1
            if correct:
                values[0] += 1
        if self.diagnostic_scores is not None and correct:
            label = "문자" if content_id.startswith("kana:") else content_id.split(":", 1)[0]
            self.diagnostic_scores[label] += 1
        if correct:
            self.score += 1
            self.quality_pending = True
        else:
            self.incorrect_questions.append((prompt, answer, distractors, content_id))
            self.position += 1
        return {"correct": correct, "answer": answer, "content_id": content_id}

    def confirm_quality(self):
        if not self.answered or not self.quality_pending or not self.current:
            return None
        self.quality_pending = False
        content_id = self.current[3]
        self.position += 1
        return content_id

    def tick(self):
        """Consume one countdown second; return true when time has expired."""
        if self.time_remaining is None:
            return False
        if self.time_remaining <= 0:
            return True
        self.time_remaining -= 1
        return False
