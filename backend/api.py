from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from mock_agent import AgentState, AgenticOrchestrator
from agent import run_agent_sandbox
import json
import asyncio
from langchain_core.messages import AIMessage, ToolMessage
from helper.debug import debug_print

class QueryRequest(BaseModel):
    prompt: str

def register_agent_routes(api: FastAPI):
    @api.get("/")
    async def root(request: Request):
        docs_url = str(request.base_url) + "docs"
        return {"message": "FastAPI backend is live! Go to $docs_url for API documentation.", "docs_url": docs_url}

    @api.get("/health")
    def health_check():
        return {"status": "healthy"}

    @api.post("/api/agent/mock")
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

    @api.post("/api/agent/run")
    async def run_agent_loop(request: Request, payload: QueryRequest):
        if not payload.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt string cannot be empty.")

        try:
            debug_print(f"Received frontend query: '{payload.prompt}'")
            final_answer = await run_agent_sandbox(
                user_prompt=payload.prompt,
                agent=request.app.state.agent
            )
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

    @api.post("/api/agent/stream")
    async def stream_agent_loop(request: Request, payload: QueryRequest):
        if not payload.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt string cannot be empty.")
        debug_print(f"Received frontend query: '{payload.prompt}'")
        compiled_agent = request.app.state.agent

        async def event_generator():
            try:
                initial_input = {
                    "messages": [("user", payload.prompt)],
                    "iteration_count": 0
                }

                # Stream updates node-by-node out of graph lifecycle
                async for chunk in compiled_agent.astream(
                    initial_input,
                    stream_mode="updates",
                    config={"recursion_limit": 25}
                ):
                    # TODO: Add circuit breaker
                    for node_name, node_update in chunk.items():
                        if "messages" not in node_update:
                            continue

                        # Split the node's message updates into model outputs and tool results
                        ai_messages = [
                            m for m in node_update["messages"]
                            if isinstance(m, AIMessage)
                        ]
                        tool_messages = [
                            m for m in node_update["messages"]
                            if isinstance(m, ToolMessage)
                        ]

                        # 1. Emit Agent/Model reasoning and pending tool-call intents
                        for msg in ai_messages:
                            extracted_content = ""
                            if isinstance(msg.content, list):
                                debug_print(f"AIMessage content is a list with {len(msg.content)} blocks.")
                                for block in msg.content:
                                    if isinstance(block, dict):
                                        if block.get("type") == "text":
                                            extracted_content += block.get("text", "")
                                        elif block.get("type") == "thought": # Check for specific thought blocks
                                            extracted_content += f"\n[THOUGHT]:\n{block.get('thought', '')}\n"
                                    elif isinstance(block, str):
                                        extracted_content += block
                            else:
                                extracted_content = str(msg.content or "")

                            # Some models put thoughts in additional_kwargs or specific fields
                            if not extracted_content.strip():
                                thought = (
                                    msg.additional_kwargs.get("reasoning_content")
                                    or msg.additional_kwargs.get("thought")
                                    or msg.additional_kwargs.get("reasoning")
                                )
                                if thought:
                                    debug_print(f"Found thought in additional_kwargs: {thought[:50]}...")
                                    extracted_content = thought

                            payload_to_send = {
                                "node_name": node_name,
                                "role": "AI",
                                "content": extracted_content.strip(),
                            }
                            if msg.tool_calls:
                                debug_print(f"Tool calls found: {[tc['name'] for tc in msg.tool_calls]}")
                                payload_to_send["tool_calls"] = msg.tool_calls

                            yield f"data: {json.dumps(payload_to_send)}\n\n"
                            await asyncio.sleep(0.05)

                        # 2. Batch all tool results emitted by a single node update into one event
                        if tool_messages:
                            tool_results = []
                            for msg in tool_messages:
                                tool_identity = getattr(msg, "name", None) or getattr(msg, "tool_call_id", "System Node")
                                raw_content = msg.content or "[Empty content payload]"
                                # Normalize structured (list-of-blocks) content to a plain string
                                if isinstance(raw_content, list):
                                    normalized_parts = []
                                    for block in raw_content:
                                        if isinstance(block, dict):
                                            if block.get("type") == "text":
                                                normalized_parts.append(block.get("text", ""))
                                            elif "text" in block:
                                                normalized_parts.append(str(block.get("text", "")))
                                        elif isinstance(block, str):
                                            normalized_parts.append(block)
                                    raw_content = "\n".join(p for p in normalized_parts if p) or "[Empty content payload]"
                                elif not isinstance(raw_content, str):
                                    raw_content = str(raw_content)
                                tool_results.append({
                                    "name": tool_identity,
                                    "content": raw_content
                                })

                            is_distill = node_name == "distill"
                            payload_to_send = {
                                "node_name": node_name,
                                "role": "Distill" if is_distill else "Tools",
                                "is_parallel": len(tool_results) > 1,
                                "tool_results": tool_results,
                            }

                            yield f"data: {json.dumps(payload_to_send)}\n\n"
                            await asyncio.sleep(0.05)

            except Exception as e:
                debug_print(f"Internal Graph Error: {str(e)}")
                yield f"data: {json.dumps({'role': 'System Error', 'content': f'Runtime breakdown: {str(e)}'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")