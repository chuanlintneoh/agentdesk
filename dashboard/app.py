import streamlit as st
import os
import requests
import json

# Page Configuration
st.set_page_config(page_title="AgentDesk Workbench", layout="wide")

FASTAPI_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# Initialize session state variables
if "trace" not in st.session_state:
    st.session_state.trace = []
if "system_ready" not in st.session_state:
    st.session_state.system_ready = True

with st.sidebar:
    st.title("AgentDesk Workbench")
    st.divider()
    st.markdown(f"**Host:** `{FASTAPI_URL.replace('http://', '')}`")

    # Health Check
    @st.fragment(run_every=30)
    def sync_health_status():
        try:
            response = requests.get(f"{FASTAPI_URL}/health", timeout=2)
            st.session_state.system_ready = response.ok
        except:
            st.session_state.system_ready = False

        st.markdown(f"**System Status:** `{'🟢 Online' if st.session_state.system_ready else '🔴 Offline'}`")
    sync_health_status()

def render_steps(trace_list):
    if not trace_list:
        return

    # Iterate through the history
    idx = 0
    while idx < len(trace_list):
        step = trace_list[idx]
        role = step.get("role", "Unknown")

        if role == "System Error":
            st.error(f"Backend Pipeline Error: {step.get('content')}")
            idx += 1
            continue
        
        # Handle standard user messages directly
        if role == "User":
            with st.chat_message("user"):
                st.markdown(step["content"])
            idx += 1
            continue
            
        # Collect all adjacent internal agent steps/tools into a list
        thinking_steps = []
        final_text_content = ""
        
        while idx < len(trace_list) and trace_list[idx].get("role") not in ["User", "System Error"]:
            current_step = trace_list[idx]
            
            # If a step contains tools OR does not have a standard text string answer,
            # it belongs inside the agent's internal thinking loop
            if current_step.get("tool_calls") or current_step.get("tool_results") or not current_step.get("content"):
                thinking_steps.append(current_step)
            else:
                # Capture the final text block to render underneath
                final_text_content = current_step.get("content", "")
            idx += 1
            
        # Render the grouped Assistant block
        if thinking_steps or final_text_content:
            with st.chat_message("assistant"):
                # If the agent thought or called tools, wrap them in the parent expander
                if thinking_steps:
                    with st.expander("Agent Execution History & Core Thinking Logs", expanded=False):
                        for t_idx, t_step in enumerate(thinking_steps):
                            node_name = t_step.get("node_name", f"Step {t_idx + 1}")
                            st.caption(f"Node Instance: {node_name}")
                            
                            # Nested Expander 1: Tool Calls
                            if t_step.get("tool_calls"):
                                with st.expander(f"Tool Invocations ({len(t_step['tool_calls'])})", expanded=True):
                                    for tc in t_step["tool_calls"]:
                                        st.code(f"{tc.get('name')}(**{json.dumps(tc.get('args'), indent=2)})", language="python")
                            
                            # Nested Expander 2: Tool Results
                            if t_step.get("tool_results"):
                                with st.expander(f"Tool Results ({len(t_step['tool_results'])})", expanded=False):
                                    for tr in t_step["tool_results"]:
                                        st.write(f"**{tr.get('name')}**")
                                        st.code(tr.get("content"), language="text")
                                        
                            # Include intermediate thinking thoughts if present
                            if t_step.get("content"):
                                st.info(t_step["content"])
                # Render the final structural markdown response outside/underneath the thinking block
                if final_text_content:
                    st.markdown(final_text_content)

render_steps(st.session_state.trace)

# Chat Input
if prompt := st.chat_input("Enter a multi-step analytical command...", disabled=not st.session_state.system_ready):
    # Add user message to trace and clear for execution
    st.session_state.trace.append({"role": "User", "content": prompt})
    st.rerun()

# Execution Logic
if (st.session_state.trace
    and st.session_state.trace[-1]["role"] == "User"
    and not st.session_state.get("is_streaming", False)):

    user_prompt = st.session_state.trace[-1]["content"]
    stream_container = st.empty()

    st.session_state.is_streaming = True

    history_cutoff = len(st.session_state.trace)

    try:
        with requests.post(
            f"{FASTAPI_URL}/api/agent/stream",
            json={"prompt": user_prompt},
            stream=True
        ) as r:
            if not r.ok:
                raise Exception("Server communication broken.")
            
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        data = json.loads(decoded_line[6:])
                        
                        # Append the incoming trace step object to history
                        st.session_state.trace.append(data)
                        
                        # Dynamically group, isolate, and redraw everything in place
                        with stream_container.container():
                            render_steps(st.session_state.trace[history_cutoff:])
                            
        # Connection finished cleanly. Seal layouts permanently.
        st.session_state.is_streaming = False
        stream_container.empty()
        st.rerun()
        
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        st.session_state.trace.append({"role": "System Error", "content": str(e)})
        st.session_state.is_streaming = False
        stream_container.empty()
        st.rerun()