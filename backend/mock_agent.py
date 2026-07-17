from typing import List, Dict, Any
import json
from mock_tools import query_sales_db, search_corporate_policies, write_local_report

class AgentState:
    """
    Mimics LangGraph State management. Tracks user input, steps taken, 
    and the final response data context.
    """
    def __init__(self, user_prompt: str):
        self.user_prompt: str = user_prompt
        self.steps_executed: List[str] = []
        self.context_data: Dict[str, Any] = {}
        self.final_answer: str = ""
        self.is_complete: bool = False

class AgenticOrchestrator:
    """
    Autonomous Agent Core running a deliberate multi-step reasoning loop.
    """
    def __init__(self, state: AgentState):
        self.state = state

    def route_next_action(self) -> str:
        """
        The "Brain" Router. Inspects the state and user prompt to determine 
        which node/tool to run next based on what's missing.
        """
        prompt = self.state.user_prompt.lower()
        
        # Step 1: Check if we need sales data
        if "sales" in prompt and "sales_data" not in self.state.context_data:
            return "NODE_QUERY_SQL"
            
        # Step 2: Check if we need policy guidelines
        if "policy" in prompt and "policy_data" not in self.state.context_data:
            return "NODE_QUERY_RAG"
            
        # Step 3: Check if we need to write a report file
        if "report" in prompt and "file_written" not in self.state.context_data:
            return "NODE_WRITE_ARTIFACT"
            
        # Final Step: Compile everything
        return "NODE_FINALIZE_RESPONSE"

    def execute_loop(self):
        """
        Runs the dynamic execution engine until the completion state is True.
        """
        print(f"\n🚀 Initializing Agentic Loop for Prompt: '{self.state.user_prompt}'")
        max_loops = 5
        loop_count = 0
        
        while not self.state.is_complete and loop_count < max_loops:
            next_node = self.route_next_action()
            print(f"Agent Router -> Directing execution to: {next_node}")
            
            if next_node == "NODE_QUERY_SQL":
                # Simulate extracting variables (e.g., 'Q3') from prompt
                quarter = "Q3" if "q3" in self.state.user_prompt.lower() else "Q4"
                data = query_sales_db(quarter=quarter)
                self.state.context_data["sales_data"] = data
                self.state.steps_executed.append("Queried SQL Database for Q3 Sales")
                
            elif next_node == "NODE_QUERY_RAG":
                data = search_corporate_policies(query="refund policy")
                self.state.context_data["policy_data"] = data
                self.state.steps_executed.append("Fetched Corporate Policy Docs via RAG")
                
            elif next_node == "NODE_WRITE_ARTIFACT":
                content = (
                    f"--- AGENTDESK AUTOMATED REPORT ---\n"
                    f"Sales Context: {json.dumps(self.state.context_data.get('sales_data'), indent=2)}\n"
                    f"Policy Context: {self.state.context_data.get('policy_data')}\n"
                )
                result = write_local_report("q3_sales_summary.txt", content)
                self.state.context_data["file_written"] = True
                self.state.steps_executed.append("Generated Automated System Report Artifact")
                
            elif next_node == "NODE_FINALIZE_RESPONSE":
                # Compile narrative context summary
                sales_count = len(self.state.context_data.get('sales_data', []))
                self.state.final_answer = (
                    f"Analysis complete. Synthesized {sales_count} sales records against corporate policy. "
                    f"Found flag regarding Stark Tech's $12,000 order needing executive review panel sign-off. "
                    f"System text report generated successfully."
                )
                self.state.is_complete = True
                self.state.steps_executed.append("Finalized narrative synthesis")
                
            loop_count += 1

        return self.state

if __name__ == "__main__":
    test_query = "Query Q3 sales, check them against the company refund policy document, and write a summary report"
    
    initial_state = AgentState(user_prompt=test_query)
    orchestrator = AgenticOrchestrator(state=initial_state)
    
    resulting_state = orchestrator.execute_loop()
    
    print("\n--- Final Agent State Verification ---")
    print(f"Execution Path Taken: {resulting_state.steps_executed}")
    print(f"Narrative Response: {resulting_state.final_answer}")