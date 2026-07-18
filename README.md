# AgentDesk

## Run the App

1. python tools.py
2. uvicorn main:app --port 8001 --reload
3. npm run dev

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
- Docker
- Unit Testing

## Challenges encountered / Enhancements made:

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

Refer to [DEMO.md](DEMO.md) for example prompt and response.
