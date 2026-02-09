"""
Dashboard Generation Workflow using Langgraph.
Orchestrates the entire pipeline from data analysis to workbook generation.
"""

import asyncio
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models.schemas import (
    AIAnalysisRequest, AIAnalysisResponse, DatasetSchema,
    GenerationRequest, GenerationResult, ValidationResult
)
from ..ai_engine.analyzer import TableauDashboardAnalyzer
from ..tableau_engine.generator import TableauWorkbookGenerator
from ..utils.config import Config
from ..utils.logger import get_logger
from ..utils.data_processor import DataProcessor

logger = get_logger(__name__)

class WorkflowState(TypedDict):
    """State structure for the dashboard generation workflow"""
    # Input data
    dataset_schema_analysis: Optional[DatasetSchema]  # Sampled schema for AI analysis
    dataset_schema_generation: Optional[DatasetSchema]  # Full schema for workbook generation
    business_goals: List[str]
    target_audience: str
    user_preferences: Dict[str, Any]
    
    # Intermediate results
    validation_result: Optional[ValidationResult]
    ai_analysis: Optional[AIAnalysisResponse]
    generation_request: Optional[GenerationRequest]
    
    # Final output
    generation_result: Optional[GenerationResult]
    
    # Workflow metadata
    workflow_id: str
    current_step: str
    start_time: datetime
    errors: List[str]
    warnings: List[str]
    
