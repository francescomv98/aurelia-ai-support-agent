import pytest
from langgraph.checkpoint.memory import MemorySaver

@pytest.mark.integration
def test_memory_checkpointer_setup():
    checkpointer = MemorySaver()

    assert checkpointer is not None
    assert callable(checkpointer.get)
    assert callable(checkpointer.put)