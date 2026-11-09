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
