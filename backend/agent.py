from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
import tiktoken
from typing import Any, Literal
import uuid
import os
# import asyncio
from helper.debug import debug_print

load_dotenv()

# intercept when agent hits this number of tool invocations
MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", 8))
# send raw payload to distillation if it exceeds this token count
MAX_PAYLOAD_LENGTH = int(os.getenv("MAX_PAYLOAD_LENGTH", 200))
# length of raw payload to send to distillation
MAX_DISTILLATION_LENGTH = int(os.getenv("MAX_DISTILLATION_LENGTH", 12000))
# fallback truncation length if distillation fails
# MANUAL_TRUNCATION_LENGTH = int(os.getenv("MANUAL_TRUNCATION_LENGTH", 6000))

tokenizer = tiktoken.get_encoding("cl100k_base")
def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text))

class AgentState(MessagesState):
    iteration_count: int = 0

async def compile_state_graph() -> CompiledStateGraph:
    debug_print("Initializing Multi-Server MCP Gateway & Custom Orchestration Graph...")

    mcp_token = os.getenv("MCP_SECRET_TOKEN", "secret-token-default")
    client = MultiServerMCPClient({
        "core_utility_server": {
            "transport": "http",
            "url": "http://localhost:8000/mcp/",
            "headers": {
                "X-MCP-Token": mcp_token
            }
        }
    })

    # 1. Define tools and model
    mcp_tools = await client.get_tools()
    debug_print(f"Auto-discovered {len(mcp_tools)} tools from FastMCP server.")
    # https://console.groq.com/docs/rate-limits
    # llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0) # deprecate 17/7/2026
    # llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0) # deprecate 16/8/2026
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    # llm = ChatGroq(model="qwen/qwen3.6-27b", temperature=0)
    compressor_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)

    llm_with_tools = llm.bind_tools(mcp_tools)
    system_instruction = SystemMessage(
        content=
        """# Role & Objective
You are AgentDesk, an autonomous, highly capable AI Agent designed to solve complex data tasks. Your primary objective is to achieve the user's goal by strictly following a cyclical process of reasoning, exploring data structures, executing actions via configured tools, and validating outcomes.

# Execution Rules & Guidelines
1. Schema Verification Absolute Priority: When interacting with any database table or data source for the first time, or if a significant gap in time/context has passed, you MUST explicitly execute a schema discovery or column listing tool FIRST. You are strictly prohibited from writing data queries based on assumed, standard, or common column names. If you do not see the column explicitly listed in a prior tool response in the current chat history, you do not know it exists.
2. Data Efficiency: Avoid wide generic dumps. Explicitly request only the targeted fields required. Utilize filters, conditions, string manipulation and limits to preserve context space.
3. Error Handling: If a tool returns an error, do not repeat the exact same request. Check the table or dataset structural info to diagnose the issue, adjust your syntax, and try a corrected approach.
4. Information Sufficiency: If the message history already contains valid data samples or tool responses that satisfy the verification goal, stop executing tool routines immediately and finalize your answer.
5. Exact Column Character Matching: When writing SQL queries, you MUST use the exact string casing, spaces, and punctuation discovered from the schema logs. If a column contains spaces, you MUST wrap it in double quotes exactly as defined. Never assume columns use snake_case or camelCase if the schema details state otherwise.
6. Schema-Driven Corrections: If a query fails due to a missing column, do not attempt to guess a replacement column. Review the exact schema log details previously returned by your metadata tools. If the required information cannot be mapped to an existing schema column, fallback to querying only the verified baseline columns or use a wildcard discovery check if allowed, rather than guessing data fields.
7. Complete Record Exhaustion: When querying a specific row, timestamp, or unique record index, extract all attributes required for downstream analysis in a single round-trip query. You are strictly prohibited from making separate sequential tool calls to fetch additional attributes from that same record layer later. Optimize data density by selecting targeted fields if known, or fallback to SELECT * only if the structural requirements are completely ambiguous.
8. Testing Assertions: When explicitly commanded to 'test' or 'verify' an MCP tool framework, you are expected to execute a baseline sample request, confirm that the tools return structural payloads successfully, and immediately terminate the loop with a summary report. Do not attempt to cross-verify database counts or loop through row records unless explicitly instructed.
9. Strict Data Grounding
You are strictly prohibited from generating content out of your own internal knowledge base. You MUST first use the tools to see if the context exists internally. If you have no tool data, you must state that you cannot find that information in the provided data stores. Do not invent details.
10. Comprehensive Parallel Discovery: When starting an objective, you MUST execute schema and environment discovery tools across ALL relevant data store modalities simultaneously in a single parallel call block. You are strictly prohibited from limiting initial discovery to a single data store type if the prompt requests attributes spanning multiple content types.
11. Multi-Source & Modality Mapping: User prompts often require combining structured data and unstructured content. You MUST analyze the prompt to identify all required content types and map them against the capabilities/descriptions of ALL available tool suites. Never assume one data store contains all necessary modalities.
12. Exhaustive Cross-Store Verification: If a specific data asset is not present in the schema of one data store, you MUST discover and query the schemas/indexes of your other configured data stores before concluding the data is unavailable or falling back to summarizing partial/proxy fields.

# Analytical Protocol (Mandatory Chain of Thought)
Before executing ANY tool call, you MUST output an explicit, concise text reasoning block explaining your structural analysis. You must answer:
1. What specific pieces of data are still missing to achieve the user's objective?
2. Exactly why the chosen tool and query parameters are the most optimal way to extract that data.
3. Verify that your planned parameters will not return empty or redundant payloads. Never execute empty lookups (like 'LIMIT 0') or duplicate queries.
Only after writing this thought block are you allowed to invoke the tool parameters.

# Tone & Style
- Be objective, analytical, and highly precise when describing metrics and data relationships.
- Present final answers in a professional, clear, and well-structured format using markdown tables where relevant.
- Do not mix conversational filler into raw data payloads or parameters."""
    )
    compression_instruction = SystemMessage(
        content=
        """You are a text compression engine. Condense the following raw data payload into a highly comprehensive bulleted summary. Retain ALL exact numerical values, dates, and structural column names, but eliminate raw formatting, whitespace, and JSON syntax."""
    )

    # 2. Define state
    # Handled inside StateGraph initialization in step 6

    # 3. Define model node
    async def call_model(state: AgentState) -> dict[str, Any]:
        # Prepend system rules to the active conversation history matrix
        messages = [system_instruction] + state["messages"]
        debug_print(f"Calling model with last message: {state['messages'][-1].content[:100]}...")
        response = await llm_with_tools.ainvoke(messages)
        current_count = state.get("iteration_count", 0)
        next_count = current_count + 1 if response.tool_calls else current_count
        # Return updates to append cleanly back into the centralized graph state
        # Case 1: AIMessage with empty `content` but populated data in `tool_calls` > Calling tool
        # Case 2: AIMessage with populated data in `content` and `tool_calls` > CoT execution
        # Case 3: AIMessage with populated data in `content` but empty `tool_calls` > Direct response
        return {
            "messages": [response],
            "iteration_count": next_count
        }
    
    async def distill_tool_response(state: AgentState) -> dict[str, Any]:
        last_message = state["messages"][-1]

        # Intercept if the newly returned payload is too heavy
        if isinstance(last_message, ToolMessage):
            content_text = ""
            if isinstance(last_message.content, list) and len(last_message.content) > 0:
                # If it's wrapped in a LangGraph structured list, grab the text attribute
                content_text = last_message.content[0].get("text", "")
            else:
                # Fallback to standard string translation
                content_text = str(last_message.content)

            token_count = count_tokens(content_text)
            if token_count > MAX_PAYLOAD_LENGTH:
                debug_print(f"Detected token count of payload ({token_count}) exceeding threshold, distilling raw payload into summary...")

                safe_input_text = content_text[:MAX_DISTILLATION_LENGTH]
                try:
                    payload_prompt = HumanMessage(content=f"Raw Data Payload to condense:\n{safe_input_text}")
                    compression_prompt = [compression_instruction, payload_prompt]
                    summary = await compressor_llm.ainvoke(compression_prompt)
                    extracted_summary = summary.content or summary.additional_kwargs.get("thought", "")
                    if extracted_summary and extracted_summary.strip():
                        final_content = f"[DISTILLED DATA SUMMARY]:\n{extracted_summary.strip()}"
                        debug_print(f"Distillation successful. Summary token count: {count_tokens(final_content)}")
                    else:
                        debug_print("Compressor LLM returned an empty summary content block. Falling back to safe programmatic truncation.")
                        raise ValueError("Compressor LLM returned an empty summary content block.")
                except Exception as e:
                    debug_print(f"Distillation LLM failure or token block: {str(e)}. Falling back to safe programmatic truncation.")
                    final_content = f"[TRUNCATED DATA PAYLOAD - SIZE LIMIT EXCEEDED]:\n{safe_input_text}\n... [Remaining data clipped to fit token window]"
                
                message_id = getattr(last_message, "id", None) or str(uuid.uuid4())
                distilled_message = ToolMessage(
                        content=final_content,
                        tool_call_id=last_message.tool_call_id,
                        name=getattr(last_message, "name", "distill"),
                        status=getattr(last_message, "status", "success"),
                        id=message_id
                    )
                return {"messages": [distilled_message]}
        
            debug_print(f"Detected token count of payload ({token_count}) does not exceed threshold, distillation skipped.")
        return {"messages": []}

    async def circuit_breaker(state: AgentState) -> dict[str, Any]:
        fallback_prompt = SystemMessage(
            content=(
                f"The tool execution threshold ({MAX_TOOL_ITERATIONS} rounds) has been reached. "
                "Synthesize a final response based solely on the data retrieved so far. "
                "Clearly list what was verified and mention what remains incomplete."
            )
        )
        
        cleaned_history = list(state["messages"])
        if cleaned_history and isinstance(cleaned_history[-1], AIMessage) and cleaned_history[-1].tool_calls:
            if cleaned_history[-1].content:
                cleaned_history[-1].content = AIMessage(content=str(cleaned_history[-1].content))
            else:
                cleaned_history.pop()
        # Call base LLM directly (without tools bound) to force text generation
        final_summary = await llm.ainvoke([fallback_prompt] + cleaned_history)
        return {"messages": [final_summary]}

    # 4. Define tool node
    tool_node = ToolNode(mcp_tools)

    # 5. Define end logic
    def should_continue(state: AgentState) -> Literal["tools", "circuit_breaker", "__end__"]:
        last_message = state["messages"][-1]
        # Conditional Check: If the model generated tool calls, loop to the execution station
        if getattr(last_message, "tool_calls", None):
            if state.get("iteration_count", 0) >= MAX_TOOL_ITERATIONS:
                debug_print(f"Circuit breaker triggered: Exceeded {MAX_TOOL_ITERATIONS} iterations.")
                return "circuit_breaker"
            debug_print("Redirecting to tool")
            return "tools"
        debug_print("Ending agentic workflow")
        # Otherwise, the model gave a conversational answer—route directly to the finish line
        return END

    # 6. Build and compile the agent
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("distill", distill_tool_response)
    workflow.add_node("circuit_breaker", circuit_breaker)
    workflow.add_edge(START, "agent")
    workflow.add_edge("tools", "distill")
    workflow.add_edge("distill", "agent")
    workflow.add_edge("circuit_breaker", END)
    workflow.add_conditional_edges(
        "agent",
        should_continue, # run this func to see what it returns
        {
            "tools": "tools",
            "circuit_breaker": "circuit_breaker",
            END: END
        } # map the func result to the next dest
    )
    compiled_agent = workflow.compile()
    debug_print("Agent compiled successfully.")
    return compiled_agent
    
