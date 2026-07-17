import os
import asyncio
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

async def run_agent_sandbox(user_prompt: str) -> str:
    print("Initializing Multi-Server MCP Gateway & Custom Orchestration Graph...")

    # client = MultiServerMCPClient({
    #     "core_utility_server": {
    #         "command": "python",
    #         "args": [os.path.abspath("tools.py")],
    #         "transport": "stdio"
    #     }
    # })
    client = MultiServerMCPClient({
        "core_utility_server": {
            "transport": "http",
            "url": "http://localhost:8000/mcp"
        }
    })

    # 1. Define tools and model
    mcp_tools = await client.get_tools()
    print(f"Auto-discovered {len(mcp_tools)} tools from FastMCP server.")
    # https://console.groq.com/docs/rate-limits
    # llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0)
    llm_with_tools = llm.bind_tools(mcp_tools)
    system_instruction = SystemMessage(
        content= (
            "You are an advanced agent assistant named AgentDesk.\n"
            "You have access to structured relational databases via SQL and unstructured documentation via RAG tools.\n"
            "Analyze the user's prompt, dynamically call the appropriate tools to collect the necessary facts, "
            "and synthesize a clean, precise response based strictly on the retrieved data.\n\n"
            "CRITICAL: When choosing to invoke a tool, you must format the arguments as a "
            "strict, valid JSON object matching the tool's schema exactly. Do not add raw text, "
            "malformed syntax, or unescaped characters inside the tool argument blocks."
        )
    )

    # 2. Define state
    # Handled inside StateGraph initialization in step 6

    # 3. Define model node
    async def call_model(state: MessagesState):
        # Prepend system rules to the active conversation history matrix
        messages = [system_instruction] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        # Return updates to append cleanly back into the centralized graph state
        return {"messages": [response]}

    # 4. Define tool node
    tool_node = ToolNode(mcp_tools)

    # 5. Define end logic
    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        # Conditional Check: If the model generated tool calls, loop to the execution station
        if getattr(last_message, "tool_calls", None):
            return "tools"
        # Otherwise, the model gave a conversational answer—route directly to the finish line
        return END

    # 6. Build and compile the agent
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue, # run this func to see what it returns
        {
            "tools": "tools",
            END: END
        } # map the func result to the next dest
    )
    workflow.add_edge("tools", "agent")
    compiled_agent = workflow.compile()
    print(f"Dispatching graph execution loop for instruction: '{user_prompt}'...\n")
    # Execute the runtime system
    initial_input = {"messages": [("user", user_prompt)]}
    final_state = await compiled_agent.ainvoke(initial_input)
    print("\nComplete Execution Steps")
    for i, message in enumerate(final_state["messages"], 1):
        # Determine the role actor name
        role = message.__class__.__name__.replace("Message", "")
        
        # Check if the message is an AIMessage with tool calling intentions
        tool_calls_str = ""
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls_str = f"[Triggers Tools: {', '.join([tc['name'] for tc in message.tool_calls])}]"

        print(f"\n[Step {i}] {role}:{tool_calls_str}")
        print("-" * 30)
        print(message.content or "[Empty content payload - Check tool_calls or metadata]")

    return final_state["messages"][-1].content

if __name__ == "__main__":
    generic_test_prompt = (
        "Analyze the financial trajectory of the company represented in the database. "
        "Calculate its key financial efficiency or profitability margins across all available "
        "historical periods, and evaluate whether the qualitative operational narrative in the "
        "internal corporate text records aligns with or contradicts these empirical trends."
    )
    asyncio.run(run_agent_sandbox(generic_test_prompt))