"""Compiled graphs for LangGraph Studio (`langgraph dev`) and LangSmith Deployments.

Run from the `backend` directory with repo-root `.env` (see `langgraph.json`):

  pip install -r requirements-dev.txt
  langgraph dev

Studio / CLI loads graphs listed in `langgraph.json` from the variables below.
Uses the same VectorStore and graph builders as the FastAPI app.
"""

from __future__ import annotations

from app.agents.graphs.documents import _build_index_graph
from app.agents.graphs.podcast import _build_podcast_script_graph
from app.agents.graphs.quiz import _build_quiz_generate_graph
from app.agents.graphs.teacher import _build_project_ideas_graph, _build_teacher_chat_graph
from app.services.vector_store import VectorStore

_vector_store = VectorStore()

teacher_chat_graph = _build_teacher_chat_graph(_vector_store)
project_ideas_graph = _build_project_ideas_graph(_vector_store)
document_index_graph = _build_index_graph(_vector_store)
quiz_generate_graph = _build_quiz_generate_graph()
podcast_script_graph = _build_podcast_script_graph()
