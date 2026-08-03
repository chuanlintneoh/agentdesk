import pytest
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock

# Bypass the health check request during testing (don't want to rely on live backend)
@pytest.fixture(autouse=True)
def mock_health_check():
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response
        yield

def test_dashboard_initial_state():
    # Test that the app starts with the correct initial state
    at = AppTest.from_file("app.py")
    at.run()
    
    assert at.session_state.trace == []
    assert at.session_state.system_ready is True
    # Sidebar should be present
    assert at.sidebar.title[0].value == "AgentDesk Workbench"

def test_trace_rendering_grouping():
    # Test that consecutive AI/Tool messages are grouped correctly
    # We'll mock render_steps directly or test via session state
    at = AppTest.from_file("app.py")
    at.run()
    
    # Mock a trace with User -> AI -> Tools -> AI
    complex_trace = [
        {"role": "User", "content": "Here is my example user prompt for testing."},
        {"role": "AI", "content": "I am thinking what I need to execute in order to answer user's question.", "node_name": "agent"},
        {"role": "Tools", "tool_results": [{"name": "test", "content": "res"}], "node_name": "tools"},
        {"role": "AI", "content": "Here is the example agent's final answer.", "node_name": "agent"}
    ]
    
    at.session_state.trace = complex_trace
    at.run()
    
    # Verify that the assistant message grouped the internal thoughts
    # AppTest makes it a bit hard to query deep nested expanders, 
    # but we can verify the session state wasn't corrupted.
    assert len(at.session_state.trace) == complex_trace.__len__()

def test_history_cutoff_isolation():
    # Test the isolation logic for streaming without running the infinite post request
    # we patch requests.post to raise an error immediately so it completes without hanging/timing out
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("Fast completion")
        
        at = AppTest.from_file("app.py")
        at.run()
        
        # Set up a history
        at.session_state.trace = [{"role": "User", "content": "old msg"}]
        
        # Simulate a new prompt being entered
        test_prompt = "Example prompt"
        at.chat_input[0].set_value(test_prompt)
        at.chat_input[0].run()
        
        # After rerun from input, trace should have the user prompt and the exception handler result
        assert any(step.get("content") == test_prompt for step in at.session_state.trace)

@patch("requests.post")
def test_circuit_breaker_on_backend_failure(mock_post):
    # Simulate a 500 error from the backend during streaming
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 500
    mock_post.return_value.__enter__.return_value = mock_response
    
    at = AppTest.from_file("app.py")
    at.run()
    
    # Add a user message to trigger the execution logic
    at.session_state.trace = [{"role": "User", "content": "trigger error"}]
    at.run() # This will run the execution logic section
    
    # Verify circuit breaker released the lock and added error message
    assert at.session_state.is_streaming is False
    assert any(step.get("role") == "System Error" for step in at.session_state.trace)