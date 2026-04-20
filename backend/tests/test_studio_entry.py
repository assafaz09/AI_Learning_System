"""Studio entry graphs are importable (same builders as FastAPI)."""


def test_studio_entry_exports_compiled_graphs():
    from app.agents import studio_entry as se

    assert se.teacher_chat_graph is not None
    assert se.quiz_generate_graph is not None
    assert se.podcast_script_graph is not None
