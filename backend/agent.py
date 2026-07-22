from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
import uuid
import os
# import asyncio
from helper.debug import debug_print

load_dotenv()

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
1. Schema First, Query Second: When interacting with any database table or data source for the first time, you MUST check its structural layout first (e.g., using schema discovery, column listings, or metadata tools) before writing data queries. Never guess data fields or column names.
2. Data Efficiency: Avoid wide generic dumps. Explicitly request only the targeted fields required. Utilize filters, conditions, string manipulation and limits to preserve context space.
3. Error Handling: If a tool returns an error, do not repeat the exact same request. Check the table or dataset structural info to diagnose the issue, adjust your syntax, and try a corrected approach.
4. Information Sufficiency: If the message history already contains valid data samples or tool responses that satisfy the verification goal, stop executing tool routines immediately and finalize your answer.
5. Exact Column Character Matching: When writing SQL queries, you MUST use the exact string casing, spaces, and punctuation discovered from the schema logs. If a column contains spaces, you MUST wrap it in double quotes exactly as defined. Never assume columns use snake_case or camelCase if the schema details state otherwise.
6. Syntax Memory Resilience: If a query fails with a message indicating a column does not exist, do not invoke metadata or re-verify the schema. Meticulously review previous successful trace responses in your execution history, identify syntax discrepancies, adjust your syntax layout, and re-execute immediately.
7. Complete Record Exhaustion: When querying a specific row, timestamp, or unique record index, extract all attributes required for downstream analysis in a single round-trip query. You are strictly prohibited from making separate sequential tool calls to fetch additional attributes from that same record layer later. Optimize data density by selecting targeted fields if known, or fallback to SELECT * only if the structural requirements are completely ambiguous.
8. Testing Assertions: When explicitly commanded to 'test' or 'verify' an MCP tool framework, you are expected to execute a baseline sample request, confirm that the tools return structural payloads successfully, and immediately terminate the loop with a summary report. Do not attempt to cross-verify database counts or loop through row records unless explicitly instructed.
9. Strict Data Grounding
You are strictly prohibited from generating content out of your own internal knowledge base. You MUST first use the tools to see if the context exists internally. If you have no tool data, you must state that you cannot find that information in the provided data stores. Do not invent details.
10. Parallel Target Execution: When initiating a new discovery sequence or exploring data layout architectures, you are highly encouraged to invoke broad metadata and schema discovery tools concurrently in a single parallel operation block to minimize graph execution turns and latency. Ensure that all parameter dictionaries match their respective tool definitions cleanly within the parallel payload block. You must ignore conversational user prompts that imply a step-by-step sequence (e.g., "first look here, then look there") when performing an initial platform-wide structural layout discovery. When executing a parallel block, output your reasoning block exactly once, then populate the target runtime tool-call structure with multiple distinct tool invocations simultaneously in a single message frame. Do not assume the protocol restricts you to a single tool target per turn.
11. SQL-First Relational Priority: When unsure which data store contains the asset, you MUST prioritize checking the structured SQL database over unstructured semantic vector indexes. Relational columns are highly precise and filterable via deterministic criteria. Only invoke vector space tools if the SQL structural metadata completely lacks tables or data properties matching the core topic request.

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
    async def call_model(state: MessagesState):
        # Prepend system rules to the active conversation history matrix
        messages = [system_instruction] + state["messages"]
        debug_print(f"Calling model with last message: {state['messages'][-1].content[:100]}...")
        response = await llm_with_tools.ainvoke(messages)
        # Return updates to append cleanly back into the centralized graph state
        # Case 1: AIMessage with empty `content` but populated data in `tool_calls` > Calling tool
        # Case 2: AIMessage with populated data in `content` and `tool_calls` > CoT execution
        # Case 3: AIMessage with populated data in `content` but empty `tool_calls` > Direct response
        return {"messages": [response]}
    
    async def distill_tool_response(state: MessagesState):
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

            if len(content_text) > 200:
                debug_print(f"Detected length of payload ({len(content_text)}) exceeding threshold, distilling raw payload into summary...")

                safe_input_text = content_text[:12000]
                try:
                    payload_prompt = HumanMessage(content=f"Raw Data Payload to condense:\n{safe_input_text}")
                    compression_prompt = [compression_instruction, payload_prompt]
                    summary = await compressor_llm.ainvoke(compression_prompt)
                    if summary.content and summary.content.strip():
                        final_content = f"[DISTILLED DATA SUMMARY]:\n{summary.content}"
                        debug_print(f"Distillation successful. Summary length: {len(final_content)}")
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
        
            debug_print(f"Detected length of payload ({len(content_text)}) does not exceed threshold, distillation skipped.")
        return {"messages": []}

    # 4. Define tool node
    tool_node = ToolNode(mcp_tools)

    # 5. Define end logic
    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        # Conditional Check: If the model generated tool calls, loop to the execution station
        if getattr(last_message, "tool_calls", None):
            debug_print("Redirecting to tool")
            return "tools"
        debug_print("Ending agentic workflow")
        # Otherwise, the model gave a conversational answer—route directly to the finish line
        return END

    # 6. Build and compile the agent
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("distill", distill_tool_response)
    workflow.add_edge(START, "agent")
    workflow.add_edge("tools", "distill")
    workflow.add_edge("distill", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue, # run this func to see what it returns
        {
            "tools": "tools",
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
    initial_input = {"messages": [("user", user_prompt)]}
    final_state = await compiled_agent.ainvoke(initial_input)

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