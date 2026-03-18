import asyncio
from app.agent.claude_agent import run_agent
from app.agent.warranty_agent import get_warranty_agent
from app.agent.scheduler_agent import get_scheduler_agent
from app.agent.telemetry_agent import get_telemetry_agent
from app.agent.rag_agent import get_rag_agent

async def run_orchestrator(user_message: str, context: dict = None) -> dict:
    """
    Routes user messages to relevant agents and executes them in parallel.
    """
    if context is None:
        context = {}

    lower_msg = user_message.lower()

    print(f"Orchestrator received message: {lower_msg}")

    # Determine which agents are relevant
    agents_to_run = []
    agent_names = []

    if "warranty" in lower_msg:
        agents_to_run.append(get_warranty_agent().process_query(user_message, context))
        agent_names.append("warranty")

    if "schedule" in lower_msg:
        agents_to_run.append(get_scheduler_agent().process_query(user_message, context))
        agent_names.append("scheduler")

    if "telemetry" in lower_msg:
        agents_to_run.append(get_telemetry_agent().process_query(user_message, context))
        agent_names.append("telemetry")

    if "rag" in lower_msg or "knowledge" in lower_msg or "document" in lower_msg:
        vehicle_info = context.get("vehicle_info", {})
        agents_to_run.append(get_rag_agent().process_query(user_message, vehicle_info))
        agent_names.append("rag")

    # If no specific agents matched, use Claude agent as default
    if not agents_to_run:
        return await run_agent(
            session_id=context.get("session_id", "default"),
            user_message=user_message,
            vehicle_id=context.get("vehicle_id")
        )

    # Execute all relevant agents in parallel
    results = await asyncio.gather(*agents_to_run, return_exceptions=True)

    # Combine results from all agents
    combined_response = {
        "agents_executed": agent_names,
        "responses": {}
    }

    for agent_name, result in zip(agent_names, results):
        if isinstance(result, Exception):
            combined_response["responses"][agent_name] = {"error": str(result)}
        else:
            combined_response["responses"][agent_name] = result

    return combined_response
