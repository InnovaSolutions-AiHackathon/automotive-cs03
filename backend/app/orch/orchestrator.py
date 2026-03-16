import os
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from anthropic import Anthropic
from langgraph.graph import StateGraph, END
from agents.rag_agent import get_rag_agent
from agents.vision_agent import get_vision_agent
from agents.warranty_agent import get_warranty_agent
from agents.scheduling_agent import get_scheduling_agent
from agents.telematics_agent import get_telematics_agent
from database.connection import get_db_context
from models.database_models import Conversation, ConversationMessage, AgentActivity
from loguru import logger
import operator


class AgentState(TypedDict):
    """State that gets passed between agents"""
    # Input
    conversation_id: int
    user_query: str
    vehicle_id: Optional[int]
    issue_id: Optional[int]
    image_paths: Optional[List[str]]
    conversation_history: List[Dict[str, str]]
    
    # Vehicle context
    vehicle_info: Optional[Dict[str, Any]]
    
    # Agent outputs
    telematics_data: Optional[Dict[str, Any]]
    vision_analysis: Optional[Dict[str, Any]]
    rag_response: Optional[Dict[str, Any]]
    warranty_check: Optional[Dict[str, Any]]
    scheduling_recommendations: Optional[Dict[str, Any]]
    
    # Final output
    final_response: str
    response_metadata: Dict[str, Any]
    
    # Workflow control
    next_actions: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]


