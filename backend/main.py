from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mock_agent import AgentState, AgenticOrchestrator
from agent import compile_state_graph, run_agent_sandbox
import json
import asyncio
from langchain_core.messages import AIMessage, ToolMessage

from helper.debug import debug_print

app = FastAPI(
    title="AgentDesk Core API",
    description="Asynchronous backend orchestrating autonomous tool-calling loops."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"], # Allows headers like Content-Type
)

class QueryRequest(BaseModel):
    prompt: str

@app.get("/")
async def root(request: Request):
    docs_url = str(request.base_url) + "docs"
    return {"message": "FastAPI backend is live! Go to $docs_url for API documentation.", "docs_url": docs_url}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/agent/mock")
async def run_mock_agent_loop(payload: QueryRequest):
    if not payload.prompt:
        raise HTTPException(status_code=400, detail="Prompt string cannot be empty.")
    
    # Initialize state and trigger the mock execution engine
    state = AgentState(user_prompt=payload.prompt)
    orchestrator = AgenticOrchestrator(state=state)
    final_state = orchestrator.execute_loop()
    
    return {
        "status": "success",
        "steps": final_state.steps_executed,
        "context_keys": list(final_state.context_data.keys()),
        "output": final_state.final_answer
    }

@app.post("/api/agent/run")
async def run_agent_loop(payload: QueryRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt string cannot be empty.")

    try:
        debug_print(f"Received frontend query: '{payload.prompt}'")
        final_answer = await run_agent_sandbox(payload.prompt)
        return {
            "status": "success",
            "output": final_answer
        }

    except Exception as e:
        debug_print(f"Internal Graph Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occured while executing agent: {str(e)}"
        )

@app.post("/api/agent/stream")
async def stream_agent_loop(payload: QueryRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt string cannot be empty.")
    debug_print(f"Received frontend query: '{payload.prompt}'")

    async def event_generator():
        try:
            # Initialize compiled graph
            compiled_agent = await compile_state_graph()
            initial_input = {"messages": [("user", payload.prompt)]}

            # Stream updates node-by-node out of graph lifecycle
            async for chunk in compiled_agent.astream(initial_input, stream_mode="updates"):
                for node_name, node_update in chunk.items():
                    if "messages" in node_update:
                        for msg in node_update["messages"]:
                            payload_to_send = {}
                            
                            # Model outputs or tool invocation triggers
                            if isinstance(msg, AIMessage):
                                payload_to_send = {
                                    "role": "AI",
                                    "content": msg.content or "",
                                }
                                if msg.tool_calls:
                                    payload_to_send["tool_calls"] = msg.tool_calls

                            # Tool execution results
                            elif isinstance(msg, ToolMessage):
                                tool_identity = getattr(msg, "name", None) or getattr(msg, "tool_call_id", "System Node")
                                payload_to_send = {
                                    "role": f"Tool ({tool_identity})",
                                    "content": msg.content or "[Empty content payload]"
                                }

                            if payload_to_send:
                                yield f"data: {json.dumps(payload_to_send)}\n\n"
                                await asyncio.sleep(0.05)

        except Exception as e:
            debug_print(f"Internal Graph Error: {str(e)}")
            yield f"data: {json.dumps({'role': 'System Error', 'content': f'Runtime breakdown: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")