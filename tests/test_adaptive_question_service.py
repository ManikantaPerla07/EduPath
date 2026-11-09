from services.adaptive_question_service import select_adaptive_questions


def make_questions(topic_slug, sequence_order=1):
    return [
        {
            "question_id": f"{topic_slug}-easy",
            "question_code": f"{topic_slug.upper()}-E",
            "topic_slug": topic_slug,
            "sequence_number": sequence_order,
            "difficulty": "easy",
        },
        {
            "question_id": f"{topic_slug}-medium",
            "question_code": f"{topic_slug.upper()}-M",
            "topic_slug": topic_slug,
            "sequence_number": sequence_order,
            "difficulty": "medium",
        },
        {
            "question_id": f"{topic_slug}-hard",
            "question_code": f"{topic_slug.upper()}-H",
            "topic_slug": topic_slug,
            "sequence_number": sequence_order,
            "difficulty": "hard",
        },
    ]


def make_progress(topic_slug, status, sequence_order=1):
    return {
        "topic_slug": topic_slug,
        "mastery_status": status,
        "sequence_order": sequence_order,
    }


def test_unassessed_topic_receives_easy_question():
    questions = make_questions("variables")
    progress = [make_progress("variables", "not_assessed")]

    selected = select_adaptive_questions(
        questions,
        progress,
        question_count=1,
    )

    assert selected[0]["difficulty"] == "easy"


def test_topic_needing_revision_receives_easy_question():
    questions = make_questions("variables")
    progress = [make_progress("variables", "needs_revision")]

    selected = select_adaptive_questions(
        questions,
        progress,
        question_count=1,
    )

    assert selected[0]["difficulty"] == "easy"


def test_developing_topic_receives_medium_question():
    questions = make_questions("loops")
    progress = [make_progress("loops", "developing")]

    selected = select_adaptive_questions(
        questions,
        progress,
        question_count=1,
    )

    assert selected[0]["difficulty"] == "medium"


def test_mastery_candidate_receives_hard_question():
    questions = make_questions("functions")
    progress = [
        make_progress("functions", "candidate_for_mastery")
    ]

    selected = select_adaptive_questions(
        questions,
        progress,
        question_count=1,
    )

    assert selected[0]["difficulty"] == "hard"


def test_needs_revision_topics_are_prioritized():
    questions = (
        make_questions("loops", sequence_order=1)
        + make_questions("variables", sequence_order=2)
    )

    progress = [
        make_progress("loops", "developing", sequence_order=1),
        make_progress("variables", "needs_revision", sequence_order=2),
    ]

    selected = select_adaptive_questions(
        questions,
        progress,
        question_count=1,
    )

    assert selected[0]["topic_slug"] == "variables"


def test_selection_spreads_questions_across_topics_before_repeating():
    questions = (
        make_questions("variables", sequence_order=1)
        + make_questions("loops", sequence_order=2)
        + make_questions("functions", sequence_order=3)
    )

    progress = [
        make_progress("variables", "needs_revision", sequence_order=1),
        make_progress("loops", "developing", sequence_order=2),
        make_progress("functions", "not_assessed", sequence_order=3),
    ]

    selected = select_adaptive_questions(
        questions,
        progress,
        question_count=3,
    )

    assert len({item["topic_slug"] for item in selected}) == 3


def test_recently_attempted_question_is_avoided_when_alternative_exists():
    questions = make_questions("variables")
    progress = [make_progress("variables", "needs_revision")]

    selected = select_adaptive_questions(
        questions,
        progress,
        recently_attempted_question_ids={"variables-easy"},
        question_count=1,
    )

    assert selected[0]["question_id"] != "variables-easy"
    assert selected[0]["difficulty"] == "medium"


def test_question_can_be_reused_when_all_alternatives_were_attempted():
    questions = make_questions("variables")
    progress = [make_progress("variables", "needs_revision")]

    attempted_ids = {
        "variables-easy",
        "variables-medium",
        "variables-hard",
    }

    selected = select_adaptive_questions(
        questions,
        progress,
        recently_attempted_question_ids=attempted_ids,
        question_count=1,
    )

    assert len(selected) == 1
    assert selected[0]["difficulty"] == "easy"


def test_question_selection_never_returns_duplicate_questions():
    questions = make_questions("variables") + make_questions(
        "loops", sequence_order=2
    )

    selected = select_adaptive_questions(
        questions,
        [
            make_progress("variables", "needs_revision"),
            make_progress("loops", "developing", sequence_order=2),
        ],
        question_count=5,
    )

    question_ids = [item["question_id"] for item in selected]

    assert len(question_ids) == len(set(question_ids))


def test_selection_does_not_exceed_available_questions():
    questions = make_questions("variables")

    selected = select_adaptive_questions(
        questions,
        [make_progress("variables", "not_assessed")],
        question_count=10,
    )

    assert len(selected) == 3


def test_empty_question_bank_returns_empty_selection():
    selected = select_adaptive_questions(
        [],
        [],
        question_count=5,
    )

    assert selected == []


def test_invalid_question_count_is_rejected():
    questions = make_questions("variables")

    for invalid_count in (0, -1, True, 1.5):
        try:
            select_adaptive_questions(
                questions,
                [],
                question_count=invalid_count,
            )
        except ValueError:
            continue

        raise AssertionError(
            f"Invalid question count was accepted: {invalid_count}"
        )

