# AgentDesk

<img width="1365" height="592" alt="Streamlit Dashboard" src="https://github.com/user-attachments/assets/abfd3ffc-53c5-47ac-9ae7-2bb77b9275f2" />
<img width="934" height="566" alt="NextJS Frontend" src="https://github.com/user-attachments/assets/760dd6ec-9326-4cf2-bbd0-09019db1d3da" />

## Run the App

1.  Run script to setup example databases (in the `backend/` directory):
    ```bash
    python scripts/db_setup.py
    ```
2.  Copy `.env.example` to `.env` and configure your `GROQ_API_KEY`:
    ```bash
    cp .env.example .env
    ```
3.  Run backend and frontend services:
    - Option A: Using Docker Compose (Recommended for Production & Local Testing)
      - Backend server only
        ```bash
        docker compose up --build
        ```
      - Backend server and Streamlit dashboard
        ```bash
        docker compose --profile streamlit up --build
        ```
      - Backend server and NextJS frontend
        ```bash
        docker compose --profile nextjs up --build
        ```
      - Backend server, NextJS frontend and Streamlit dashboard
        ```bash
        docker compose --profile all up --build
        ```
    - Option B: Local Development
      1. Start backend service with ASGI-mounted FastMCP server (in the `backend/` directory)
         ```bash
         uvicorn main:app --port 8000 --reload
         ```
      2. Run frontend service
         - Streamlit dashboard (in the `dashboard/` directory)
           ```bash
           streamlit run app.py
           ```
         - NextJS frontend (in the `frontend/` directory)
           ```bash
           npm run dev
           ```
4.  Launch:
    - Click [here](http://localhost:8000/docs) to access FastAPI server documentations:
      `http://localhost:8000/docs`
    - Click [here](http://localhost:3000) to access NextJS frontend:
      `http://localhost:3000`
    - Click [here](http://localhost:8501) to access Streamlit dashboard:
      `http://localhost:8501`

## System Description

Technologies:

- FastAPI
- SwaggerUI / OpenAPI schemas
- LLMs
- LangChain
- LangGraph
- Dynamic RAG
- Prompt Engineering
- Tool / Function Calling
- MCP
- SQL
- Vector database
- Next.js
- React
- TypeScript
- JavaScript
- HTML
- TailwindCSS
- Streamlit
- Docker / Docker Compose
- Unit Testing

## Run Test Scripts

- Backend Server
  ```bash
  cd backend/
  source benv/Scripts/activate
  pytest
  ```
- Streamlit Dashboard
  ```bash
  cd dashboard/
  source denv/Scripts/activate
  pytest
  ```

## Challenges Encountered & Enhancements Made

1. Token limit system crash
   - what: Frequent hit of rate limit exceeded error when answering a complex multi-step query
   - when: Agent fall deep into analysis loop
   - why: Agent dumping massive tables into chat history, rolling memory snowball
   - how: Add text trimmer to slice huge data contents

2. Blind SQL db querying
   - what: AI writing broken SQL queries causing runtime errors
   - when: Agent try pulling data from new table without knowing what fields are available
   - why: Agent blindly guessing column names
   - how: Rewrite system instructions to force "look before you leap" rule

3. Distillation node
   - what: Hitting TPM limit during complex queries
   - when: Main model tries to process massive raw text payloads from tool results
   - why: Tool payloads consume too many tokens, triggering rate limits on subsequent steps
   - how: Introduce a distillation node to summarize and compress raw data before passing it back to the main model

4. Database blueprint lookup
   - what: AI blindly querying tables it doesn't know the structure of
   - when: Attempting to pull columns from empty or newly created tables
   - why: tool provided only returned table names, but left column names a mystery
   - how: Upgraded to a full blueprint lookup tool that spits out both tables and their column schemas (with data types)

5. Hard to debug AI reasoning
   - what: Hard to debug or refine agent behaviors without knowing why the AI chose a tool
   - when: Diagnosing why the AI made a wrong decision, loop, or empty lookup
   - why: Pure API logs don't reveal the agent's internal logic and strategy
   - how: Enforced a strict Chain of Thought rule requiring the AI to output its structural reasoning before calling tools, display it in the frontend, and use those outputs to refine system instructions

Refer to [DEMO.md](DEMO.md) for example prompt and response.
