from src.agent.checkpointer import create_checkpointer

def test_postgres_checkpointer_setup():
    checkpointer = create_checkpointer()

    assert checkpointer is not None