def test_postgres_uuid_question_ids_are_supported():
    from uuid import uuid4

    question_id = uuid4()

    questions = [
        {
            "question_id": question_id,
            "question_code": "UUID-E",
            "topic_slug": "variables",
            "sequence_number": 1,
            "difficulty": "easy",
        }
    ]

    selected = select_adaptive_questions(
        questions,
        [make_progress("variables", "not_assessed")],
        recently_attempted_question_ids={str(question_id)},
        question_count=1,
    )

    assert len(selected) == 1
    assert selected[0]["question_id"] == question_id

class TestDynamicDifficulty:

    def test_correct_easy_answer_increases_to_medium(self):
        from services.adaptive_question_service import adjust_next_difficulty

        assert adjust_next_difficulty("easy", True) == "medium"

    def test_correct_medium_answer_increases_to_hard(self):
        from services.adaptive_question_service import adjust_next_difficulty

        assert adjust_next_difficulty("medium", True) == "hard"

    def test_correct_hard_answer_stays_hard(self):
        from services.adaptive_question_service import adjust_next_difficulty

        assert adjust_next_difficulty("hard", True) == "hard"

    def test_incorrect_hard_answer_decreases_to_medium(self):
        from services.adaptive_question_service import adjust_next_difficulty

        assert adjust_next_difficulty("hard", False) == "medium"

    def test_incorrect_medium_answer_decreases_to_easy(self):
        from services.adaptive_question_service import adjust_next_difficulty

        assert adjust_next_difficulty("medium", False) == "easy"

    def test_incorrect_easy_answer_stays_easy(self):
        from services.adaptive_question_service import adjust_next_difficulty

        assert adjust_next_difficulty("easy", False) == "easy"

    def test_invalid_current_difficulty_is_rejected(self):
        from services.adaptive_question_service import adjust_next_difficulty

        try:
            adjust_next_difficulty("expert", True)
        except ValueError:
            return

        raise AssertionError("Invalid difficulty was accepted.")

    def test_invalid_correctness_value_is_rejected(self):
        from services.adaptive_question_service import adjust_next_difficulty

        try:
            adjust_next_difficulty("easy", "yes")
        except ValueError:
            return

        raise AssertionError("Non-boolean correctness was accepted.")


class TestDynamicQuestionSelection:

    def test_correct_answer_prefers_harder_question_in_same_topic(self):
        from services.adaptive_question_service import (
            select_next_adaptive_question,
        )

        questions = [
            {
                "question_id": "variables-medium",
                "question_code": "VAR-M",
                "topic_slug": "variables",
                "difficulty": "medium",
            },
            {
                "question_id": "loops-easy",
                "question_code": "LOOP-E",
                "topic_slug": "loops",
                "difficulty": "easy",
            },
        ]

        selected = select_next_adaptive_question(
            questions=questions,
            topic_progress=[
                make_progress("variables", "developing"),
                make_progress("loops", "not_assessed", 2),
            ],
            used_question_ids={"variables-easy"},
            recently_attempted_question_ids=set(),
            last_topic_slug="variables",
            last_difficulty="easy",
            last_answer_correct=True,
        )

        assert selected["question_id"] == "variables-medium"

    def test_incorrect_answer_prefers_easier_question_in_same_topic(self):
        from services.adaptive_question_service import (
            select_next_adaptive_question,
        )

        questions = [
            {
                "question_id": "variables-easy",
                "question_code": "VAR-E",
                "topic_slug": "variables",
                "difficulty": "easy",
            },
            {
                "question_id": "variables-hard",
                "question_code": "VAR-H",
                "topic_slug": "variables",
                "difficulty": "hard",
            },
        ]

        selected = select_next_adaptive_question(
            questions=questions,
            topic_progress=[
                make_progress("variables", "developing"),
            ],
            used_question_ids={"variables-medium"},
            recently_attempted_question_ids=set(),
            last_topic_slug="variables",
            last_difficulty="hard",
            last_answer_correct=False,
        )

        assert selected["question_id"] == "variables-easy"

    def test_used_questions_are_never_selected_again(self):
        from services.adaptive_question_service import (
            select_next_adaptive_question,
        )

        questions = make_questions("variables")

        selected = select_next_adaptive_question(
            questions=questions,
            topic_progress=[
                make_progress("variables", "developing"),
            ],
            used_question_ids={
                "variables-easy",
                "variables-medium",
            },
            recently_attempted_question_ids=set(),
            last_topic_slug="variables",
            last_difficulty="medium",
            last_answer_correct=True,
        )

        assert selected["question_id"] not in {
            "variables-easy",
            "variables-medium",
        }

    def test_falls_back_to_another_topic_when_preferred_topic_is_exhausted(self):
        from services.adaptive_question_service import (
            select_next_adaptive_question,
        )

        questions = make_questions("loops", sequence_order=2)

        selected = select_next_adaptive_question(
            questions=questions,
            topic_progress=[
                make_progress("variables", "needs_revision", 1),
                make_progress("loops", "developing", 2),
            ],
            used_question_ids=set(),
            recently_attempted_question_ids=set(),
            last_topic_slug="variables",
            last_difficulty="medium",
            last_answer_correct=True,
        )

        assert selected["topic_slug"] == "loops"

    def test_returns_none_when_no_unused_questions_remain(self):
        from services.adaptive_question_service import (
            select_next_adaptive_question,
        )

        questions = make_questions("variables")

        selected = select_next_adaptive_question(
            questions=questions,
            topic_progress=[
                make_progress("variables", "needs_revision"),
            ],
            used_question_ids={
                "variables-easy",
                "variables-medium",
                "variables-hard",
            },
            recently_attempted_question_ids=set(),
            last_topic_slug="variables",
            last_difficulty="easy",
            last_answer_correct=True,
        )

        assert selected is None
