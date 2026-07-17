from fastapi import FastAPI, HTTPException, Request
# from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mock_agent import AgentState, AgenticOrchestrator
from agent import run_agent_sandbox

app = FastAPI(
    title="AgentDesk Core API",
    description="Asynchronous backend orchestrating autonomous tool-calling loops."
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], # In production, restrict this to your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

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
        print(f"Received frontend query: '{payload.prompt}'")
        final_answer = await run_agent_sandbox(payload.prompt)
        return {
            "status": "success",
            "output": final_answer
        }

    except Exception as e:
        print(f"Internal Graph Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occured while executing agent: {str(e)}"
        )