class DashboardGenerationWorkflow:
    """
    Langgraph-based workflow for orchestrating dashboard generation process.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.data_processor = DataProcessor(config)
        self.analyzer = TableauDashboardAnalyzer(config)
        self.generator = TableauWorkbookGenerator(config.file_storage.output_folder)
        
        # Initialize checkpointer first before creating workflow
        self.checkpointer = MemorySaver()
        
        # Setup workflow graph
        self.workflow = self._create_workflow()
        
        logger.info("Dashboard generation workflow initialized")
    
    def _create_workflow(self) -> StateGraph:
        """Create the Langgraph workflow"""
        
        # Create state graph
        workflow = StateGraph(WorkflowState)
        
        # Define workflow nodes
        workflow.add_node("validate_input", self._validate_input_node)
        workflow.add_node("analyze_data", self._analyze_data_node)
        workflow.add_node("generate_workbook", self._generate_workbook_node)
        workflow.add_node("finalize_result", self._finalize_result_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Define workflow edges
        workflow.set_entry_point("validate_input")
        
        # Conditional routing from validation
        workflow.add_conditional_edges(
            "validate_input",
            self._should_continue_after_validation,
            {
                "continue": "analyze_data",
                "error": "handle_error"
            }
        )
        
        # Conditional routing from analysis
        workflow.add_conditional_edges(
            "analyze_data", 
            self._should_continue_after_analysis,
            {
                "continue": "generate_workbook",
                "error": "handle_error"
            }
        )
        
        # Conditional routing from generation
        workflow.add_conditional_edges(
            "generate_workbook",
            self._should_continue_after_generation,
            {
                "success": "finalize_result",
                "error": "handle_error"
            }
        )
        
        # End nodes
        workflow.add_edge("finalize_result", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def run_workflow(
        self,
        dataset_schema_analysis: DatasetSchema,
        dataset_schema_generation: DatasetSchema,
        business_goals: List[str],
        target_audience: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete dashboard generation workflow.
        
        Args:
            dataset_schema_analysis: Sampled schema for AI analysis
            dataset_schema_generation: Full schema for workbook generation
            business_goals: List of business objectives
            target_audience: Target audience description
            user_preferences: Optional user preferences
            workflow_id: Optional workflow identifier
            
        Returns:
            Workflow execution result
        """
        if workflow_id is None:
            workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting workflow execution: {workflow_id}")
        
        # Initialize workflow state
        initial_state = WorkflowState(
            dataset_schema_analysis=dataset_schema_analysis,
            dataset_schema_generation=dataset_schema_generation,
            business_goals=business_goals,
            target_audience=target_audience,
            user_preferences=user_preferences or {},
            validation_result=None,
            ai_analysis=None,
            generation_request=None,
            generation_result=None,
            workflow_id=workflow_id,
            current_step="validate_input",
            start_time=datetime.now(),
            errors=[],
            warnings=[]
        )
        
        try:
            # Execute workflow
            config = {"configurable": {"thread_id": workflow_id}}
            result = await self.workflow.ainvoke(initial_state, config)
            
            execution_time = (datetime.now() - initial_state["start_time"]).total_seconds()
            
            logger.info(f"Workflow completed: {workflow_id} ({execution_time:.1f}s)")
            
            return {
                "workflow_id": workflow_id,
                "success": len(result["errors"]) == 0,
                "execution_time_seconds": execution_time,
                "generation_result": result.get("generation_result"),
                "errors": result["errors"],
                "warnings": result["warnings"],
                "final_state": result
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {workflow_id} - {e}")
            return {
                "workflow_id": workflow_id,
                "success": False,
                "execution_time_seconds": (datetime.now() - initial_state["start_time"]).total_seconds(),
                "generation_result": None,
                "errors": [str(e)],
                "warnings": [],
                "final_state": initial_state
            }
    
    async def _validate_input_node(self, state: WorkflowState) -> WorkflowState:
        """Validate input data and configuration"""
        logger.info(f"[{state['workflow_id']}] Validating input data")
        
        state["current_step"] = "validate_input"
        
        try:
            # Validate dataset schemas
            if not state["dataset_schema_analysis"]:
                state["errors"].append("Dataset schema (analysis) is required")
                return state
            
            if not state["dataset_schema_generation"]:
                state["errors"].append("Dataset schema (generation) is required")
                return state
            
            if not state["business_goals"]:
                state["errors"].append("Business goals are required")
                return state
            
            if not state["target_audience"]:
                state["errors"].append("Target audience is required")
                return state
            
            # Validate dataset content
            dataset = state["dataset_schema"]
            
            if dataset.total_rows == 0:
                state["errors"].append("Dataset is empty")
                return state
            
            if dataset.total_columns == 0:
                state["errors"].append("Dataset has no columns")
                return state
            
            if dataset.data_quality_score < 0.5:
                state["warnings"].append(
                    f"Low data quality score: {dataset.data_quality_score:.1%}"
                )
            
            # Create validation result
            validation_result = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=state["warnings"].copy(),
                suggestions=[]
            )
            
            state["validation_result"] = validation_result
            
            logger.info(f"[{state['workflow_id']}] Input validation completed successfully")
            
        except Exception as e:
            error_msg = f"Input validation failed: {e}"
            logger.error(f"[{state['workflow_id']}] {error_msg}")
            state["errors"].append(error_msg)
        
        return state
    
    async def _analyze_data_node(self, state: WorkflowState) -> WorkflowState:
        """Perform AI analysis of the dataset"""
        logger.info(f"[{state['workflow_id']}] Starting AI data analysis")
        
        state["current_step"] = "analyze_data"
        
        try:
            # Create AI analysis request using SAMPLED schema for faster analysis
            analysis_request = AIAnalysisRequest(
                dataset_schema=state["dataset_schema_analysis"],
                business_goals=state["business_goals"],
                target_audience=state["target_audience"],
                preferences=state["user_preferences"],
                constraints={}
            )
            
            # Perform AI analysis
            ai_analysis = await self.analyzer.analyze_dataset(analysis_request)
            state["ai_analysis"] = ai_analysis
            
            logger.info(f"[{state['workflow_id']}] AI analysis completed")
            logger.debug(f"[{state['workflow_id']}] Generated {len(ai_analysis.recommended_kpis)} KPIs and {len(ai_analysis.recommended_visualizations)} visualizations")
            
        except Exception as e:
            error_msg = f"AI analysis failed: {e}"
            logger.error(f"[{state['workflow_id']}] {error_msg}")
            state["errors"].append(error_msg)
        
        return state
    
    async def _generate_workbook_node(self, state: WorkflowState) -> WorkflowState:
        """Generate the Tableau workbook"""
        logger.info(f"[{state['workflow_id']}] Starting workbook generation")
        
        state["current_step"] = "generate_workbook"
        
        try:
            # Create generation request using FULL schema for complete data in workbook
            generation_request = GenerationRequest(
                dataset_schema=state["dataset_schema_generation"],
                ai_analysis=state["ai_analysis"],
                user_preferences=state["user_preferences"],
                output_format="twbx",
                include_sample_data=True
            )
            
            state["generation_request"] = generation_request
            
            # Generate workbook
            generation_result = self.generator.generate_workbook(generation_request)
            state["generation_result"] = generation_result
            
            if generation_result.success:
                logger.info(f"[{state['workflow_id']}] Workbook generated successfully: {generation_result.file_path}")
            else:
                error_msg = f"Workbook generation failed: {generation_result.error_message}"
                logger.error(f"[{state['workflow_id']}] {error_msg}")
                state["errors"].append(error_msg)
            
            # Add any warnings from generation
            state["warnings"].extend(generation_result.warnings)
            
        except Exception as e:
            error_msg = f"Workbook generation failed: {e}"
            logger.error(f"[{state['workflow_id']}] {error_msg}")
            state["errors"].append(error_msg)
        
        return state
    
    async def _finalize_result_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow result"""
        logger.info(f"[{state['workflow_id']}] Finalizing workflow result")
        
        state["current_step"] = "finalize_result"
        
        try:
            # Calculate total execution time
            execution_time = (datetime.now() - state["start_time"]).total_seconds()
            
            # Log success metrics
            if state["generation_result"] and state["generation_result"].success:
                logger.info(f"[{state['workflow_id']}] Workflow completed successfully in {execution_time:.1f}s")
                
                # Log generation statistics
                workbook_spec = state["generation_result"].workbook_spec
                logger.info(f"[{state['workflow_id']}] Generated workbook with {len(workbook_spec.dashboards)} dashboard(s)")
                
                total_worksheets = sum(len(d.worksheets) for d in workbook_spec.dashboards)
                logger.info(f"[{state['workflow_id']}] Total worksheets: {total_worksheets}")
                
                if state["warnings"]:
                    logger.warning(f"[{state['workflow_id']}] Generated with warnings: {len(state['warnings'])}")
            
        except Exception as e:
            error_msg = f"Result finalization failed: {e}"
            logger.error(f"[{state['workflow_id']}] {error_msg}")
            state["errors"].append(error_msg)
        
        return state
    
    async def _handle_error_node(self, state: WorkflowState) -> WorkflowState:
        """Handle workflow errors"""
        logger.error(f"[{state['workflow_id']}] Handling workflow errors")
        
        state["current_step"] = "handle_error"
        
        # Log all errors
        for error in state["errors"]:
            logger.error(f"[{state['workflow_id']}] Error: {error}")
        
        # Log all warnings
        for warning in state["warnings"]:
            logger.warning(f"[{state['workflow_id']}] Warning: {warning}")
        
        execution_time = (datetime.now() - state["start_time"]).total_seconds()
        logger.error(f"[{state['workflow_id']}] Workflow failed after {execution_time:.1f}s")
        
        return state
    
    def _should_continue_after_validation(self, state: WorkflowState) -> str:
        """Determine next step after validation"""
        if state["errors"]:
            return "error"
        return "continue"
    
    def _should_continue_after_analysis(self, state: WorkflowState) -> str:
        """Determine next step after analysis"""
        if state["errors"] or not state["ai_analysis"]:
            return "error"
        return "continue"
    
    def _should_continue_after_generation(self, state: WorkflowState) -> str:
        """Determine next step after generation"""
        if state["errors"]:
            return "error"
        if state["generation_result"] and state["generation_result"].success:
            return "success"
        return "error"
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow"""
        try:
            config = {"configurable": {"thread_id": workflow_id}}
            
            # Get current state from checkpointer
            checkpoint = self.checkpointer.get(config)
            if checkpoint and checkpoint.values:
                state = checkpoint.values
                
                return {
                    "workflow_id": workflow_id,
                    "current_step": state.get("current_step"),
                    "start_time": state.get("start_time"),
                    "errors": state.get("errors", []),
                    "warnings": state.get("warnings", []),
                    "has_result": state.get("generation_result") is not None
                }
        
        except Exception as e:
            logger.error(f"Failed to get workflow status for {workflow_id}: {e}")
        
        return None
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflow executions"""
        try:
            # This would typically connect to a database or storage system
            # For now, return empty list as MemorySaver doesn't persist across restarts
            return []
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []