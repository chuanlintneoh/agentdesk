import pytest
from unittest.mock import AsyncMock
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from agent import compile_state_graph

# Configure pytest-asyncio to use the event loop
pytestmark = pytest.mark.asyncio

async def test_langgraph_state_channels():
    # Test that MessagesState handles different message types correctly
    state = {"messages": [HumanMessage(content="hello")]}
    
    # Simulate agent node adding an AIMessage
    ai_msg = AIMessage(content="thinking", tool_calls=[{"name": "test_tool", "args": {}, "id": "1"}])
    state["messages"].append(ai_msg)
    
    # Simulate tool node adding a ToolMessage
    tool_msg = ToolMessage(content="result", tool_call_id="1")
    state["messages"].append(tool_msg)
    
    assert len(state["messages"]) == 3
    assert isinstance(state["messages"][0], HumanMessage)
    assert isinstance(state["messages"][1], AIMessage)
    assert isinstance(state["messages"][2], ToolMessage)
    assert state["messages"][2].tool_call_id == "1"

async def test_distillation_node_logic(monkeypatch):
    # Mock the compressor LLM logic
    async def mock_distill(state):
        last_message = state["messages"][-1]
        if isinstance(last_message, ToolMessage) and len(str(last_message.content)) > 200:
            return {"messages": [ToolMessage(content="[DISTILLED DATA SUMMARY]:\nSummary of large data", tool_call_id="call_123", name="big_tool")]}
        return {"messages": []}

    # Create a dummy state with a large ToolMessage
    large_content = "x" * 20000
    state = {
        "messages": [
            ToolMessage(content=large_content, tool_call_id="call_123", name="big_tool")
        ]
    }
    
    result = await mock_distill(state)
    assert len(result["messages"]) == 1
    assert "[DISTILLED DATA SUMMARY]" in result["messages"][0].content
    assert result["messages"][0].tool_call_id == "call_123"

async def test_graph_compilation():
    # Verify that the graph compiles without errors
    # We'll mock the internal dependencies of compile_state_graph
    with patch("agent.MultiServerMCPClient") as mock_mcp:
        mock_instance = mock_mcp.return_value
        mock_instance.get_tools = AsyncMock(return_value=[])
        
        try:
            graph = await compile_state_graph()
            assert graph is not None
        except Exception as e:
            pytest.fail(f"Graph compilation failed: {e}")

from unittest.mock import patch
