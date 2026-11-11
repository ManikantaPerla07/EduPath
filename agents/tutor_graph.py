"""LangGraph orchestration for the adaptive, grounded EduPath tutor."""

import json
import logging
import time
from typing import Annotated, Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, add_messages
from langgraph.prebuilt import ToolNode

from services.adaptive_learning_service import (
    get_learner_teaching_profile,
)
from services.answer_generation_service import (
    AnswerGenerationError,
    FALLBACK_GENERATION_MODEL,
    GENERATION_MODEL,
    MAX_QUESTION_LENGTH,
    generate_grounded_answer,
)
from services.embedding_service import load_gemini_api_key
from services.gemini_error_utils import is_retryable_gemini_error
from agents.learner_tools import (
    get_my_learning_progress,
    get_my_study_plan,
)
from services.conversation_context_service import (
    resolve_contextual_question,
)
from services.retrieval_service import (
    MAX_SEARCH_LIMIT,
    MIN_SEARCH_LIMIT,
)
from services.chat_service import get_chat_session
from services.agent_telemetry_service import (
    AgentRunAlreadyActiveError,
    finish_agent_run,
    start_agent_run,
)
from services.langgraph_checkpoint_service import open_langgraph_checkpointer

from services.langchain_retriever import retrieve_course_chunks


logger = logging.getLogger(__name__)


LEARNER_DATA_TOOLS = [
    get_my_learning_progress,
    get_my_study_plan,
]

TOOL_ROUTER_SYSTEM_INSTRUCTION = """
You are EduPath's learner-data tool router.

Decide whether the latest learner question requires access to their own
saved learning progress or current study plan.

TOOL SELECTION:
- Call get_my_learning_progress when the learner asks about their own scores,
  attempts, accuracy, topic mastery, learning progress, or practice history.
- Call get_my_study_plan when the learner asks about their own plan, schedule,
  pending activities, revision tasks, or upcoming study activities.
- Call both tools when the learner explicitly needs both kinds of personal data.
- Only call tools when the question is exclusively about this learner's saved
  progress or study plan.
- Do not call tools when the question also asks for a Python explanation,
  example, or code. Those requests must stay on the grounded RAG route.
- Do not call tools for general educational questions that do not ask about
  this learner's own records.

SECURITY:
- The tools already receive the authenticated learner and selected course.
- Never ask for or invent a user ID, course ID, plan ID, or other identifier.
- Never try to access another learner's records.
- Tool results are private learner data and are not course reference material.

Return a tool call only when one is genuinely needed. Otherwise return a
message without tool calls. Do not answer the learner's question.
""".strip()

LEARNER_DATA_ANSWER_MODEL_MAX_TOKENS = 1024


def _build_learner_tool_model(
    model_name: str = GENERATION_MODEL,
) -> ChatGoogleGenerativeAI:
    """Create a Gemini model for selecting authenticated learner-data tools."""

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=load_gemini_api_key(),
        temperature=0,
        max_output_tokens=LEARNER_DATA_ANSWER_MODEL_MAX_TOKENS,
        max_retries=1,
    )


class TutorGraphState(TypedDict, total=False):
    """Data passed between the tutor graph nodes."""

    question: str
    course_slug: str
    topic_slug: str | None
    limit: int
    user_id: str | None
    conversation_history: list[dict[str, Any]]
    retrieval_query: str
    retrieved_chunks: list[dict[str, Any]]
    teaching_profile: dict[str, Any] | None
    answer_result: dict[str, Any]
    messages: Annotated[list[AnyMessage], add_messages]
    learner_context: dict[str, Any]


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

    user_id = state.get("user_id")

    if user_id is not None and (
        not isinstance(user_id, str) or not user_id.strip()
    ):
        raise ValueError("Learner user ID must be a non-empty string.")

    return {
        "question": question,
        "course_slug": course_slug.strip(),
        "topic_slug": topic_slug.strip() if topic_slug else None,
        "limit": limit,
        "conversation_history": conversation_history,
        "user_id": user_id.strip() if user_id else None,
    }


