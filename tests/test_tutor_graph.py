"""Tests for the LangGraph-based EduPath tutor workflow."""

import unittest
from unittest.mock import MagicMock, call, patch

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.tutor_graph import build_tutor_graph, run_tutor_graph
from services.answer_generation_service import (
    AnswerGenerationError,
    FALLBACK_GENERATION_MODEL,
    GENERATION_MODEL,
)


class TestTutorGraph(unittest.TestCase):

    @patch("agents.tutor_graph.StateGraph")
    def test_builds_graph_with_supplied_checkpointer(self, mock_state_graph):
        graph = MagicMock()
        mock_state_graph.return_value = graph
        checkpointer = object()

        result = build_tutor_graph(checkpointer=checkpointer)

        self.assertIs(result, graph.compile.return_value)
        graph.compile.assert_called_once_with(checkpointer=checkpointer)

    def test_generates_answer_when_retrieval_finds_sources(self):
        chunks = [
            {
                "chunk_id": "chunk-1",
                "content": "Variables store values in Python.",
            }
        ]

        expected_result = {
            "answer": "Variables store values. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        with (
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = chunks
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="What is a variable?",
                course_slug="python-basics",
            )

        self.assertEqual(result, expected_result)

        retrieve.assert_called_once_with(
            query="What is a variable?",
            course_slug="python-basics",
            topic_slug=None,
            limit=5,
            client=None,
        )

        generate.assert_called_once_with(
            question="What is a variable?",
            retrieved_chunks=chunks,
            client=None,
        )

    def test_uses_abstention_path_when_retrieval_finds_no_sources(self):
        expected_result = {
            "answer": "Insufficient approved course material.",
            "insufficient_evidence": True,
            "citations": [],
            "retrieved_count": 0,
            "model": "test-model",
            "reason": "no_retrieved_evidence",
        }

        with (
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = []
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="Explain an unknown topic.",
                course_slug="python-basics",
            )

        self.assertEqual(result, expected_result)

        generate.assert_called_once_with(
            question="Explain an unknown topic.",
            retrieved_chunks=[],
            client=None,
        )

    def test_rejects_empty_question_before_retrieval(self):
        with patch("agents.tutor_graph.retrieve_course_chunks") as retrieve:
            with self.assertRaisesRegex(
                ValueError,
                "Question cannot be empty.",
            ):
                run_tutor_graph(
                    question="   ",
                    course_slug="python-basics",
                )

            retrieve.assert_not_called()

    def test_rejects_invalid_search_limit_before_retrieval(self):
        with patch("agents.tutor_graph.retrieve_course_chunks") as retrieve:
            with self.assertRaisesRegex(
                ValueError,
                "Search limit must be an integer",
            ):
                run_tutor_graph(
                    question="What is Python?",
                    course_slug="python-basics",
                    limit=0,
                )

            retrieve.assert_not_called()

    def test_passes_topic_limit_and_client_to_existing_services(self):
        chunks = [{"chunk_id": "chunk-2", "content": "Python lists."}]
        expected_result = {
            "answer": "A list stores multiple values. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        fake_client = object()

        with (
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = chunks
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="What is a list?",
                course_slug="python-basics",
                topic_slug="lists",
                limit=3,
                client=fake_client,
            )

        self.assertEqual(result, expected_result)

        retrieve.assert_called_once_with(
            query="What is a list?",
            course_slug="python-basics",
            topic_slug="lists",
            limit=3,
            client=fake_client,
        )

        generate.assert_called_once_with(
            question="What is a list?",
            retrieved_chunks=chunks,
            client=fake_client,
        )



    def test_resolves_follow_up_before_retrieval(self):
        history = [
            {"role": "user", "content": "What is a Python variable?"},
            {
                "role": "assistant",
                "content": "A variable refers to a value.",
            },
        ]

        resolved_query = (
            "Explain Python variable reassignment with an example."
        )

        expected_result = {
            "answer": "A variable can refer to a new value. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        chunks = [{"chunk_id": "chunk-1", "content": "Python variables."}]

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question"
            ) as resolve,
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            resolve.return_value = resolved_query
            retrieve.return_value = chunks
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="Explain that with an example.",
                course_slug="python-basics",
                conversation_history=history,
            )

        self.assertEqual(result, expected_result)

        resolve.assert_called_once_with(
            question="Explain that with an example.",
            conversation_history=history,
            client=None,
        )

        retrieve.assert_called_once_with(
            query=resolved_query,
            course_slug="python-basics",
            topic_slug=None,
            limit=5,
            client=None,
        )

        generate.assert_called_once_with(
            question=resolved_query,
            retrieved_chunks=chunks,
            client=None,
        )

    def test_passes_empty_history_for_a_new_conversation(self):
        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ) as resolve,
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = []
            generate.return_value = {
                "answer": "Insufficient evidence.",
                "insufficient_evidence": True,
                "citations": [],
                "retrieved_count": 0,
                "model": "test-model",
                "reason": "no_retrieved_evidence",
            }

            run_tutor_graph(
                question="What is Python?",
                course_slug="python-basics",
            )

        resolve.assert_called_once_with(
            question="What is Python?",
            conversation_history=[],
            client=None,
        )

        retrieve.assert_called_once_with(
            query="What is Python?",
            course_slug="python-basics",
            topic_slug=None,
            limit=5,
            client=None,
        )

    def test_rejects_invalid_history_before_context_resolution(self):
        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question"
            ) as resolve,
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Conversation history must be a list.",
            ):
                run_tutor_graph(
                    question="Explain that.",
                    course_slug="python-basics",
                    conversation_history="invalid",
                )

            resolve.assert_not_called()
            retrieve.assert_not_called()



    def test_loads_learner_progress_and_passes_teaching_guidance(self):
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        history = [
            {"role": "user", "content": "What are Python variables?"},
        ]

        chunks = [
            {
                "chunk_id": "chunk-1",
                "topic_slug": "variables-data-types",
                "content": "Python variables store references to values.",
            }
        ]

        teaching_profile = {
            "topic_slug": "variables-data-types",
            "topic_name": "Variables and Data Types",
            "mastery_status": "needs_revision",
            "level": "foundational_revision",
            "label": "Foundational revision",
            "instruction": "Break the concept into small steps.",
        }

        expected_result = {
            "answer": "A variable refers to a value. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
            "teaching_profile": teaching_profile,
        }

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch(
                "agents.tutor_graph.get_learner_teaching_profile"
            ) as get_profile,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = chunks
            get_profile.return_value = teaching_profile
            generate.return_value = expected_result

            result = run_tutor_graph(
                question="What are Python variables?",
                course_slug="python-basics",
                conversation_history=history,
                user_id=user_id,
            )

        self.assertEqual(result, expected_result)

        get_profile.assert_called_once_with(
            user_id=user_id,
            course_slug="python-basics",
            retrieved_chunks=chunks,
        )

        generate.assert_called_once_with(
            question="What are Python variables?",
            retrieved_chunks=chunks,
            client=None,
            teaching_guidance=teaching_profile,
        )

    def test_skips_progress_lookup_when_retrieval_finds_no_sources(self):
        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            patch("agents.tutor_graph.retrieve_course_chunks") as retrieve,
            patch(
                "agents.tutor_graph.get_learner_teaching_profile"
            ) as get_profile,
            patch("agents.tutor_graph.generate_grounded_answer") as generate,
        ):
            retrieve.return_value = []
            generate.return_value = {
                "answer": "Insufficient evidence.",
                "insufficient_evidence": True,
                "citations": [],
                "retrieved_count": 0,
                "model": "test-model",
                "reason": "no_retrieved_evidence",
            }

            result = run_tutor_graph(
                question="What is an unknown topic?",
                course_slug="python-basics",
                user_id="123e4567-e89b-12d3-a456-426614174000",
            )

        self.assertTrue(result["insufficient_evidence"])
        get_profile.assert_not_called()
        generate.assert_called_once_with(
            question="What is an unknown topic?",
            retrieved_chunks=[],
            client=None,
        )

    def test_rejects_invalid_learner_id_before_context_resolution(self):
        with patch(
            "agents.tutor_graph.resolve_contextual_question"
        ) as resolve:
            with self.assertRaisesRegex(
                ValueError,
                "Learner user ID must be a non-empty string.",
            ):
                run_tutor_graph(
                    question="What is Python?",
                    course_slug="python-basics",
                    user_id="   ",
                )

            resolve.assert_not_called()


    def test_persistent_session_uses_owned_thread_id_and_checkpointer(self):
        user_id = "ea181992-f802-4528-ae24-10b7e198d8a2"
        session_id = "11111111-1111-4111-8111-111111111111"
        thread_id = "22222222-2222-4222-8222-222222222222"
        expected_result = {
            "answer": "A variable stores a value. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        checkpointer = object()
        checkpointer_context = MagicMock()
        checkpointer_context.__enter__.return_value = checkpointer
        checkpointer_context.__exit__.return_value = False

        graph = MagicMock()
        graph.invoke.return_value = {"answer_result": expected_result}

        with (
            patch(
                "agents.tutor_graph.get_chat_session",
                return_value={"thread_id": thread_id},
            ) as get_session,
            patch(
                "agents.tutor_graph.open_langgraph_checkpointer",
                return_value=checkpointer_context,
            ) as open_checkpointer,
            patch(
                "agents.tutor_graph.build_tutor_graph",
                return_value=graph,
            ) as build_graph,
        ):
            result = run_tutor_graph(
                question="What is a variable?",
                course_slug="python-basics",
                user_id=user_id,
                session_id=session_id,
            )

        self.assertEqual(result, expected_result)
        get_session.assert_called_once_with(
            user_id=user_id,
            session_id=session_id,
        )
        open_checkpointer.assert_called_once_with()
        build_graph.assert_called_once_with(
            client=None,
            checkpointer=checkpointer,
            enable_tools=True,
            tool_model=None,
        )
        graph.invoke.assert_called_once_with(
            {
                "question": "What is a variable?",
                "course_slug": "python-basics",
                "topic_slug": None,
                "limit": 5,
                "conversation_history": [],
                "user_id": user_id,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

    @patch("agents.tutor_graph.get_chat_session")
    def test_persistent_session_requires_authenticated_user_id(
        self,
        get_session,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "learner user ID is required",
        ):
            run_tutor_graph(
                question="What is a variable?",
                course_slug="python-basics",
                session_id="11111111-1111-4111-8111-111111111111",
            )

        get_session.assert_not_called()


class FakeLearnerToolModel:

    def __init__(self, response):
        self.response = response
        self.bound_tools = []
        self.invocation_messages = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.invocation_messages = messages
        return self.response


class SequenceFakeLearnerToolModel:

    def __init__(self, responses):
        self.responses = list(responses)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self.responses.pop(0)


class RaisingLearnerToolModel:

    def __init__(self, error):
        self.error = error

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        raise self.error


class LearnerToolGraphTests(unittest.TestCase):

    USER_ID = "ea181992-f802-4528-ae24-10b7e198d8a2"

    def _graph_input(self, question):
        return {
            "question": question,
            "course_slug": "python-basics",
            "topic_slug": None,
            "limit": 5,
            "conversation_history": [],
            "user_id": self.USER_ID,
        }

    def test_no_tool_call_keeps_existing_rag_path(self):
        tool_model = FakeLearnerToolModel(
            AIMessage(content="No learner records are needed.")
        )
        chunks = [
            {
                "chunk_id": "chunk-1",
                "content": "Python variables store values.",
            }
        ]
        expected = {
            "answer": "A variable stores a value. [S1]",
            "insufficient_evidence": False,
            "citations": [{"source_id": "S1"}],
            "retrieved_count": 1,
            "model": "test-model",
            "reason": None,
        }

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            patch(
                "agents.tutor_graph.retrieve_course_chunks",
                return_value=chunks,
            ) as retrieve,
            patch(
                "agents.tutor_graph.get_learner_teaching_profile",
                return_value=None,
            ),
            patch(
                "agents.tutor_graph.generate_grounded_answer",
                return_value=expected,
            ) as generate,
        ):
            graph = build_tutor_graph(
                enable_tools=True,
                tool_model=tool_model,
            )
            state = graph.invoke(
                self._graph_input("What is a Python variable?")
            )

        self.assertEqual(state["answer_result"], expected)
        retrieve.assert_called_once()
        generate.assert_called_once_with(
            question="What is a Python variable?",
            retrieved_chunks=chunks,
            client=None,
        )
        self.assertEqual(
            {tool.name for tool in tool_model.bound_tools},
            {"get_my_learning_progress", "get_my_study_plan"},
        )
        self.assertEqual(tool_model.invocation_messages[-1].content, "What is a Python variable?")

    @patch("agents.learner_tools.fetch_learner_topic_progress")
    @patch("agents.tutor_graph.resolve_contextual_question")
    @patch("agents.tutor_graph.retrieve_course_chunks", return_value=[])
    @patch("agents.tutor_graph.generate_grounded_answer")
    def test_model_selected_progress_tool_uses_authenticated_state(
        self,
        generate,
        retrieve,
        resolve,
        fetch_progress,
    ):
        tool_model = FakeLearnerToolModel(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_my_learning_progress",
                        "args": {},
                        "id": "progress_call_1",
                        "type": "tool_call",
                    }
                ],
            )
        )
        fetch_progress.return_value = [
            {
                "topic_slug": "variables-data-types",
                "topic_name": "Variables and Data Types",
                "total_attempts": 5,
                "correct_answers": 4,
                "accuracy_percent": 80,
                "mastery_score": 80,
                "mastery_status": "candidate_for_mastery",
                "last_attempted_at": None,
            }
        ]
        expected = {
            "answer": "You have 80% accuracy in Variables and Data Types.",
            "insufficient_evidence": False,
            "citations": [],
            "retrieved_count": 0,
            "model": "test-model",
            "reason": None,
            "learner_context_used": True,
        }
        generate.return_value = expected
        resolve.side_effect = (
            lambda question, conversation_history, client: question
        )

        graph = build_tutor_graph(
            enable_tools=True,
            tool_model=tool_model,
        )
        state = graph.invoke(
            self._graph_input("How am I doing in Variables and Data Types?")
        )

        self.assertEqual(state["answer_result"], expected)
        fetch_progress.assert_called_once_with(
            user_id=self.USER_ID,
            course_slug="python-basics",
        )
        retrieve.assert_not_called()
        generate.assert_called_once()
        generation_arguments = generate.call_args.kwargs
        self.assertEqual(generation_arguments["retrieved_chunks"], [])
        self.assertEqual(
            generation_arguments["learner_context"]["get_my_learning_progress"]["topics"][0]["accuracy_percent"],
            80,
        )
        self.assertEqual(
            generation_arguments["learner_context"]["get_my_learning_progress"]["topics"][0]["mastery_status"],
            "candidate_for_mastery",
        )

    @patch("agents.learner_tools.fetch_active_study_plan")
    @patch("agents.tutor_graph.resolve_contextual_question")
    @patch("agents.tutor_graph.retrieve_course_chunks", return_value=[])
    @patch("agents.tutor_graph.generate_grounded_answer")
    def test_model_selected_study_plan_tool_returns_plan_data(
        self,
        generate,
        retrieve,
        resolve,
        fetch_plan,
    ):
        tool_model = FakeLearnerToolModel(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_my_study_plan",
                        "args": {},
                        "id": "plan_call_1",
                        "type": "tool_call",
                    }
                ],
            )
        )
        fetch_plan.return_value = {
            "title": "Python Foundations",
            "status": "active",
            "start_date": "2026-11-10",
            "end_date": "2026-11-19",
            "items": [
                {
                    "topic_name": "Variables and Data Types",
                    "topic_slug": "variables-data-types",
                    "activity_type": "revision",
                    "scheduled_date": "2026-11-11",
                    "estimated_minutes": 20,
                    "status": "pending",
                    "recommendation_reason": "Revisit the fundamentals.",
                }
            ],
        }
        generate.return_value = {
            "answer": "Your revision activity is scheduled for November 11.",
            "insufficient_evidence": False,
            "citations": [],
            "retrieved_count": 0,
            "model": "test-model",
            "reason": None,
        }
        resolve.side_effect = (
            lambda question, conversation_history, client: question
        )

        graph = build_tutor_graph(
            enable_tools=True,
            tool_model=tool_model,
        )
        state = graph.invoke(self._graph_input("What is in my study plan?"))

        fetch_plan.assert_called_once_with(
            user_id=self.USER_ID,
            course_slug="python-basics",
        )
        generate.assert_called_once()
        plan_context = generate.call_args.kwargs["learner_context"]
        self.assertEqual(
            plan_context["get_my_study_plan"]["title"],
            "Python Foundations",
        )
        self.assertEqual(
            plan_context["get_my_study_plan"]["activity_counts"]["pending"],
            1,
        )
        self.assertFalse(state["answer_result"]["insufficient_evidence"])


    @patch("agents.learner_tools.fetch_learner_topic_progress")
    @patch("agents.tutor_graph.resolve_contextual_question")
    @patch("agents.tutor_graph.retrieve_course_chunks", return_value=[])
    @patch("agents.tutor_graph.generate_grounded_answer")
    def test_previous_turn_tool_data_is_cleared_in_same_checkpointed_thread(
        self,
        generate,
        retrieve,
        resolve,
        fetch_progress,
    ):
        tool_model = SequenceFakeLearnerToolModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_my_learning_progress",
                            "args": {},
                            "id": "first_progress_call",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="No learner data is needed for this question."),
            ]
        )
        fetch_progress.return_value = [
            {
                "topic_slug": "variables-data-types",
                "topic_name": "Variables and Data Types",
                "total_attempts": 5,
                "correct_answers": 4,
                "accuracy_percent": 80,
                "mastery_score": 80,
                "mastery_status": "candidate_for_mastery",
                "last_attempted_at": None,
            }
        ]
        generate.side_effect = [
            {
                "answer": "Your accuracy is 80%.",
                "insufficient_evidence": False,
                "citations": [],
                "retrieved_count": 0,
                "model": "test-model",
                "reason": None,
                "learner_context_used": True,
            },
            {
                "answer": "Insufficient approved course material.",
                "insufficient_evidence": True,
                "citations": [],
                "retrieved_count": 0,
                "model": "test-model",
                "reason": "no_retrieved_evidence",
            },
        ]
        resolve.side_effect = (
            lambda question, conversation_history, client: question
        )

        graph = build_tutor_graph(
            checkpointer=MemorySaver(),
            enable_tools=True,
            tool_model=tool_model,
        )
        config = {
            "configurable": {
                "thread_id": "22222222-2222-4222-8222-222222222222"
            }
        }

        first_state = graph.invoke(
            self._graph_input("How am I doing in Python?"),
            config=config,
        )
        second_state = graph.invoke(
            self._graph_input("Explain decorators."),
            config=config,
        )

        self.assertIn("learner_context", first_state)
        self.assertTrue(first_state["learner_context"])
        self.assertEqual(second_state["learner_context"], {})
        self.assertTrue(second_state["answer_result"]["insufficient_evidence"])
        self.assertEqual(generate.call_count, 2)
        self.assertIn("learner_context", generate.call_args_list[0].kwargs)
        self.assertNotIn("learner_context", generate.call_args_list[1].kwargs)
        fetch_progress.assert_called_once_with(
            user_id=self.USER_ID,
            course_slug="python-basics",
        )



    @patch("agents.learner_tools.fetch_active_study_plan", return_value=None)
    @patch("agents.tutor_graph.resolve_contextual_question")
    @patch("agents.tutor_graph.retrieve_course_chunks")
    @patch("agents.tutor_graph.generate_grounded_answer")
    @patch("agents.tutor_graph._build_learner_tool_model")
    def test_retries_tool_routing_with_fallback_after_transport_failure(
        self,
        build_model,
        generate,
        retrieve,
        resolve,
        fetch_plan,
    ):
        remote_protocol_error = type(
            "RemoteProtocolError",
            (Exception,),
            {"__module__": "httpx"},
        )
        primary_model = RaisingLearnerToolModel(
            remote_protocol_error("Server disconnected")
        )
        fallback_model = FakeLearnerToolModel(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_my_study_plan",
                        "args": {},
                        "id": "fallback_plan_call",
                        "type": "tool_call",
                    }
                ],
            )
        )
        build_model.side_effect = [primary_model, fallback_model]
        retrieve.return_value = []
        expected = {
            "answer": "You do not have a current study plan.",
            "insufficient_evidence": False,
            "citations": [],
            "retrieved_count": 0,
            "model": "test-model",
            "reason": None,
            "learner_context_used": True,
        }
        generate.return_value = expected
        resolve.side_effect = (
            lambda question, conversation_history, client: question
        )

        graph = build_tutor_graph(enable_tools=True)
        state = graph.invoke(
            self._graph_input("What is in my study plan?")
        )

        self.assertEqual(state["answer_result"], expected)
        self.assertEqual(
            build_model.call_args_list,
            [
                call(GENERATION_MODEL),
                call(FALLBACK_GENERATION_MODEL),
            ],
        )
        self.assertEqual(
            {tool.name for tool in fallback_model.bound_tools},
            {"get_my_learning_progress", "get_my_study_plan"},
        )
        fetch_plan.assert_called_once_with(
            user_id=self.USER_ID,
            course_slug="python-basics",
        )
        retrieve.assert_not_called()
        generate.assert_called_once()
        self.assertIn(
            "get_my_study_plan",
            generate.call_args.kwargs["learner_context"],
        )

    @patch("agents.tutor_graph._build_learner_tool_model")
    def test_tool_router_does_not_fallback_for_client_error(self, build_model):
        client_error = RuntimeError("Invalid API request")
        client_error.code = 403
        build_model.return_value = RaisingLearnerToolModel(client_error)

        graph = build_tutor_graph(enable_tools=True)

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            self.assertRaises(AnswerGenerationError),
        ):
            graph.invoke(
                self._graph_input("What is in my study plan?")
            )

        build_model.assert_called_once_with(GENERATION_MODEL)

    @patch("agents.tutor_graph._build_learner_tool_model")
    def test_tool_router_stops_after_one_fallback_failure(self, build_model):
        primary_error = RuntimeError("Primary model unavailable")
        primary_error.code = 503
        fallback_error = RuntimeError("Fallback model unavailable")
        fallback_error.code = 503
        build_model.side_effect = [
            RaisingLearnerToolModel(primary_error),
            RaisingLearnerToolModel(fallback_error),
        ]

        graph = build_tutor_graph(enable_tools=True)

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            self.assertRaises(AnswerGenerationError),
        ):
            graph.invoke(
                self._graph_input("What is in my study plan?")
            )

        self.assertEqual(
            build_model.call_args_list,
            [
                call(GENERATION_MODEL),
                call(FALLBACK_GENERATION_MODEL),
            ],
        )

    def test_learner_tools_require_authenticated_user_before_model_call(self):
        tool_model = FakeLearnerToolModel(
            AIMessage(content="No learner data is needed.")
        )
        graph = build_tutor_graph(
            enable_tools=True,
            tool_model=tool_model,
        )
        graph_input = self._graph_input("How am I doing?")
        graph_input["user_id"] = None

        with (
            patch(
                "agents.tutor_graph.resolve_contextual_question",
                side_effect=lambda question, conversation_history, client:
                    question,
            ),
            self.assertRaisesRegex(
                ValueError,
                "authenticated learner is required",
            ),
        ):
            graph.invoke(graph_input)

        self.assertEqual(tool_model.bound_tools, [])


if __name__ == "__main__":
    unittest.main()
