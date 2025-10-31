"""
Streamlit web interface for the Tableau Dashboard Generator.
Provides an intuitive user interface for data upload and dashboard generation.
"""

import streamlit as st
import asyncio
import pandas as pd
import io
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from ..utils.config import get_config
from ..utils.logger import get_logger, init_default_logging
from ..utils.data_processor import DataProcessor
from ..workflows.dashboard_workflow import DashboardGenerationWorkflow
from ..models.schemas import validate_dataframe_schema

# Initialize logging
init_default_logging()
logger = get_logger(__name__)

class StreamlitApp:
    """
    Main Streamlit web application.
    
    Provides the complete UI for data upload, requirements specification,
    AI analysis, and Tableau dashboard generation.
    
    Attributes
    ----------
    config : Config
        Application configuration loaded from config.yaml
    data_processor : DataProcessor
        Data loading and validation processor
    workflow : DashboardGenerationWorkflow
        Langgraph workflow orchestrator
    """
    
    def __init__(self):
        self.config = None
        self.data_processor = None
        self.workflow = None
        self.setup_config()
        
    def setup_config(self):
        """
        Initialize configuration and components.
        
        Loads config from YAML, initializes DataProcessor and Workflow.
        Logs errors to both Streamlit UI and logger.
        """
        try:
            self.config = get_config()
            self.data_processor = DataProcessor(self.config)
            self.workflow = DashboardGenerationWorkflow(self.config)
            logger.info("Streamlit app initialized successfully")
        except Exception as e:
            st.error(f"Failed to initialize application: {e}")
            logger.error(f"App initialization failed: {e}")
    
    def run(self):
        """
        Run the Streamlit application.
        
        Configures page metadata and renders header, sidebar, and main content.
        """
        # Configure Streamlit page
        st.set_page_config(
            page_title=self.config.streamlit.page_config.get("page_title", "Tableau Dashboard Generator"),
            page_icon=self.config.streamlit.page_config.get("page_icon", "📊"),
            layout=self.config.streamlit.page_config.get("layout", "wide"),
            initial_sidebar_state=self.config.streamlit.page_config.get("initial_sidebar_state", "expanded")
        )
        
        # Main app layout
        self.render_header()
        self.render_sidebar()
        self.render_main_content()
        
    def render_header(self):
        """
        Render application header with title and status.
        
        Displays app title, description, and expandable status section
        showing Azure OpenAI connectivity, version, and debug mode.
        """
        st.title("🚀 Tableau Dashboard Generator")
        st.markdown("""
        **AI-Powered Automatic Dashboard Creation** • Upload your data and let AI create compelling Tableau dashboards
        """)
        
        # Display configuration status
        if self.config:
            with st.expander("ℹ️ Application Status", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Azure OpenAI", "✅ Connected" if self.config.azure_openai.api_key else "❌ Not Configured")
                
                with col2:
                    st.metric("Version", self.config.application.version)
                
                with col3:
                    st.metric("Debug Mode", "On" if self.config.application.debug else "Off")
    
    def render_sidebar(self):
        """
        Render sidebar with configuration options.
        
        Shows file upload settings, output format selection, sample data option,
        and advanced options (color scheme, max visualizations).
        Stores selections in session_state.
        """
        with st.sidebar:
            st.header("⚙️ Settings")
            
            # File upload settings
            st.subheader("Data Upload")
            st.info(f"Max file size: {self.config.data_processing.max_file_size_mb}MB")
            st.info(f"Supported formats: {', '.join(self.config.data_processing.supported_formats)}")
            
            # Generation settings
            st.subheader("Generation Options")
            
            output_format = st.selectbox(
                "Output Format",
                ["twbx", "twb"],
                help="TWBX includes data, TWB is XML only"
            )
            
            include_sample_data = st.checkbox(
                "Include Sample Data",
                value=True,
                help="Include sample data in the generated workbook"
            )
            
            # Store settings in session state
            st.session_state.output_format = output_format
            st.session_state.include_sample_data = include_sample_data
            
            # Advanced settings
            with st.expander("Advanced Options"):
                color_scheme = st.selectbox(
                    "Color Scheme",
                    ["tableau10", "tableau20", "category10", "blues", "oranges", "greens"],
                    help="Default color scheme for visualizations"
                )
                
                max_visualizations = st.slider(
                    "Max Visualizations",
                    min_value=2,
                    max_value=15,
                    value=6,
                    help="Maximum number of visualizations to generate"
                )
                
                st.session_state.color_scheme = color_scheme
                st.session_state.max_visualizations = max_visualizations
    
    def render_main_content(self):
        """
        Render main content with four workflow tabs.
        
        Tabs: Data Upload → Requirements → AI Analysis → Generate Dashboard.
        Initializes session state for workflow tracking.
        """
        
        # Initialize session state
        if 'workflow_status' not in st.session_state:
            st.session_state.workflow_status = 'ready'
        
        if 'uploaded_data' not in st.session_state:
            st.session_state.uploaded_data = None
        
        if 'generation_result' not in st.session_state:
            st.session_state.generation_result = None
        
        # Main workflow tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📤 Data Upload", 
            "🎯 Requirements", 
            "🤖 AI Analysis", 
            "📊 Generate Dashboard"
        ])
        
        with tab1:
            self.render_data_upload_tab()
        
        with tab2:
            self.render_requirements_tab()
        
        with tab3:
            self.render_analysis_tab()
        
        with tab4:
            self.render_generation_tab()
    
    def render_data_upload_tab(self):
        """
        Render data upload interface.
        
        Handles file upload, validation, preprocessing, and schema creation.
        Displays data preview, validation results, and data summary metrics.
        Stores processed data and schema in session_state.
        """
        st.header("📤 Upload Your Data")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a data file",
            type=self.config.data_processing.supported_formats,
            help=f"Upload files up to {self.config.data_processing.max_file_size_mb}MB"
        )
        
        if uploaded_file is not None:
            try:
                # Display file info
                file_details = {
                    "filename": uploaded_file.name,
                    "filetype": uploaded_file.type,
                    "filesize": f"{uploaded_file.size / 1024 / 1024:.2f} MB"
                }
                
                st.json(file_details)
                
                # Load and validate data
                with st.spinner("Loading and analyzing data..."):
                    # Save uploaded file temporarily
                    temp_path = Path(self.config.file_storage.temp_folder) / uploaded_file.name
                    temp_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Load data
                    df = self.data_processor.load_data_file(temp_path)
                    
                    # Validate data
                    validation_result = self.data_processor.validate_data(df)
                    
                    # Preprocess data
                    df_processed = self.data_processor.preprocess_data(df)
                    
                    # Create dataset schema
                    dataset_schema = self.data_processor.create_dataset_schema(
                        df_processed, 
                        uploaded_file.name.split('.')[0]
                    )
                    
                    # Store in session state
                    st.session_state.uploaded_data = {
                        'dataframe': df_processed,
                        'schema': dataset_schema,
                        'validation': validation_result,
                        'original_filename': uploaded_file.name
                    }
                    
                    # Clean up temp file
                    temp_path.unlink(missing_ok=True)
                
                # Display data preview and validation results
                self.display_data_preview(df_processed, validation_result)
                
                st.success("✅ Data loaded successfully!")
                
            except Exception as e:
                st.error(f"Failed to load data: {e}")
                logger.error(f"Data loading failed: {e}")
        
        # Display current data status
        if st.session_state.uploaded_data:
            st.info("✅ Data is ready for analysis")
            
            # Data summary
            with st.expander("📊 Data Summary", expanded=True):
                schema = st.session_state.uploaded_data['schema']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Rows", f"{schema.total_rows:,}")
                with col2:
                    st.metric("Columns", schema.total_columns)
                with col3:
                    st.metric("Data Quality", f"{schema.data_quality_score:.1%}")
                with col4:
                    st.metric("File", st.session_state.uploaded_data['original_filename'])
    
    def display_data_preview(self, df: pd.DataFrame, validation_result):
        """
        Display data preview and validation results.
        
        Parameters
        ----------
        df : pd.DataFrame
            Processed dataframe to preview (first 10 rows)
        validation_result : ValidationResult
            Validation result with errors, warnings, suggestions
        """
        
        # Data preview
        st.subheader("🔍 Data Preview")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Validation results
        st.subheader("✅ Data Validation")
        
        if validation_result.is_valid:
            st.success("Data validation passed!")
        else:
            st.error("Data validation failed!")
        
        # Display errors
        if validation_result.errors:
            st.subheader("❌ Errors")
            for error in validation_result.errors:
                st.error(error)
        
        # Display warnings
        if validation_result.warnings:
            st.subheader("⚠️ Warnings")
            for warning in validation_result.warnings:
                st.warning(warning)
        
        # Display suggestions
        if validation_result.suggestions:
            st.subheader("💡 Suggestions")
            for suggestion in validation_result.suggestions:
                st.info(suggestion)
        
        # Column analysis
        with st.expander("📋 Column Details"):
            col_data = []
            for col in st.session_state.uploaded_data['schema'].columns:
                col_data.append({
                    "Column": col.name,
                    "Type": col.data_type.value,
                    "Unique Values": col.unique_values,
                    "Nulls": col.null_count,
                    "Role": col.recommended_role or "auto"
                })
            
            st.dataframe(pd.DataFrame(col_data), use_container_width=True)
    
    def render_requirements_tab(self):
        """
        Render requirements specification interface.
        
        Captures business goals, target audience, and dashboard preferences.
        Stores requirements in session_state for workflow use.
        """
        st.header("🎯 Specify Requirements")
        
        if not st.session_state.uploaded_data:
            st.warning("Please upload data first!")
            return
        
        # Business goals
        st.subheader("📈 Business Goals")
        st.write("What business questions do you want this dashboard to answer?")
        
        # Pre-defined goal options
        goal_options = [
            "Track key performance metrics",
            "Analyze trends over time",
            "Compare performance across categories", 
            "Identify outliers and anomalies",
            "Monitor operational efficiency",
            "Understand customer behavior",
            "Measure financial performance",
            "Assess product performance",
            "Geographic analysis",
            "Custom analysis"
        ]
        
        selected_goals = st.multiselect(
            "Select business goals (choose multiple):",
            goal_options,
            help="Select the main objectives for your dashboard"
        )
        
        # Custom goals
        custom_goals = st.text_area(
            "Additional custom goals:",
            placeholder="Enter any specific requirements or questions...",
            help="Describe any specific analysis needs not covered above"
        )
        
        # Combine goals
        business_goals = selected_goals.copy()
        if custom_goals.strip():
            business_goals.extend([goal.strip() for goal in custom_goals.split('\n') if goal.strip()])
        
        # Target audience
        st.subheader("👥 Target Audience")
        target_audience = st.selectbox(
            "Who is the primary audience for this dashboard?",
            [
                "Executive leadership",
                "Management team",
                "Data analysts",
                "Operations team",
                "Sales team",
                "Marketing team",
                "Financial analysts",
                "General business users",
                "Technical team",
                "External stakeholders"
            ],
            help="This helps AI tailor the complexity and focus of visualizations"
        )
        
        # Audience details
        audience_details = st.text_area(
            "Audience details (optional):",
            placeholder="Describe the audience's technical level, preferences, or specific needs...",
            help="Additional context about your audience"
        )
        
        # Dashboard preferences  
        st.subheader("🎨 Dashboard Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            dashboard_style = st.selectbox(
                "Dashboard Style",
                ["Executive Summary", "Detailed Analysis", "Operational Monitoring", "Exploratory"],
                help="Choose the overall approach and complexity level"
            )
            
            update_frequency = st.selectbox(
                "Expected Update Frequency",
                ["Real-time", "Daily", "Weekly", "Monthly", "Quarterly", "Ad-hoc"],
                help="How often will this dashboard be updated?"
            )
        
        with col2:
            interactivity_level = st.selectbox(
                "Interactivity Level",
                ["High (many filters)", "Medium (some filters)", "Low (minimal filters)"],
                help="How interactive should the dashboard be?"
            )
            
            priority_focus = st.selectbox(
                "Priority Focus",
                ["Visual appeal", "Data density", "Performance", "Simplicity"],
                help="What aspect should be prioritized?"
            )
        
        # Save requirements to session state
        if business_goals and target_audience:
            st.session_state.requirements = {
                'business_goals': business_goals,
                'target_audience': target_audience + (f" - {audience_details}" if audience_details else ""),
                'preferences': {
                    'dashboard_style': dashboard_style,
                    'update_frequency': update_frequency,
                    'interactivity_level': interactivity_level,
                    'priority_focus': priority_focus,
                    'color_scheme': getattr(st.session_state, 'color_scheme', 'tableau10'),
                    'max_visualizations': getattr(st.session_state, 'max_visualizations', 6)
                }
            }
            
            st.success("✅ Requirements captured!")
            
            # Display summary
            with st.expander("📋 Requirements Summary"):
                st.json(st.session_state.requirements)
        
        else:
            if 'requirements' in st.session_state:
                del st.session_state.requirements
    
    def render_analysis_tab(self):
        """
        Render AI analysis interface.
        
        Requires data upload and requirements specification.
        Triggers AI analysis via workflow.analyzer and displays results.
        """
        st.header("🤖 AI Analysis")
        
        if not st.session_state.uploaded_data:
            st.warning("Please upload data first!")
            return
        
        if not st.session_state.get('requirements'):
            st.warning("Please specify requirements first!")
            return
        
        # Run AI analysis
        if st.button("🚀 Start AI Analysis", type="primary", use_container_width=True):
            self.run_ai_analysis()
        
        # Display analysis results
        if 'ai_analysis' in st.session_state:
            self.display_analysis_results()
    
    def run_ai_analysis(self):
        """
        Execute AI analysis asynchronously.
        
        Runs workflow.analyzer.analyze_dataset with dataset schema,
        business goals, and user preferences. Displays progress.
        Stores result in session_state.ai_analysis.
        """
        try:
            with st.spinner("🤖 AI is analyzing your data and requirements..."):
                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate progress updates (since we can't easily track internal AI progress)
                status_text.text("Initializing AI analysis...")
                progress_bar.progress(10)
                time.sleep(1)
                
                status_text.text("Analyzing data structure...")
                progress_bar.progress(30)
                time.sleep(2)
                
                status_text.text("Generating insights...")
                progress_bar.progress(60)
                time.sleep(2)
                
                status_text.text("Creating recommendations...")
                progress_bar.progress(90)
                
                # Run actual analysis
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    result = loop.run_until_complete(self.workflow.analyzer.analyze_dataset({
                        'dataset_schema': st.session_state.uploaded_data['schema'],
                        'business_goals': st.session_state.requirements['business_goals'],
                        'target_audience': st.session_state.requirements['target_audience'],
                        'preferences': st.session_state.requirements['preferences'],
                        'constraints': {}
                    }))
                    
                    st.session_state.ai_analysis = result
                    
                finally:
                    loop.close()
                
                progress_bar.progress(100)
                status_text.text("Analysis complete!")
                
                st.success("🎉 AI analysis completed successfully!")
                
        except Exception as e:
            st.error(f"AI analysis failed: {e}")
            logger.error(f"AI analysis failed: {e}")
    
    def display_analysis_results(self):
        """
        Display AI analysis results in expandable sections.
        
        Shows dataset insights, recommended KPIs, visualizations,
        design recommendations, and performance considerations.
        """
        analysis = st.session_state.ai_analysis
        
        st.subheader("📊 AI Analysis Results")
        
        # Dataset insights
        with st.expander("🔍 Dataset Insights", expanded=True):
            insights = analysis.dataset_insights
            
            if 'data_characteristics' in insights:
                st.json(insights['data_characteristics'])
            
            if 'business_potential' in insights:
                st.write("**Business Potential:**")
                for potential in insights['business_potential']:
                    st.write(f"• {potential}")
            
            if 'data_quality_issues' in insights:
                st.write("**Data Quality Issues:**")
                for issue in insights['data_quality_issues']:
                    st.write(f"⚠️ {issue}")
        
        # Recommended KPIs
        with st.expander(f"📈 Recommended KPIs ({len(analysis.recommended_kpis)})", expanded=True):
            if analysis.recommended_kpis:
                kpi_data = []
                for kpi in analysis.recommended_kpis:
                    kpi_data.append({
                        "KPI": kpi.name,
                        "Description": kpi.description,
                        "Priority": kpi.priority,
                        "Format": kpi.format_string
                    })
                
                st.dataframe(pd.DataFrame(kpi_data), use_container_width=True)
            else:
                st.info("No specific KPIs recommended")
        
        # Recommended visualizations
        with st.expander(f"📊 Recommended Visualizations ({len(analysis.recommended_visualizations)})", expanded=True):
            if analysis.recommended_visualizations:
                viz_data = []
                for viz in analysis.recommended_visualizations:
                    viz_data.append({
                        "Chart Type": viz.chart_type.value,
                        "Title": viz.title,
                        "X-Axis": ", ".join(viz.x_axis),
                        "Y-Axis": ", ".join(viz.y_axis),
                        "Color": viz.color_field or "None",
                        "Aggregation": viz.aggregation_type or "None"
                    })
                
                st.dataframe(pd.DataFrame(viz_data), use_container_width=True)
            else:
                st.info("No visualizations recommended")
        
        # Design recommendations
        with st.expander("🎨 Design Recommendations"):
            st.write("**Dashboard Layout:**")
            st.write(f"Confidence: {analysis.dashboard_recommendations.confidence_score:.1%}")
            st.write(analysis.dashboard_recommendations.reasoning)
            
            st.write("**Color Scheme:**")
            st.write(f"Confidence: {analysis.color_scheme_recommendation.confidence_score:.1%}")
            st.write(analysis.color_scheme_recommendation.reasoning)
        
        # Performance considerations
        if analysis.performance_considerations:
            with st.expander("⚡ Performance Considerations"):
                for consideration in analysis.performance_considerations:
                    st.write(f"• {consideration}")
    
    def render_generation_tab(self):
        """
        Render dashboard generation interface.
        
        Validates data upload, requirements, and analysis.
        Shows generation progress and result download button.
        """
        st.header("📊 Generate Dashboard")
        
        if not st.session_state.uploaded_data:
            st.warning("Please upload data first!")
            return
        
        if not st.session_state.get('requirements'):
            st.warning("Please specify requirements first!")
            return
        
        if not st.session_state.get('ai_analysis'):
            st.warning("Please run AI analysis first!")
            return
        
        # Generation status
        if st.session_state.workflow_status == 'generating':
            st.info("🔄 Dashboard generation in progress...")
            
            # Show progress (placeholder)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # This would typically be replaced with real progress tracking
            for i in range(100):
                progress_bar.progress(i + 1)
                status_text.text(f"Generating dashboard... {i+1}%")
                time.sleep(0.05)
            
            st.session_state.workflow_status = 'ready'
            st.success("Dashboard generation complete!")
            st.experimental_rerun()
        
        # Generation button
        if st.button("🎨 Generate Tableau Dashboard", type="primary", use_container_width=True):
            self.start_dashboard_generation()
        
        # Display generation result
        if st.session_state.generation_result:
            self.display_generation_result()
    
    def start_dashboard_generation(self):
        """
        Start the complete dashboard generation workflow.
        
        Runs workflow.run_workflow asynchronously with dataset schema,
        business goals, audience, and preferences. Stores result in
        session_state.generation_result.
        """
        try:
            st.session_state.workflow_status = 'generating'
            
            with st.spinner("🎨 Generating your Tableau dashboard..."):
                # Run the complete workflow
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    result = loop.run_until_complete(
                        self.workflow.run_workflow(
                            dataset_schema=st.session_state.uploaded_data['schema'],
                            business_goals=st.session_state.requirements['business_goals'],
                            target_audience=st.session_state.requirements['target_audience'],
                            user_preferences=st.session_state.requirements['preferences']
                        )
                    )
                    
                    st.session_state.generation_result = result
                    
                finally:
                    loop.close()
            
            st.session_state.workflow_status = 'completed'
            
            if st.session_state.generation_result['success']:
                st.success("🎉 Dashboard generated successfully!")
            else:
                st.error("❌ Dashboard generation failed!")
            
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Generation failed: {e}")
            logger.error(f"Dashboard generation failed: {e}")
            st.session_state.workflow_status = 'ready'
    
    def display_generation_result(self):
        """
        Display generation results and download options.
        
        Shows execution metrics, workbook details, download button,
        and any warnings or errors from generation.
        """
        result = st.session_state.generation_result
        
        if result['success']:
            st.success("✅ Dashboard Generated Successfully!")
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Execution Time", f"{result['execution_time_seconds']:.1f}s")
            
            with col2:
                st.metric("Warnings", len(result.get('warnings', [])))
            
            with col3:
                workbook_spec = result['generation_result'].workbook_spec
                total_worksheets = sum(len(d.worksheets) for d in workbook_spec.dashboards)
                st.metric("Worksheets", total_worksheets)
            
            # File download
            if result['generation_result'] and result['generation_result'].file_path:
                file_path = Path(result['generation_result'].file_path)
                
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    st.download_button(
                        label="📥 Download Tableau Workbook",
                        data=file_data,
                        file_name=file_path.name,
                        mime="application/octet-stream",
                        use_container_width=True
                    )
                    
                    st.info(f"💾 File saved as: {file_path.name}")
            
            # Display workbook details
            if result['generation_result']:
                with st.expander("📋 Workbook Details"):
                    workbook_spec = result['generation_result'].workbook_spec
                    
                    workbook_info = {
                        "Name": workbook_spec.name,
                        "Description": workbook_spec.description,
                        "Dashboards": len(workbook_spec.dashboards),
                        "Created By": workbook_spec.created_by,
                        "Version": workbook_spec.version,
                        "Data Source": workbook_spec.data_source
                    }
                    
                    st.json(workbook_info)
            
            # Display warnings if any
            if result.get('warnings'):
                with st.expander("⚠️ Generation Warnings"):
                    for warning in result['warnings']:
                        st.warning(warning)
        
        else:
            st.error("❌ Dashboard generation failed!")
            
            # Display errors
            if result.get('errors'):
                st.subheader("Error Details:")
                for error in result['errors']:
                    st.error(error)

# Create and run the app
def main():
    """
    Main entry point for the Streamlit app.
    
    Creates StreamlitApp instance and runs it.
    Catches initialization errors and displays to UI.
    """
    try:
        app = StreamlitApp()
        app.run()
    except Exception as e:
        st.error(f"Application failed to start: {e}")
        logger.error(f"Streamlit app failed: {e}")

if __name__ == "__main__":
    main()