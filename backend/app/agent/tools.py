from app.rag.retriever import search_docs
from app.services.warranty_engine import check_warranty
from app.services.scheduler import get_slots
from app.services.telematics import get_vehicle_data, decode_dtc

TOOL_DEFINITIONS = [
    {
        "name": "search_knowledge_base",
        "description": "Search service manuals, TSBs, repair guides for vehicle issues",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 3}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_vehicle_info",
        "description": "Get vehicle details, telematics, and fault codes from database",
        "input_schema": {
            "type": "object",
            "properties": {"vehicle_id": {"type": "string"}},
            "required": ["vehicle_id"]
        }
    },
    {
        "name": "check_warranty_eligibility",
        "description": "Check if a repair type is covered under vehicle warranty",
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string"},
                "repair_type": {"type": "string"}
            },
            "required": ["vehicle_id", "repair_type"]
        }
    },
    {
        "name": "get_available_slots",
        "description": "Get repair scheduling slots at the service center",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_type": {"type": "string"},
                "urgency": {"type": "string", "enum": ["critical","high","normal"]}
            },
            "required": ["service_type"]
        }
    },
    {
        "name": "analyze_fault_codes",
        "description": "Decode OBD-II DTC codes and return diagnosis info",
        "input_schema": {
            "type": "object",
            "properties": {
                "codes": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["codes"]
        }
    }
]

async def execute_tool(name: str, inputs: dict) -> dict:
    dispatch = {
        "search_knowledge_base":    lambda: search_docs(inputs["query"], inputs.get("top_k", 3)),
        "get_vehicle_info":          lambda: get_vehicle_data(inputs["vehicle_id"]),
        "check_warranty_eligibility": lambda: check_warranty(inputs["vehicle_id"], inputs["repair_type"]),
        "get_available_slots":        lambda: get_slots(inputs["service_type"], inputs.get("urgency","normal")),
        "analyze_fault_codes":        lambda: decode_dtc(inputs["codes"]),
    }
    fn = dispatch.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    return await fn()