def build_tutor_graph(
    client: Any | None = None,
    checkpointer: Any | None = None,
    enable_tools: bool = False,
    tool_model: Any | None = None,
):
    """Build and compile the adaptive tutoring workflow.

    An optional checkpointer persists state for one learner chat thread.
    """

    def validate_input_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Validate input and clear transient data from the previous turn."""

        return {
            **_validate_input(state),
            "retrieved_chunks": [],
            "teaching_profile": None,
            "learner_context": {},
            "answer_result": {},
        }

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

    def decide_learner_tools_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Let Gemini select zero or more authenticated learner-data tools."""

        if not state.get("user_id"):
            raise ValueError(
                "An authenticated learner is required for learner-data tools."
            )

        # Explicitly injected models are used as-is for deterministic tests.
        # The application uses one bounded primary-to-fallback attempt.
        model_names = (
            (None,)
            if tool_model is not None
            else (GENERATION_MODEL, FALLBACK_GENERATION_MODEL)
        )
        decision = None

        for index, model_name in enumerate(model_names):
            try:
                decision_model = (
                    tool_model
                    if model_name is None
                    else _build_learner_tool_model(model_name)
                )
                model_with_tools = decision_model.bind_tools(
                    LEARNER_DATA_TOOLS
                )
                decision = model_with_tools.invoke(
                    [
                        SystemMessage(
                            content=TOOL_ROUTER_SYSTEM_INSTRUCTION
                        ),
                        HumanMessage(
                            content=state["retrieval_query"]
                        ),
                    ]
                )
                break

            except Exception as exc:
                can_use_fallback = (
                    tool_model is None
                    and index == 0
                    and is_retryable_gemini_error(exc)
                )

                if can_use_fallback:
                    logger.warning(
                        "Gemini learner-tool router model %s failed with "
                        "a retryable error (%s); trying fallback model %s.",
                        model_name,
                        type(exc).__name__,
                        FALLBACK_GENERATION_MODEL,
                    )
                    continue

                failed_model = model_name or "the injected model"
                raise AnswerGenerationError(
                    "The tutor could not determine whether learner data "
                    f"is needed using {failed_model}."
                ) from exc

        if not isinstance(decision, AIMessage):
            raise RuntimeError(
                "The learner tool router returned an invalid message."
            )

        # Checkpoint only the current turn's tool exchange. The authoritative
        # transcript continues to live in chat_messages.
        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                HumanMessage(content=state["question"]),
                decision,
            ],
            # Never reuse learner data from a previous checkpointed turn.
            "learner_context": {},
        }

    def route_after_tool_decision(state: TutorGraphState) -> str:
        """Run tools only when Gemini explicitly requested a tool call."""

        messages = state.get("messages", [])

        if messages and isinstance(messages[-1], AIMessage):
            if messages[-1].tool_calls:
                return "learner_tools"

        return "retrieve_context"

    def collect_learner_context_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Collect structured results from the current turn's tool calls."""

        messages = state.get("messages", [])
        tool_calls = [
            call
            for message in messages
            if isinstance(message, AIMessage)
            for call in message.tool_calls
        ]
        call_ids = {call.get("id") for call in tool_calls}

        learner_context: dict[str, Any] = {}

        for message in messages:
            if (
                not isinstance(message, ToolMessage)
                or message.tool_call_id not in call_ids
            ):
                continue

            tool_name = message.name or "learner_tool"

            # ToolNode marks handled exceptions as error messages. Never
            # pass an error string to the language model as learner evidence.
            if getattr(message, "status", "success") == "error":
                raise RuntimeError(
                    "EduPath could not load the requested learner data."
                )

            try:
                if not isinstance(message.content, str):
                    continue

                tool_payload = json.loads(message.content)

                if isinstance(tool_payload, dict):
                    learner_context[tool_name] = tool_payload

            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    "EduPath received invalid learner data from a tutor tool."
                ) from exc

        return {"learner_context": learner_context}

    def retrieve_context_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Retrieve educational chunks using the resolved question."""

        chunks = retrieve_course_chunks(
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
        """Route according to whether approved educational sources exist."""

        if state.get("retrieved_chunks"):
            return "adapt_teaching"

        if state.get("learner_context"):
            return "generate_answer"

        return "abstain"

    def adapt_teaching_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Load the learner's progress for the retrieved primary topic."""

        profile = get_learner_teaching_profile(
            user_id=state.get("user_id"),
            course_slug=state["course_slug"],
            retrieved_chunks=state["retrieved_chunks"],
        )

        return {"teaching_profile": profile}

    def generate_answer_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Generate a grounded answer using adaptive teaching guidance."""

        arguments = {
            "question": state["retrieval_query"],
            "retrieved_chunks": state.get("retrieved_chunks") or [],
            "client": client,
        }

        teaching_profile = state.get("teaching_profile")

        if teaching_profile is not None:
            arguments["teaching_guidance"] = teaching_profile

        learner_context = state.get("learner_context")

        if learner_context:
            arguments["learner_context"] = learner_context

        result = generate_grounded_answer(**arguments)

        return {"answer_result": result}

    def abstain_node(
        state: TutorGraphState,
    ) -> dict[str, Any]:
        """Return a safe response when retrieval finds no evidence."""

        arguments = {
            "question": state["retrieval_query"],
            "retrieved_chunks": [],
            "client": client,
        }

        learner_context = state.get("learner_context")

        if learner_context:
            arguments["learner_context"] = learner_context

        result = generate_grounded_answer(**arguments)

        return {"answer_result": result}

    graph = StateGraph(TutorGraphState)

    graph.add_node("validate_input", validate_input_node)
    graph.add_node("resolve_context", resolve_context_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("adapt_teaching", adapt_teaching_node)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("abstain", abstain_node)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "resolve_context")

    if enable_tools:
        graph.add_node("decide_learner_tools", decide_learner_tools_node)
        graph.add_node(
            "learner_tools",
            ToolNode(LEARNER_DATA_TOOLS),
        )
        graph.add_node(
            "collect_learner_context",
            collect_learner_context_node,
        )

        graph.add_edge("resolve_context", "decide_learner_tools")
        graph.add_conditional_edges(
            "decide_learner_tools",
            route_after_tool_decision,
            {
                "learner_tools": "learner_tools",
                "retrieve_context": "retrieve_context",
            },
        )
        graph.add_edge("learner_tools", "collect_learner_context")
        # Personal-data-only questions can be answered directly from tool
        # results. Mixed/course questions are routed to RAG by the tool router.
        graph.add_edge("collect_learner_context", "generate_answer")
    else:
        graph.add_edge("resolve_context", "retrieve_context")

    graph.add_conditional_edges(
        "retrieve_context",
        route_after_retrieval,
        {
            "adapt_teaching": "adapt_teaching",
            "generate_answer": "generate_answer",
            "abstain": "abstain",
        },
    )

    graph.add_edge("adapt_teaching", "generate_answer")
    graph.add_edge("generate_answer", END)
    graph.add_edge("abstain", END)

    return graph.compile(checkpointer=checkpointer)


def _finish_run_telemetry_safely(
    user_id: str,
    run_id: Any | None,
    status: str,
    started_at: float,
    error_code: str | None = None,
) -> None:
    """Best-effort run completion that never blocks a learner response."""

    if run_id is None:
        return

    duration_ms = max(0, round((time.perf_counter() - started_at) * 1000))

    try:
        finish_agent_run(
            user_id=user_id,
            run_id=run_id,
            status=status,
            duration_ms=duration_ms,
            error_code=error_code,
        )
    except Exception as exc:
        # Telemetry is diagnostic; a logging failure must not fail tutoring.
        logger.warning(
            "Could not finish Tutor run telemetry (%s).",
            type(exc).__name__,
        )


def run_tutor_graph(
    question: str,
    course_slug: str,
    topic_slug: str | None = None,
    limit: int = 5,
    client: Any | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tool_model: Any | None = None,
) -> dict[str, Any]:
    """Run the adaptive tutor, checkpointing and tracking persistent chats."""

    graph_input = {
        "question": question,
        "course_slug": course_slug,
        "topic_slug": topic_slug,
        "limit": limit,
        "conversation_history": conversation_history or [],
        "user_id": user_id,
    }

    thread_id = None
    run_id = None
    started_at = time.perf_counter()

    if session_id is not None:
        if user_id is None:
            raise ValueError(
                "A learner user ID is required for a persistent chat session."
            )

        # Resolve the thread ID from an owned session. Never trust a thread ID
        # supplied by the browser or model.
        session = get_chat_session(
            user_id=user_id,
            session_id=session_id,
        )
        thread_id = session["thread_id"]

        # Telemetry is best-effort and stores only lifecycle metadata.
        try:
            run_id = start_agent_run(
                user_id=user_id,
                session_id=session_id,
            )
        except AgentRunAlreadyActiveError:
            # A session reservation conflict is a correctness safeguard,
            # not a best-effort telemetry failure.
            raise
        except Exception as exc:
            logger.warning(
                "Could not start Tutor run telemetry (%s).",
                type(exc).__name__,
            )

    try:
        if session_id is None:
            graph = build_tutor_graph(client=client)
            final_state = graph.invoke(graph_input)
        else:
            with open_langgraph_checkpointer() as checkpointer:
                graph = build_tutor_graph(
                    client=client,
                    checkpointer=checkpointer,
                    enable_tools=True,
                    tool_model=tool_model,
                )
                final_state = graph.invoke(
                    graph_input,
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                        }
                    },
                )

        result = final_state.get("answer_result")

        if not isinstance(result, dict):
            raise RuntimeError(
                "The tutor graph did not produce an answer result."
            )

        # Expose the selected teaching approach as display metadata.
        teaching_profile = final_state.get("teaching_profile")

        if teaching_profile is not None:
            result = {
                **result,
                "teaching_profile": teaching_profile,
            }

    except Exception as exc:
        _finish_run_telemetry_safely(
            user_id=user_id or "",
            run_id=run_id,
            status="failed",
            started_at=started_at,
            error_code=type(exc).__name__,
        )
        raise

    _finish_run_telemetry_safely(
        user_id=user_id or "",
        run_id=run_id,
        status="completed",
        started_at=started_at,
    )

    return result