async def run_agent_sandbox(user_prompt: str) -> str:
    compiled_agent = await compile_state_graph()
    debug_print(f"Dispatching graph execution loop for instruction: '{user_prompt}'...\n")
    # Execute the runtime system
    initial_input = {
        "messages": [("user", user_prompt)],
        "iteration_count": 0
    }
    final_state = await compiled_agent.ainvoke(
        initial_input,
        config={"recursion_limit": 25}
    )

    debug_print("\nComplete Execution Steps")
    for i, message in enumerate(final_state["messages"], 1):
        # Determine the role actor name
        role = message.__class__.__name__.replace("Message", "")
        
        # Check if the message is an AIMessage with tool calling intentions
        tool_calls_str = ""
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls_str = f"[Triggers Tools: {', '.join([tc['name'] for tc in message.tool_calls])}]"

        debug_print(f"\n[Step {i}] {role}:{tool_calls_str}")
        debug_print("-" * 30)
        debug_print(message.content or "[Empty content payload - Check tool_calls or metadata]")

    return final_state["messages"][-1].content

# if __name__ == "__main__":
#     generic_test_prompt = (
#         "Analyze the financial trajectory of the company represented in the database. "
#         "Calculate its key financial efficiency or profitability margins across all available "
#         "historical periods, and evaluate whether the qualitative operational narrative in the "
#         "internal corporate text records aligns with or contradicts these empirical trends."
#     )
#     asyncio.run(run_agent_sandbox(generic_test_prompt))