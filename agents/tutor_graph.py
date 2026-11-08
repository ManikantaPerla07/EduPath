"""LangGraph orchestration for the EduPath grounded AI tutor."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from services.answer_generation_service import (
    MAX_QUESTION_LENGTH,
    generate_grounded_answer,
)
from services.conversation_context_service import (
    resolve_contextual_question,
)
from services.retrieval_service import (
    MAX_SEARCH_LIMIT,
    MIN_SEARCH_LIMIT,
    search_knowledge_base,
)


class TutorGraphState(TypedDict, total=False):
    """Data passed between the tutor graph nodes."""

    question: str
    course_slug: str
    topic_slug: str | None
    limit: int
    conversation_history: list[dict[str, Any]]
    retrieval_query: str
    retrieved_chunks: list[dict[str, Any]]
    answer_result: dict[str, Any]


def _validate_input(state: TutorGraphState) -> dict[str, Any]:
    """Validate and normalize learner input before retrieval."""

    question = state.get("question")

    if not isinstance(question, str):
        raise ValueError("Question must be a string.")

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Question cannot exceed {MAX_QUESTION_LENGTH} characters."
        )

    course_slug = state.get("course_slug")

    if not isinstance(course_slug, str) or not course_slug.strip():
        raise ValueError("Course slug cannot be empty.")

    topic_slug = state.get("topic_slug")

    if topic_slug is not None and (
        not isinstance(topic_slug, str) or not topic_slug.strip()
    ):
        raise ValueError("Topic slug cannot be empty.")

    limit = state.get("limit", 5)

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not MIN_SEARCH_LIMIT <= limit <= MAX_SEARCH_LIMIT
    ):
        raise ValueError(
            f"Search limit must be an integer between "
            f"{MIN_SEARCH_LIMIT} and {MAX_SEARCH_LIMIT}."
        )

    conversation_history = state.get("conversation_history", [])

    if not isinstance(conversation_history, list):
        raise ValueError("Conversation history must be a list.")

    return {
        "question": question,
        "course_slug": course_slug.strip(),
        "topic_slug": topic_slug.strip() if topic_slug else None,
        "limit": limit,
        "conversation_history": conversation_history,
    }


def build_tutor_graph(client: Any | None = None):
    """Build and compile the conversation-aware tutoring workflow."""

    def validate_input_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        return _validate_input(state)

    def resolve_context_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Convert a contextual follow-up into a standalone query."""

        retrieval_query = resolve_contextual_question(
            question=state["question"],
            conversation_history=state["conversation_history"],
            client=client,
        )

        return {"retrieval_query": retrieval_query}

    def retrieve_context_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Retrieve educational chunks using the resolved question."""

        chunks = search_knowledge_base(
            query=state["retrieval_query"],
            course_slug=state["course_slug"],
            topic_slug=state.get("topic_slug"),
            limit=state["limit"],
            client=client,
        )

        return {"retrieved_chunks": chunks}

    def route_after_retrieval(
        state: TutorGraphState,
    ) -> str:
        """Choose the next node according to retrieval results."""

        if state.get("retrieved_chunks"):
            return "generate_answer"

        return "abstain"

    def generate_answer_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Generate a grounded answer using approved retrieved sources."""

        result = generate_grounded_answer(
            question=state["retrieval_query"],
            retrieved_chunks=state["retrieved_chunks"],
            client=client,
        )

        return {"answer_result": result}

    def abstain_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Return a safe response when retrieval finds no evidence."""

        result = generate_grounded_answer(
            question=state["retrieval_query"],
            retrieved_chunks=[],
            client=client,
        )

        return {"answer_result": result}

    graph = StateGraph(TutorGraphState)

    graph.add_node("validate_input", validate_input_node)
    graph.add_node("resolve_context", resolve_context_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("abstain", abstain_node)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "resolve_context")
    graph.add_edge("resolve_context", "retrieve_context")

    graph.add_conditional_edges(
        "retrieve_context",
        route_after_retrieval,
        {
            "generate_answer": "generate_answer",
            "abstain": "abstain",
        },
    )

    graph.add_edge("generate_answer", END)
    graph.add_edge("abstain", END)

    return graph.compile()


def run_tutor_graph(
    question: str,
    course_slug: str,
    topic_slug: str | None = None,
    limit: int = 5,
    client: Any | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the conversation-aware tutor and return its answer result."""

    graph = build_tutor_graph(client=client)

    final_state = graph.invoke(
        {
            "question": question,
            "course_slug": course_slug,
            "topic_slug": topic_slug,
            "limit": limit,
            "conversation_history": conversation_history or [],
        }
    )

    result = final_state.get("answer_result")

    if not isinstance(result, dict):
        raise RuntimeError("The tutor graph did not produce an answer result.")

    return result