class CopilotOrchestrator:
    """
    Main orchestrator for the AI copilot system
    Coordinates multiple agents to handle customer queries
    """
    
    def __init__(self):
        # Initialize Claude for orchestration decisions
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        
        # Initialize all agents
        self.rag_agent = get_rag_agent()
        self.vision_agent = get_vision_agent()
        self.warranty_agent = get_warranty_agent()
        self.scheduling_agent = get_scheduling_agent()
        self.telematics_agent = get_telematics_agent()
        
        # Build workflow graph
        self.workflow = self._build_workflow()
        
        logger.info("✓ Copilot Orchestrator initialized")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow for agent orchestration
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("analyze_query", self._analyze_query_node)
        workflow.add_node("fetch_telematics", self._fetch_telematics_node)
        workflow.add_node("analyze_images", self._analyze_images_node)
        workflow.add_node("retrieve_knowledge", self._retrieve_knowledge_node)
        workflow.add_node("check_warranty", self._check_warranty_node)
        workflow.add_node("recommend_scheduling", self._recommend_scheduling_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Set entry point
        workflow.set_entry_point("analyze_query")
        
        # Define conditional edges
        workflow.add_conditional_edges(
            "analyze_query",
            self._route_after_analysis,
            {
                "telematics": "fetch_telematics",
                "images": "analyze_images",
                "knowledge": "retrieve_knowledge",
                "end": END
            }
        )
        
        workflow.add_edge("fetch_telematics", "retrieve_knowledge")
        workflow.add_edge("analyze_images", "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "check_warranty")
        workflow.add_edge("check_warranty", "recommend_scheduling")
        workflow.add_edge("recommend_scheduling", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _analyze_query_node(self, state: AgentState) -> AgentState:
        """
        Analyze the user query to determine which agents to invoke
        """
        logger.info("Analyzing user query...")
        
        try:
            query = state['user_query']
            has_images = bool(state.get('image_paths'))
            has_vehicle = bool(state.get('vehicle_id'))
            
            # Use Claude to analyze intent
            system_prompt = """Analyze the customer service query and determine which actions are needed.

Available actions:
- telematics: Fetch real-time vehicle diagnostic data
- images: Analyze dashboard or vehicle images
- knowledge: Search service documentation
- warranty: Check warranty coverage
- scheduling: Recommend service appointments

Respond with JSON:
{
    "primary_intent": "diagnose|schedule|warranty_check|general_inquiry",
    "needs_telematics": true/false,
    "needs_image_analysis": true/false,
    "needs_knowledge": true/false,
    "needs_warranty": true/false,
    "needs_scheduling": true/false,
    "urgency": "critical|high|medium|low"
}"""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Query: {query}\nHas images: {has_images}\nHas vehicle ID: {has_vehicle}"
                    }
                ]
            )
            
            import json
            response_text = response.content[0].text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            analysis = json.loads(response_text[json_start:json_end])
            
            # Populate next_actions based on analysis
            next_actions = []
            if has_vehicle and analysis.get('needs_telematics'):
                next_actions.append('telematics')
            if has_images and analysis.get('needs_image_analysis'):
                next_actions.append('images')
            if analysis.get('needs_knowledge', True):  # Default to true
                next_actions.append('knowledge')
            
            state['next_actions'] = next_actions
            state['response_metadata'] = {'intent_analysis': analysis}
            
            logger.info(f"Query analyzed - Next actions: {next_actions}")
            
        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}")
            state['errors'] = [str(e)]
            state['next_actions'] = ['knowledge']  # Fallback to knowledge retrieval
        
        return state
    
    def _route_after_analysis(self, state: AgentState) -> str:
        """Determine next step after query analysis"""
        next_actions = state.get('next_actions', [])
        
        if 'telematics' in next_actions:
            return "telematics"
        elif 'images' in next_actions:
            return "images"
        elif 'knowledge' in next_actions:
            return "knowledge"
        else:
            return "end"
    
    def _fetch_telematics_node(self, state: AgentState) -> AgentState:
        """Fetch telematics data"""
        logger.info("Fetching telematics data...")
        
        try:
            vehicle_id = state.get('vehicle_id')
            if vehicle_id:
                telematics_data = self.telematics_agent.get_vehicle_telematics(
                    vehicle_id=vehicle_id,
                    include_history=True,
                    hours_back=24
                )
                state['telematics_data'] = telematics_data
                logger.info("Telematics data retrieved")
        except Exception as e:
            logger.error(f"Error fetching telematics: {str(e)}")
            state['errors'] = [f"Telematics error: {str(e)}"]
        
        return state
    
    def _analyze_images_node(self, state: AgentState) -> AgentState:
        """Analyze dashboard images"""
        logger.info("Analyzing images...")
        
        try:
            image_paths = state.get('image_paths', [])
            vehicle_info = state.get('vehicle_info')
            
            analyses = []
            for image_path in image_paths:
                analysis = self.vision_agent.analyze_dashboard_image(
                    image_path=image_path,
                    vehicle_info=vehicle_info
                )
                analyses.append(analysis)
            
            state['vision_analysis'] = {
                'analyses': analyses,
                'image_count': len(image_paths)
            }
            logger.info(f"Analyzed {len(image_paths)} images")
            
        except Exception as e:
            logger.error(f"Error analyzing images: {str(e)}")
            state['errors'] = [f"Vision error: {str(e)}"]
        
        return state
    
    def _retrieve_knowledge_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant knowledge"""
        logger.info("Retrieving knowledge...")
        
        try:
            # Enhance query with telematics and vision insights
            enhanced_query = state['user_query']
            
            if state.get('telematics_data'):
                dtc_codes = state['telematics_data'].get('current_data', {}).get('dtc_codes', [])
                if dtc_codes:
                    enhanced_query += f" DTC codes: {', '.join(dtc_codes)}"
            
            if state.get('vision_analysis'):
                warnings = []
                for analysis in state['vision_analysis'].get('analyses', []):
                    detected = analysis.get('analysis', {}).get('warnings_detected', [])
                    warnings.extend([w['name'] for w in detected])
                if warnings:
                    enhanced_query += f" Warning lights: {', '.join(warnings)}"
            
            rag_response = self.rag_agent.process_query(
                user_query=enhanced_query,
                vehicle_info=state.get('vehicle_info'),
                conversation_history=state.get('conversation_history'),
                conversation_id=state.get('conversation_id')
            )
            
            state['rag_response'] = rag_response
            logger.info("Knowledge retrieved")
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {str(e)}")
            state['errors'] = [f"RAG error: {str(e)}"]
        
        return state
    
    def _check_warranty_node(self, state: AgentState) -> AgentState:
        """Check warranty coverage"""
        logger.info("Checking warranty...")
        
        try:
            vehicle_id = state.get('vehicle_id')
            if not vehicle_id:
                return state
            
            # Determine issue category from RAG response or telematics
            issue_category = "engine"  # Default
            issue_description = state['user_query']
            
            warranty_check = self.warranty_agent.validate_warranty(
                vehicle_id=vehicle_id,
                issue_category=issue_category,
                issue_description=issue_description
            )
            
            state['warranty_check'] = warranty_check
            logger.info(f"Warranty check complete - Eligible: {warranty_check.get('eligible')}")
            
        except Exception as e:
            logger.error(f"Error checking warranty: {str(e)}")
            state['errors'] = [f"Warranty error: {str(e)}"]
        
        return state
    
    def _recommend_scheduling_node(self, state: AgentState) -> AgentState:
        """Recommend appointment scheduling"""
        logger.info("Generating scheduling recommendations...")
        
        try:
            vehicle_id = state.get('vehicle_id')
            issue_id = state.get('issue_id')
            
            if not vehicle_id:
                return state
            
            # Determine severity from intent analysis
            severity_map = {
                'critical': 'critical',
                'high': 'high',
                'medium': 'medium',
                'low': 'low'
            }
            
            urgency = state.get('response_metadata', {}).get('intent_analysis', {}).get('urgency', 'medium')
            from models.database_models import IssueSeverity
            severity = IssueSeverity(severity_map.get(urgency, 'medium'))
            
            scheduling = self.scheduling_agent.recommend_appointments(
                vehicle_id=vehicle_id,
                issue_id=issue_id,
                issue_severity=severity,
                issue_description=state['user_query']
            )
            
            state['scheduling_recommendations'] = scheduling
            logger.info(f"Generated {len(scheduling.get('recommended_slots', []))} appointment recommendations")
            
        except Exception as e:
            logger.error(f"Error generating scheduling: {str(e)}")
            state['errors'] = [f"Scheduling error: {str(e)}"]
        
        return state
    
    def _generate_response_node(self, state: AgentState) -> AgentState:
        """Generate final comprehensive response"""
        logger.info("Generating final response...")
        
        try:
            # Compile all agent outputs
            context = {
                "user_query": state['user_query'],
                "rag_response": state.get('rag_response', {}).get('response'),
                "telematics_summary": self._summarize_telematics(state.get('telematics_data')),
                "vision_summary": self._summarize_vision(state.get('vision_analysis')),
                "warranty_summary": self._summarize_warranty(state.get('warranty_check')),
                "scheduling_summary": self._summarize_scheduling(state.get('scheduling_recommendations'))
            }
            
            system_prompt = """You are a helpful automotive service assistant. Synthesize all the information from various agents into a clear, actionable response for the customer service agent.

Structure your response:
1. Issue Summary
2. Diagnostic Findings
3. Warranty Status (if applicable)
4. Recommended Actions
5. Next Steps / Scheduling

Be clear, concise, and prioritize safety."""
            
            user_message = f"""Customer Query: {context['user_query']}

Knowledge Base Response:
{context['rag_response'] or 'No specific documentation found'}

Telematics Data:
{context['telematics_summary'] or 'No telematics data available'}

Dashboard Analysis:
{context['vision_summary'] or 'No images analyzed'}

Warranty Status:
{context['warranty_summary'] or 'Not checked'}

Scheduling Options:
{context['scheduling_summary'] or 'Not generated'}

Please provide a comprehensive response to assist the customer service agent."""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            final_response = response.content[0].text
            
            state['final_response'] = final_response
            state['response_metadata'].update({
                'agents_used': [
                    k for k in ['telematics_data', 'vision_analysis', 'rag_response', 'warranty_check', 'scheduling_recommendations']
                    if state.get(k)
                ],
                'total_execution_time_ms': sum([
                    state.get('rag_response', {}).get('execution_time_ms', 0),
                    state.get('telematics_data', {}).get('execution_time_ms', 0)
                ])
            })
            
            logger.info("Final response generated")
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            state['errors'] = [f"Response generation error: {str(e)}"]
            state['final_response'] = "I apologize, but I encountered an error generating the response. Please try again."
        
        return state
    
    def _summarize_telematics(self, data: Optional[Dict]) -> str:
        """Summarize telematics data"""
        if not data or 'error' in data:
            return "Telematics data unavailable"
        
        current = data.get('current_data', {})
        health_score = data.get('health_score', 'N/A')
        dtc_codes = data.get('dtc_codes_decoded', [])
        
        summary = f"Vehicle Health Score: {health_score}/100\n"
        if dtc_codes:
            summary += f"Active Diagnostic Codes: {len(dtc_codes)}\n"
            for code in dtc_codes[:3]:
                summary += f"  - {code['code']}: {code['description']}\n"
        
        return summary
    
    def _summarize_vision(self, analysis: Optional[Dict]) -> str:
        """Summarize vision analysis"""
        if not analysis:
            return "No dashboard images analyzed"
        
        total_warnings = 0
        critical_warnings = []
        
        for img_analysis in analysis.get('analyses', []):
            warnings = img_analysis.get('analysis', {}).get('warnings_detected', [])
            total_warnings += len(warnings)
            critical_warnings.extend([w for w in warnings if w.get('severity') == 'critical'])
        
        summary = f"Dashboard Analysis: {total_warnings} warning(s) detected\n"
        if critical_warnings:
            summary += "CRITICAL WARNINGS:\n"
            for w in critical_warnings:
                summary += f"  - {w.get('name')}: {w.get('recommended_action')}\n"
        
        return summary
    
    def _summarize_warranty(self, check: Optional[Dict]) -> str:
        """Summarize warranty check"""
        if not check:
            return "Warranty not checked"
        
        if check.get('eligible'):
            return f"✓ Covered under {check.get('warranty_type')} warranty ({check.get('coverage_percentage')}% coverage)"
        else:
            return f"✗ Not covered: {check.get('reason')}"
    
    def _summarize_scheduling(self, scheduling: Optional[Dict]) -> str:
        """Summarize scheduling recommendations"""
        if not scheduling or 'error' in scheduling:
            return "Scheduling unavailable"
        
        slots = scheduling.get('recommended_slots', [])
        if not slots:
            return "No available appointments found"
        
        top_slot = slots[0]
        return f"Recommended: {top_slot['service_center_name']} on {top_slot['day_of_week']} at {top_slot['time_slot']}"
    
    def process_request(
        self,
        conversation_id: int,
        user_query: str,
        vehicle_id: Optional[int] = None,
        issue_id: Optional[int] = None,
        image_paths: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a customer service request through the multi-agent system
        
        Args:
            conversation_id: Conversation ID
            user_query: Customer's query
            vehicle_id: Vehicle ID (if applicable)
            issue_id: Issue ID (if exists)
            image_paths: Paths to uploaded images
            conversation_history: Previous conversation messages
            
        Returns:
            Complete response with all agent outputs
        """
        start_time = datetime.utcnow()
        
        # Get vehicle info if vehicle_id provided
        vehicle_info = None
        if vehicle_id:
            with get_db_context() as db:
                from models.database_models import Vehicle
                vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
                if vehicle:
                    vehicle_info = {
                        "make": vehicle.make,
                        "model": vehicle.model,
                        "year": vehicle.year,
                        "vin": vehicle.vin,
                        "current_mileage": vehicle.current_mileage
                    }
        
        # Initialize state
        initial_state: AgentState = {
            "conversation_id": conversation_id,
            "user_query": user_query,
            "vehicle_id": vehicle_id,
            "issue_id": issue_id,
            "image_paths": image_paths or [],
            "conversation_history": conversation_history or [],
            "vehicle_info": vehicle_info,
            "telematics_data": None,
            "vision_analysis": None,
            "rag_response": None,
            "warranty_check": None,
            "scheduling_recommendations": None,
            "final_response": "",
            "response_metadata": {},
            "next_actions": [],
            "errors": []
        }
        
        # Execute workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            
            total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return {
                "response": final_state['final_response'],
                "metadata": final_state['response_metadata'],
                "telematics": final_state.get('telematics_data'),
                "vision": final_state.get('vision_analysis'),
                "warranty": final_state.get('warranty_check'),
                "scheduling": final_state.get('scheduling_recommendations'),
                "errors": final_state.get('errors', []),
                "total_execution_time_ms": total_time
            }
            
        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e),
                "errors": [str(e)]
            }


# Singleton instance
_orchestrator = None

def get_orchestrator() -> CopilotOrchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CopilotOrchestrator()
    return _orchestrator


if __name__ == "__main__":
    # Test orchestrator
    orchestrator = CopilotOrchestrator()
    
    print("Copilot Orchestrator Test")
    print("=" * 50)
    print("✓ All agents initialized")
    print("✓ Workflow graph built")
    print("\nReady to process requests!")
