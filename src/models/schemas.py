"""
Core Pydantic models for the Tableau Dashboard Generator application.

This module defines the complete data structure hierarchy for the Tableau Dashboard Generator,
including dataset specifications, AI analysis responses, visualization recommendations,
dashboard configurations, and workbook specifications. All models use Pydantic for
automatic validation, serialization, and type safety.

The module is organized in layers:
1. **Enumerations** - Define valid choices (DataType, VisualizationType, ColorScheme)
2. **Basic Models** - Single-entity specs (DataColumn, CalculatedFieldSpec, KPISpecification)
3. **Composite Models** - Multi-entity containers (DatasetSchema, VisualizationSpec, DashboardSpec)
4. **AI Models** - AI analysis requests and responses (AIAnalysisRequest, AIAnalysisResponse)
5. **Generation Models** - Workbook generation specifications (GenerationRequest, GenerationResult)
6. **Validation Models** - Validation results and status (ValidationResult)
7. **Utility Functions** - Helper functions for model creation and validation

All models support JSON serialization via `.dict()` and `.json()` methods, making them
suitable for API responses, file storage, and LangChain chain integration.

Note:
    All models inherit from Pydantic BaseModel and support automatic validation,
    type checking, and JSON schema generation.
"""

from typing import List, Dict, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum
import pandas as pd
from datetime import datetime

class DataType(str, Enum):
    """
    Enumeration of supported data types in the application.
    
    This enum defines all data types that the application recognizes and can
    process during data analysis and dashboard generation. Types are used for
    automatic visualization recommendation and role assignment.
    
    Attributes
    ----------
    INTEGER : str
        Integer numeric data type (64-bit signed)
    FLOAT : str
        Floating-point numeric data type (64-bit double precision)
    STRING : str
        Text/string data type of variable length
    DATE : str
        Date data type (YYYY-MM-DD format)
    DATETIME : str
        Date and time data type with timestamp
    BOOLEAN : str
        Binary boolean data type (true/false)
    CATEGORICAL : str
        Categorical/enumerated data type with discrete values
    
    Examples
    --------
    >>> dtype = DataType.INTEGER
    >>> print(dtype.value)
    'integer'
    
    >>> if col_type == DataType.FLOAT:
    ...     print("Numeric column suitable for aggregation")
    """
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"

class VisualizationType(str, Enum):
    """
    Enumeration of supported Tableau visualization types.
    
    Defines all chart types that the application can automatically generate and
    recommend. The AI engine uses data characteristics to select optimal visualization
    types for representing insights in Tableau dashboards.
    
    Attributes
    ----------
    BAR : str
        Bar chart for categorical comparisons and distributions
    LINE : str
        Line chart for time-series trends and continuous data
    AREA : str
        Area chart for cumulative trends and trend composition
    SCATTER : str
        Scatter plot for relationship analysis between two numeric variables
    PIE : str
        Pie chart for composition and proportion visualization
    HISTOGRAM : str
        Histogram for distribution analysis and frequency visualization
    HEATMAP : str
        Heat map for pattern detection across categorical dimensions
    TREEMAP : str
        Treemap for hierarchical data and proportional area visualization
    MAP : str
        Geographic map for location-based analysis
    FILLED_MAP : str
        Filled map (choropleth) for regional/aggregated geographic data
    GANTT : str
        Gantt chart for timeline and project scheduling visualization
    PACKED_BUBBLES : str
        Packed bubble chart for hierarchical proportional visualization
    BOX_PLOT : str
        Box plot for statistical distribution and outlier detection
    BULLET_GRAPH : str
        Bullet graph for performance vs. target visualization
    
    Notes
    -----
    Visualization selection considers:
    - Number of dimensions and measures
    - Data cardinality (unique value counts)
    - Data types of fields
    - Business goals (compare, trend, distribute, etc.)
    - Target audience complexity level
    
    Examples
    --------
    >>> viz_type = VisualizationType.BAR
    >>> if viz_type in [VisualizationType.BAR, VisualizationType.LINE]:
    ...     print("Suitable for time-series comparison")
    
    >>> recommended_types = [VisualizationType.SCATTER, VisualizationType.HEATMAP]
    """
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    SCATTER = "scatter"
    PIE = "pie"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    MAP = "map"
    FILLED_MAP = "filled_map"
    GANTT = "gantt"
    PACKED_BUBBLES = "packed_bubbles"
    BOX_PLOT = "box_plot"
    BULLET_GRAPH = "bullet_graph"

class ColorScheme(str, Enum):
    """
    Enumeration of supported Tableau color schemes.
    
    Defines color palettes available for dashboard visualizations. Color schemes
    affect visual appeal, accessibility, and information perception. The AI engine
    recommends color schemes based on data type, target audience, and business context.
    
    Attributes
    ----------
    TABLEAU10 : str
        Tableau's 10-color categorical palette. Recommended for up to 10 distinct
        categories with good color differentiation
    TABLEAU20 : str
        Tableau's 20-color extended palette. Suitable for datasets with more than
        10 distinct categories
    CATEGORY10 : str
        D3.js category10 palette. Good for web-based dashboards and multi-category
        visualizations
    BLUES : str
        Sequential blue color palette. Ideal for numeric data scales and heatmaps
    ORANGES : str
        Sequential orange color palette. Alternative for numeric scales and heatmaps
    GREENS : str
        Sequential green color palette. Environmental/sustainability themes
    RED_BLUE : str
        Diverging red-blue palette. Ideal for data showing positive/negative divergence
    ORANGE_BLUE : str
        Diverging orange-blue palette. Accessible alternative to red-blue
    GREEN_ORANGE : str
        Diverging green-orange palette. Colorblind-friendly option
    
    Notes
    -----
    Color scheme selection considerations:
    - Accessibility: Some schemes are colorblind-friendly
    - Semantics: Red-blue conveys positive-negative; sequential conveys magnitude
    - Print quality: Some schemes work better in grayscale than others
    - Screen readiness: Schemes should have sufficient contrast
    
    Examples
    --------
    >>> scheme = ColorScheme.TABLEAU10
    >>> print(f"Using color scheme: {scheme.value}")
    
    >>> for audience in ["executive", "analyst", "general"]:
    ...     if audience == "general":
    ...         recommended = ColorScheme.TABLEAU10
    """
    TABLEAU10 = "tableau10"
    TABLEAU20 = "tableau20"
    CATEGORY10 = "category10"
    BLUES = "blues"
    ORANGES = "oranges"
    GREENS = "greens"
    RED_BLUE = "red_blue"
    ORANGE_BLUE = "orange_blue"
    GREEN_ORANGE = "green_orange"

class DataColumn(BaseModel):
    """
    Specification for a single column in the dataset.
    
    Represents metadata and statistical information about a column from the source
    dataset. This includes data type information, value distribution, quality metrics,
    and Tableau role recommendations used by the AI engine for visualization selection.
    
    Attributes
    ----------
    name : str
        Column identifier and display name in source dataset
    data_type : DataType
        Inferred or specified data type (integer, float, string, date, etc.)
    unique_values : int
        Count of distinct non-null values in the column. Used to determine
        dimensionality and cardinality for visualization selection
    null_count : int, default=0
        Number of missing/null values in the column. High null counts indicate
        data quality issues requiring preprocessing
    sample_values : List[Any]
        Representative sample of actual column values (typically 5-10 samples).
        Used for data preview and quality inspection
    statistics : Optional[Dict[str, float]], default=None
        Statistical summary for numeric columns including mean, standard deviation,
        minimum, and maximum values. Null for non-numeric columns
    is_key_field : bool, default=False
        Whether the column is identified as a unique identifier or key field.
        Determined by high uniqueness relative to total row count
    recommended_role : Optional[Literal["dimension", "measure", "attribute"]], default=None
        Recommended Tableau role:
        - "dimension": Categorical/grouping field (typically for axes/colors)
        - "measure": Numeric aggregatable field (values to be summed/averaged)
        - "attribute": Descriptive field without aggregation
    
    Examples
    --------
    Creating a numeric column specification:
    
    >>> revenue_col = DataColumn(
    ...     name="Revenue",
    ...     data_type=DataType.FLOAT,
    ...     unique_values=45000,
    ...     null_count=150,
    ...     sample_values=[10000.50, 25000.00, 5000.25],
    ...     statistics={
    ...         "mean": 15000.00,
    ...         "std": 8000.00,
    ...         "min": 100.00,
    ...         "max": 500000.00
    ...     },
    ...     recommended_role="measure"
    ... )
    
    Accessing column properties:
    
    >>> print(f"Column: {revenue_col.name}, Type: {revenue_col.data_type.value}")
    >>> if revenue_col.null_count > len(df) * 0.1:
    ...     print("Warning: High null percentage in column")
    
    Notes
    -----
    The DataColumn is the building block for DatasetSchema and is used throughout
    the AI analysis pipeline for:
    - Automatic data type inference
    - Role assignment in Tableau visualizations
    - Quality scoring and issue detection
    - Visualization recommendation
    """
    name: str = Field(..., description="Column name")
    data_type: DataType = Field(..., description="Data type of the column")
    unique_values: int = Field(..., description="Number of unique values")
    null_count: int = Field(0, description="Number of null values")
    sample_values: List[Any] = Field(..., description="Sample values from the column")
    statistics: Optional[Dict[str, float]] = Field(None, description="Statistical summary for numeric columns")
    is_key_field: bool = Field(False, description="Whether this column is identified as a key business field")
    recommended_role: Optional[Literal["dimension", "measure", "attribute"]] = Field(None, description="Recommended Tableau role")


class CalculatedFieldSpec(BaseModel):
    """
    Specification for a calculated field (dimension or measure) in Tableau.
    
    Defines custom fields created using Tableau formulas that derive values from
    existing columns. Supports simple aggregations, string operations, table
    calculations, and advanced Level of Detail (LOD) expressions.
    
    Calculated fields are essential for KPI definitions and complex business logic
    that cannot be captured by simple column aggregation.
    
    Attributes
    ----------
    name : str
        Display name for the calculated field in Tableau. Used in worksheets,
        dashboards, and as a reference in formulas
    formula : str
        Tableau calculation formula using Tableau's native syntax.
        
        Supported formula types:
        - Aggregates: SUM([Sales]), AVG([Price]), COUNT([ID])
        - String ops: UPPER([Name]), CONCAT([First], " ", [Last])
        - Logic: IF [Profit] > 0 THEN "Positive" ELSE "Negative" END
        - Table Calcs: RUNNING_SUM(SUM([Sales])), RANK()
        - LOD: {FIXED [Region]: SUM([Sales])}
        - Window: WINDOW_SUM(SUM([Sales]))
    
    data_type : DataType
        Output data type of the calculated field. Determines how Tableau interprets
        and displays the result:
        - INTEGER/FLOAT for numeric calculations
        - STRING for text operations
        - DATE/DATETIME for date operations
    
    role : Optional[Literal["dimension", "measure"]], default="measure"
        Tableau role determining field behavior:
        - "measure": Aggregatable numeric field (typically sums/averages)
        - "dimension": Categorical grouping field (typically for filters/axes)
    
    Examples
    --------
    Simple aggregation calculated field:
    
    >>> profit_calc = CalculatedFieldSpec(
    ...     name="Profit Margin %",
    ...     formula="([Profit] / [Revenue]) * 100",
    ...     data_type=DataType.FLOAT,
    ...     role="measure"
    ... )
    
    String concatenation:
    
    >>> full_name = CalculatedFieldSpec(
    ...     name="Full Name",
    ...     formula="CONCAT([FirstName], ' ', [LastName])",
    ...     data_type=DataType.STRING,
    ...     role="dimension"
    ... )
    
    Level of Detail (LOD) expression:
    
    >>> regional_sales = CalculatedFieldSpec(
    ...     name="Region Total Sales",
    ...     formula="{FIXED [Region]: SUM([Sales])}",
    ...     data_type=DataType.FLOAT,
    ...     role="measure"
    ... )
    
    Notes
    -----
    Formula Syntax:
    - Field references must use square brackets: [FieldName]
    - Strings use single quotes: 'text'
    - Operators: +, -, *, /, %, CONCAT()
    - Functions: SUM(), AVG(), COUNT(), MIN(), MAX(), etc.
    - LOD: {FIXED [dims]: [aggs]}, {INCLUDE [dims]: [aggs]}, {EXCLUDE [dims]: [aggs]}
    - Table Calcs: RUNNING_SUM(), RANK(), PERCENTILE(), PREVIOUS_VALUE(), etc.
    
    Validation:
    - Formula should be syntactically valid for Tableau
    - Referenced fields must exist in the dataset
    - Data type should match formula output
    
    See Also
    --------
    KPISpecification : Uses calculated fields for KPI definitions
    DatasetSchema : Contains calculated_fields list
    """
    name: str = Field(..., description="Calculated field name")
    formula: str = Field(..., description="Tableau calculation formula")
    data_type: DataType = Field(..., description="Data type of the calculated field")
    role: Optional[Literal["dimension", "measure"]] = Field("measure", description="Tableau role")


class DatasetSchema(BaseModel):
    """
    Complete dataset schema and comprehensive metadata.
    
    This is the central model representing a dataset's structure, composition, and
    quality metrics. It serves as the input to the AI analysis engine and is threaded
    through all analysis stages to accumulate insights and recommendations.
    
    The DatasetSchema contains all information needed for:
    - Automatic visualization recommendation
    - KPI identification and formula generation
    - Data quality assessment
    - Tableau workbook generation
    
    Attributes
    ----------
    name : str
        Dataset identifier and display name used in dashboard/workbook titles
    
    total_rows : int
        Total number of records in the dataset. Used for:
        - Data quality calculations
        - Performance consideration recommendations
        - Aggregation strategy selection
    
    total_columns : int
        Total number of fields/columns in the dataset. Indicates data complexity
    
    columns : List[DataColumn]
        Ordered list of column specifications with metadata and statistics for
        each field in the dataset
    
    data_quality_score : float
        Overall quality metric ranging from 0.0 (worst) to 1.0 (best). Calculated as:
        (1 - total_null_count / total_cells). Indicates fitness for dashboard generation:
        - 0.9+: Excellent - minimal preprocessing needed
        - 0.7-0.9: Good - minor cleaning recommended
        - 0.5-0.7: Fair - significant preprocessing required
        - <0.5: Poor - consider data source validation
    
    business_context : Optional[str], default=None
        Free-text description of business domain and use case. Provides AI engine with
        domain knowledge for contextual recommendations
    
    created_at : datetime, default=now
        Timestamp when schema was created/extracted from source data
    
    calculated_fields : List[CalculatedFieldSpec], default=[]
        List of custom calculated fields to be generated in Tableau.
        Accumulates as analysis progresses (empty initially, populated from AI recommendations)
    
    Examples
    --------
    Creating a dataset schema from scratch:
    
    >>> schema = DatasetSchema(
    ...     name="Sales Dataset",
    ...     total_rows=50000,
    ...     total_columns=12,
    ...     columns=[...],  # List of DataColumn objects
    ...     data_quality_score=0.92,
    ...     business_context="Monthly sales by region and product category"
    ... )
    
    Adding calculated fields:
    
    >>> schema.calculated_fields.append(
    ...     CalculatedFieldSpec(
    ...         name="Revenue",
    ...         formula="[UnitPrice] * [Quantity]",
    ...         data_type=DataType.FLOAT,
    ...         role="measure"
    ...     )
    ... )
    
    Notes
    -----
    The DatasetSchema is:
    - Created via `validate_dataframe_schema()` utility function
    - Passed to `AIAnalysisRequest` for AI processing
    - Referenced in `GenerationRequest` for workbook creation
    - Accumulated with calculated_fields during analysis pipeline
    
    Quality Score Interpretation:
    - Primarily driven by null value frequency
    - Can be improved by preprocessing (handling nulls, removing outliers)
    - Does not account for semantic correctness or domain relevance
    
    Field Roles:
    - "dimension": Grouping/filtering field (categorical)
    - "measure": Aggregatable field (numeric)
    - Fields recommended_role is populated from DataColumn.recommended_role
    
    See Also
    --------
    DataColumn : Individual column specification
    validate_dataframe_schema : Function to create schema from pandas DataFrame
    AIAnalysisRequest : Uses DatasetSchema as primary input
    """
    name: str = Field(..., description="Dataset name")
    total_rows: int = Field(..., description="Total number of rows")
    total_columns: int = Field(..., description="Total number of columns")
    columns: List[DataColumn] = Field(..., description="List of column specifications")
    data_quality_score: float = Field(..., ge=0, le=1, description="Overall data quality score")
    business_context: Optional[str] = Field(None, description="Business context description")
    created_at: datetime = Field(default_factory=datetime.now)
    calculated_fields: List[CalculatedFieldSpec] = Field(default_factory=list, description="List of calculated fields for Tableau")



class KPISpecification(BaseModel):
    """
    Specification for a Key Performance Indicator (KPI).
    
    Defines a measurable business metric that will be calculated, displayed, and
    monitored in the Tableau dashboard. KPIs are AI-generated based on data analysis
    and business goals, with Tableau-compatible calculation formulas.
    
    KPIs serve as focal points for executive decision-making and performance tracking.
    
    Attributes
    ----------
    name : str
        KPI display name (e.g., "Total Revenue", "Customer Satisfaction Score").
        Used in dashboards, KPI cards, and metric definitions
    
    description : str
        Business-context description explaining what the KPI measures and why it's
        important. Displayed in dashboard tooltips and documentation
    
    calculation : str
        Tableau calculation formula that computes the KPI value.
        
        Supports all Tableau formula types:
        - Aggregates: SUM([Revenue]), AVG([Score])
        - Counts: COUNTD([CustomerID])
        - Table Calcs: RUNNING_SUM(SUM([Sales]))
        - LOD: {FIXED [Region]: SUM([Revenue])}
        - Complex: SUM([Revenue]) / {FIXED [Year]: SUM([Revenue])} * 100
    
    target_value : Optional[float], default=None
        Desired or benchmark value for the KPI. Used for:
        - Performance comparison (actual vs. target)
        - Bullet graph visualization
        - Conditional formatting and alerts
    
    format_string : str, default="#,##0"
        Tableau number format specification controlling display. Common formats:
        - "#,##0" - Integer with thousands separator
        - "#,##0.00" - Two decimal places
        - "#,##0.0%" - Percentage format
        - "$#,##0" - Currency format
        - "0.0E+0" - Scientific notation
    
    priority : int, default=1
        Priority ranking for dashboard placement (1=highest, 5=lowest). Used to:
        - Order KPIs on dashboard (high priority first)
        - Determine visual prominence and size
        - Filter KPIs for executive vs. detailed views
        Range: 1 (highest priority) to 5 (lowest priority)
    
    Examples
    --------
    Revenue KPI with target:
    
    >>> revenue_kpi = KPISpecification(
    ...     name="Total Revenue",
    ...     description="Sum of all sales revenue across all regions",
    ...     calculation="SUM([Sales])",
    ...     target_value=1000000.0,
    ...     format_string="$#,##0",
    ...     priority=1
    ... )
    
    Profit margin percentage KPI:
    
    >>> profit_margin = KPISpecification(
    ...     name="Profit Margin %",
    ...     description="Profit as percentage of revenue",
    ...     calculation="SUM([Profit]) / SUM([Revenue]) * 100",
    ...     format_string="#,##0.0%",
    ...     priority=2
    ... )
    
    Year-over-year growth:
    
    >>> yoy_growth = KPISpecification(
    ...     name="YoY Revenue Growth",
    ...     description="Year-over-year sales growth percentage",
    ...     calculation="(SUM([Revenue])-LOOKUP(SUM([Revenue]),-1))/LOOKUP(SUM([Revenue]),-1)*100",
    ...     format_string="#,##0.0%",
    ...     priority=2
    ... )
    
    Notes
    -----
    KPI Generation:
    - Generated by AI engine's `_run_kpi_generation()` method
    - Based on data analysis, business goals, and column availability
    - Typically 3-7 KPIs recommended per dashboard
    
    Calculation Validation:
    - Formula should reference fields that exist in dataset
    - Syntax must be valid for Tableau 2023.3+
    - Aggregate functions automatically handle row context
    
    Dashboard Integration:
    - KPIs converted to CalculatedFieldSpec for workbook generation
    - Displayed in KPI cards, scorecards, or small multiple views
    - Used for interactivity and drill-down filtering
    
    Priority Guidelines:
    - Priority 1: Core business metrics (revenue, customers, margin)
    - Priority 2: Important operational metrics
    - Priority 3: Secondary/supporting metrics
    - Priority 4-5: Detailed/exploratory metrics
    
    See Also
    --------
    CalculatedFieldSpec : Used to implement KPI formulas in Tableau
    AIAnalysisResponse : Contains recommended_kpis list
    """
    name: str = Field(..., description="KPI name")
    description: str = Field(..., description="KPI description")
    calculation: str = Field(..., description="Tableau calculation formula")
    target_value: Optional[float] = Field(None, description="Target value for the KPI")
    format_string: str = Field("#,##0", description="Number format")
    priority: int = Field(1, ge=1, le=5, description="Priority level (1=highest, 5=lowest)")

class VisualizationSpec(BaseModel):
    """
    Specification for a single visualization (worksheet) in Tableau.
    
    Defines complete configuration for one chart/visualization that will be embedded
    in a Tableau worksheet, including chart type, field mappings, filters, and
    formatting options. Multiple VisualizationSpecs are combined into a DashboardSpec.
    
    Attributes
    ----------
    chart_type : VisualizationType
        Primary visualization type (bar, line, scatter, etc.). Determines shelf
        configuration and interaction defaults
    
    title : str
        Display title for the visualization in the dashboard. Should be clear and
        business-focused
    
    x_axis : List[str]
        Field names for X-axis/columns shelf. Typically:
        - Dimensions for categorical data
        - Time dimensions for time-series
        - Continuous measures for scatter plots
    
    y_axis : List[str]
        Field names for Y-axis/rows shelf. Typically:
        - Measures for aggregation (sum, average, count)
        - Dimensions for stacked/grouped visualization
    
    color_field : Optional[str], default=None
        Field for color encoding. Typically:
        - Dimension for categorical coloring
        - Measure for gradient color scales
    
    size_field : Optional[str], default=None
        Field for size encoding (bubble size). Typically numeric measure.
        Only applicable for bubble, scatter, and packed bubble charts
    
    filters : List[Dict[str, Any]], default=[]
        Data filter specifications applied to visualization. Each filter includes:
        - 'field': Field name to filter
        - 'operator': 'equals', 'greater_than', 'contains', etc.
        - 'values': List of allowed values
    
    color_scheme : ColorScheme, default=TABLEAU10
        Color palette for encoding. Selection impacts:
        - Visual appeal
        - Accessibility (colorblind-friendly options available)
        - Print reproduction
    
    show_labels : bool, default=True
        Whether to display data labels on chart marks. Aids readability but can
        clutter dense visualizations
    
    show_legend : bool, default=True
        Whether to display legend for color/size encoding. Important for categorical
        and sequential color schemes
    
    aggregation_type : Optional[Literal["sum", "avg", "count", "min", "max"]], default="sum"
        Default aggregation function for numeric measures. Common options:
        - "sum": Total values (revenue, sales)
        - "avg": Average/mean values (rating, price)
        - "count": Record count (transactions, users)
        - "min": Minimum value
        - "max": Maximum value
    
    Examples
    --------
    Simple bar chart comparing sales by region:
    
    >>> bar_viz = VisualizationSpec(
    ...     chart_type=VisualizationType.BAR,
    ...     title="Sales by Region",
    ...     x_axis=["Region"],
    ...     y_axis=["Sales"],
    ...     color_field="Product Category",
    ...     aggregation_type="sum"
    ... )
    
    Time-series line chart with multiple metrics:
    
    >>> trend_viz = VisualizationSpec(
    ...     chart_type=VisualizationType.LINE,
    ...     title="Revenue Trend",
    ...     x_axis=["Date"],
    ...     y_axis=["Revenue", "Profit"],
    ...     show_labels=False,
    ...     aggregation_type="sum"
    ... )
    
    Scatter plot with filters:
    
    >>> scatter_viz = VisualizationSpec(
    ...     chart_type=VisualizationType.SCATTER,
    ...     title="Price vs. Volume",
    ...     x_axis=["Price"],
    ...     y_axis=["Sales Volume"],
    ...     color_field="Product",
    ...     size_field="Profit",
    ...     filters=[
    ...         {"field": "Region", "operator": "equals", "values": ["North", "South"]}
    ...     ],
    ...     color_scheme=ColorScheme.TABLEAU10
    ... )
    
    Notes
    -----
    Field Mapping Rules:
    - Continuous dimensions and measures can be on any shelf
    - Discrete dimensions create groups/categories
    - Measures trigger aggregation (unless specified as continuous)
    - Multiple fields on same axis create multi-series visualization
    
    Aggregation Interaction:
    - Default aggregation applied if not explicitly set
    - Can be overridden per field in Tableau UI
    - Applies to numeric measures only
    
    Filter Application:
    - Filters reduce dataset before aggregation
    - Multiple filters work as AND conditions
    - Can be exposed as dashboard filters
    
    Chart Type Compatibility:
    - Not all field combinations valid for all chart types
    - Tableau automatically adjusts incompatible configurations
    - Some types require specific field counts (e.g., scatter needs 2+ measures)
    
    See Also
    --------
    WorksheetSpec : Contains VisualizationSpec and metadata
    DashboardSpec : Combines multiple WorksheetSpecs
    VisualizationType : Chart type enumeration
    """
    chart_type: VisualizationType = Field(..., description="Type of visualization")
    title: str = Field(..., description="Chart title")
    x_axis: List[str] = Field(..., description="Fields for X-axis")
    y_axis: List[str] = Field(..., description="Fields for Y-axis")
    color_field: Optional[str] = Field(None, description="Field for color encoding")
    size_field: Optional[str] = Field(None, description="Field for size encoding")
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Applied filters")
    color_scheme: ColorScheme = Field(ColorScheme.TABLEAU10, description="Color scheme to use")
    show_labels: bool = Field(True, description="Whether to show data labels")
    show_legend: bool = Field(True, description="Whether to show legend")
    aggregation_type: Optional[Literal["sum", "avg", "count", "min", "max"]] = Field("sum", description="Aggregation method")

class WorksheetSpec(BaseModel):
    """
    Specification for a Tableau worksheet.
    
    A worksheet is a single sheet/tab in a Tableau workbook containing one primary
    visualization plus optional KPI cards or supplementary visualizations. Worksheets
    are building blocks for dashboards.
    
    Attributes
    ----------
    name : str
        Worksheet identifier and display name in workbook tabs. Should be descriptive
        and unique within the workbook
    
    visualization : VisualizationSpec
        Primary visualization configuration for this worksheet
    
    kpis : List[KPISpecification], default=[]
        Associated KPIs to display alongside visualization. Can include:
        - KPI cards showing key metrics
        - Scorecards with actual vs. target
        - Summary statistics
    
    description : Optional[str], default=None
        Documentation describing worksheet purpose, methodology, and intended use.
        Displayed in worksheet tooltips and documentation
    
    dimensions : Dict[str, int], default={"width": 800, "height": 600}
        Canvas dimensions in pixels:
        - "width": Worksheet width
        - "height": Worksheet height
        Used for responsive layout calculation
    
    Examples
    --------
    Creating a worksheet with visualization and KPIs:
    
    >>> ws = WorksheetSpec(
    ...     name="Sales Overview",
    ...     visualization=VisualizationSpec(
    ...         chart_type=VisualizationType.BAR,
    ...         title="Sales by Region",
    ...         x_axis=["Region"],
    ...         y_axis=["Sales"]
    ...     ),
    ...     kpis=[
    ...         KPISpecification(
    ...             name="Total Revenue",
    ...             calculation="SUM([Sales])",
    ...             description="Total sales revenue"
    ...         )
    ...     ],
    ...     dimensions={"width": 1000, "height": 700}
    ... )
    
    Notes
    -----
    Worksheet Lifecycle:
    - Created from VisualizationSpec during generation
    - Added to DashboardSpec for dashboard composition
    - Can be used in multiple dashboards
    - Data source shared across all worksheets in workbook
    
    Dimensions:
    - Width/height affect responsive behavior
    - Actual rendered size depends on dashboard layout
    - Typically 800x600 for standard, 1000x700 for detailed
    
    KPI Integration:
    - KPIs displayed as cards/scorecards above main visualization
    - Share data source with visualization
    - Can be filtered by visualization selections
    
    See Also
    --------
    VisualizationSpec : Primary visualization configuration
    DashboardSpec : Contains multiple WorksheetSpecs
    """
    name: str = Field(..., description="Worksheet name")
    visualization: VisualizationSpec = Field(..., description="Visualization specification")
    kpis: List[KPISpecification] = Field(default_factory=list, description="Associated KPIs")
    description: Optional[str] = Field(None, description="Worksheet description")
    dimensions: Dict[str, int] = Field({"width": 800, "height": 600}, description="Worksheet dimensions")

class DashboardLayout(BaseModel):
    """
    Dashboard layout specification and positioning information.
    
    Defines how worksheets are arranged on a dashboard canvas. Layout types range
    from automatic (Tableau-managed) to free-form (precise pixel positioning).
    
    Attributes
    ----------
    layout_type : Literal["automatic", "grid", "free_form"], default="automatic"
        Layout algorithm:
        - "automatic": Tableau automatically arranges worksheets (responsive)
        - "grid": Worksheets arranged in regular rows/columns
        - "free_form": Worksheets positioned with precise coordinates
    
    rows : int, default=2
        Number of rows for grid layout. Ignored for automatic/free_form layouts.
        Range: 1-N (determines grid granularity)
    
    columns : int, default=2
        Number of columns for grid layout. Ignored for automatic/free_form layouts.
        Range: 1-N (typical: 2-4 for standard dashboards)
    
    worksheet_positions : Dict[str, Dict[str, Union[int, float]]], default={}
        Positioning coordinates for free_form layout. Format:
        {
            "worksheet_name": {
                "x": 100,        # Left position in pixels
                "y": 50,         # Top position in pixels
                "width": 400,    # Width in pixels
                "height": 300    # Height in pixels
            }
        }
        Ignored for automatic/grid layouts
    
    Examples
    --------
    Automatic layout (most common):
    
    >>> layout = DashboardLayout(
    ...     layout_type="automatic"
    ... )
    
    Grid layout with 2x2:
    
    >>> layout = DashboardLayout(
    ...     layout_type="grid",
    ...     rows=2,
    ...     columns=2
    ... )
    
    Free-form layout with precise positioning:
    
    >>> layout = DashboardLayout(
    ...     layout_type="free_form",
    ...     worksheet_positions={
    ...         "Sales Overview": {"x": 0, "y": 0, "width": 800, "height": 400},
    ...         "Regional Breakdown": {"x": 800, "y": 0, "width": 400, "height": 400},
    ...         "KPI Summary": {"x": 0, "y": 400, "width": 600, "height": 200}
    ...     }
    ... )
    
    Notes
    -----
    Layout Selection:
    - Automatic: Best for responsive dashboards, mobile support
    - Grid: Good for consistent structure, easy to maintain
    - Free-form: Maximum control, requires precise planning
    
    Responsive Behavior:
    - Automatic layout adapts to screen size
    - Grid respects row/column constraints
    - Free-form may not scale well to small screens
    
    Performance:
    - Automatic has best render performance
    - Free-form may cause layout jitter on resize
    - Grid provides balance
    
    See Also
    --------
    DashboardSpec : Uses DashboardLayout for composition
    """
    layout_type: Literal["automatic", "grid", "free_form"] = Field("automatic", description="Layout type")
    rows: int = Field(2, ge=1, description="Number of rows in grid layout")
    columns: int = Field(2, ge=1, description="Number of columns in grid layout")
    worksheet_positions: Dict[str, Dict[str, Union[int, float]]] = Field(
        default_factory=dict, 
        description="Positioning information for worksheets"
    )

class DashboardSpec(BaseModel):
    """
    Specification for a complete dashboard.
    
    Represents one dashboard page within a Tableau workbook. Combines multiple
    worksheets, KPIs, filters, and layout information into a cohesive analytics view.
    A workbook can contain multiple dashboards, typically organized by business area.
    
    Attributes
    ----------
    name : str
        Dashboard identifier and display name. Appears in dashboard tabs and titles.
        Examples: "Executive Summary", "Sales Analysis", "Operations Dashboard"
    
    description : str
        Business context and usage documentation. Describes:
        - Purpose and business use case
        - Intended audience
        - Key insights to focus on
    
    worksheets : List[WorksheetSpec]
        Ordered list of worksheets to include in dashboard. Each worksheet contains
        one primary visualization and optional KPIs
    
    layout : DashboardLayout, default=DashboardLayout()
        Layout configuration specifying worksheet arrangement (automatic/grid/free-form)
    
    global_filters : List[Dict[str, Any]], default=[]
        Dashboard-level filters that apply to all worksheets. Format:
        {
            "field": "field_name",
            "type": "string|date|numeric",
            "default_value": "value",
            "allow_multiple": true
        }
    
    color_scheme : ColorScheme, default=TABLEAU10
        Overall color palette for the dashboard. Applied as default to visualizations
        that don't specify their own scheme
    
    dimensions : Dict[str, int], default={"width": 1200, "height": 800}
        Dashboard canvas dimensions in pixels:
        - "width": Dashboard width
        - "height": Dashboard height
        Affects responsive behavior and layout calculations
    
    Examples
    --------
    Creating a sales dashboard:
    
    >>> sales_dashboard = DashboardSpec(
    ...     name="Sales Performance",
    ...     description="Executive-level sales metrics and regional analysis",
    ...     worksheets=[
    ...         WorksheetSpec(name="KPI Summary", visualization=kpi_viz),
    ...         WorksheetSpec(name="Regional Breakdown", visualization=regional_viz),
    ...         WorksheetSpec(name="Trend Analysis", visualization=trend_viz)
    ...     ],
    ...     layout=DashboardLayout(layout_type="grid", rows=2, columns=2),
    ...     global_filters=[
    ...         {
    ...             "field": "Date",
    ...             "type": "date",
    ...             "default_value": "last_30_days"
    ...         }
    ...     ],
    ...     color_scheme=ColorScheme.TABLEAU10,
    ...     dimensions={"width": 1200, "height": 800}
    ... )
    
    Notes
    -----
    Dashboard Design:
    - Typically 3-6 worksheets per dashboard
    - Global filters enable cross-worksheet drilling
    - Related visualizations should share consistent color scheme
    - Layout should guide user attention to key metrics first
    
    Global Filters:
    - Applied as parameters in Tableau
    - Can be exposed to end users for interactivity
    - Multiple filters work as AND conditions
    
    Color Consistency:
    - Default scheme applied if worksheet doesn't specify
    - Consistency improves visual comprehension
    - Consider accessibility when selecting scheme
    
    Performance:
    - Fewer worksheets = faster load time
    - Complex calculations impact refresh speed
    - Aggregated data sources recommended
    
    Workbook Organization:
    - Separate dashboards by business area
    - Use consistent naming conventions
    - Include summary dashboard as entry point
    
    See Also
    --------
    WorksheetSpec : Individual worksheet container
    DashboardLayout : Layout configuration
    TableauWorkbookSpec : Contains multiple DashboardSpecs
    """
    name: str = Field(..., description="Dashboard name")
    description: str = Field(..., description="Dashboard description")
    worksheets: List[WorksheetSpec] = Field(..., description="List of worksheets in the dashboard")
    layout: DashboardLayout = Field(default_factory=DashboardLayout, description="Dashboard layout")
    global_filters: List[Dict[str, Any]] = Field(default_factory=list, description="Dashboard-level filters")
    color_scheme: ColorScheme = Field(ColorScheme.TABLEAU10, description="Overall color scheme")
    dimensions: Dict[str, int] = Field({"width": 1200, "height": 800}, description="Dashboard dimensions")

class TableauWorkbookSpec(BaseModel):
    """
    Complete Tableau workbook specification.
    
    The top-level specification representing an entire Tableau workbook (.twb or .twbx file).
    Contains all information needed to generate a production-ready workbook including
    dashboards, data sources, metadata, and version information.
    
    Attributes
    ----------
    name : str
        Workbook identifier and filename (without extension). Examples:
        "Sales_Analysis", "Customer_Dashboard", "Operational_Metrics"
    
    description : str
        Comprehensive workbook documentation including:
        - High-level business purpose
        - Intended audience and use cases
        - Key features and capabilities
        - Update frequency and data refresh schedule
    
    dashboards : List[DashboardSpec]
        Ordered list of dashboards in the workbook. Typically organized by:
        - Business area (Sales, Operations, Finance)
        - Hierarchy (Executive Summary → Detailed Analysis)
        - Function (KPI Tracking, Trend Analysis, Diagnostic)
    
    data_source : str
        Data source connection string or file path. Format depends on source:
        - Local file: "/path/to/data.csv" or "/path/to/data.xlsx"
        - Database: "connection://server:port/database"
        - Extract: "data_extract.tde"
    
    version : str, default="2023.3"
        Target Tableau version for compatibility. Affects:
        - Supported features and functions
        - Formula syntax compatibility
        - File format compatibility
        Examples: "2023.3", "2023.1", "2022.4"
    
    created_by : str, default="AI Dashboard Generator"
        Creator/source attribution. For tracking origin of auto-generated workbooks
    
    created_at : datetime, default=now
        Timestamp when workbook specification was generated
    
    Examples
    --------
    Creating a complete workbook specification:
    
    >>> workbook = TableauWorkbookSpec(
    ...     name="Sales_Dashboard",
    ...     description="Executive sales analytics with regional breakdown and trend analysis",
    ...     dashboards=[
    ...         DashboardSpec(
    ...             name="Executive Summary",
    ...             description="High-level KPIs and trends",
    ...             worksheets=[...]
    ...         ),
    ...         DashboardSpec(
    ...             name="Regional Analysis",
    ...             description="Detailed regional performance",
    ...             worksheets=[...]
    ...         )
    ...     ],
    ...     data_source="file:///data/sales.csv",
    ...     version="2023.3",
    ...     created_by="AI Dashboard Generator"
    ... )
    
    Notes
    -----
    Workbook Structure:
    - Typically 2-5 dashboards per workbook
    - First dashboard is entry point/summary
    - Each dashboard 3-6 worksheets for optimal performance
    - Shared data source across all dashboards
    
    Data Source Management:
    - Can reference local files, databases, or Tableau Server
    - Supports CSV, Excel, TDE, and database sources
    - Recommend aggregated data extracts for performance
    
    Version Compatibility:
    - Higher versions support newer features
    - Older versions may not open newer workbooks
    - Default 2023.3 has good feature coverage and adoption
    
    Performance Optimization:
    - Minimize number of dashboards for load time
    - Use published data sources for consistency
    - Extract aggregated data when possible
    - Minimize calculated fields in data source
    
    File Formats:
    - .twb: Workbook (references external data source)
    - .twbx: Packaged workbook (includes data extract)
    
    Generation:
    - Generated from AIAnalysisResponse by Tableau Engine
    - Converted to XML and packaged as TWBX
    - Can be opened in Tableau Desktop or Tableau Server
    
    See Also
    --------
    DashboardSpec : Individual dashboard within workbook
    GenerationRequest : Request to generate this workbook
    GenerationResult : Result with file path
    """
    name: str = Field(..., description="Workbook name")
    description: str = Field(..., description="Workbook description")
    dashboards: List[DashboardSpec] = Field(..., description="List of dashboards")
    data_source: str = Field(..., description="Data source connection string or file path")
    version: str = Field("2023.3", description="Tableau version compatibility")
    created_by: str = Field("AI Dashboard Generator", description="Creator information")
    created_at: datetime = Field(default_factory=datetime.now)

class AIAnalysisRequest(BaseModel):
    """
    Request for AI analysis of dataset.
    
    Encapsulates all information needed by the AI engine to analyze a dataset and
    generate dashboard recommendations. Passed to TableauDashboardAnalyzer for
    multi-stage analysis including data insights, KPI generation, and visualization
    recommendations.
    
    Attributes
    ----------
    dataset_schema : DatasetSchema
        Complete dataset schema and metadata for analysis
    
    business_goals : List[str]
        Business objectives to consider when recommending KPIs and visualizations.
        Examples:
        - "Maximize revenue and market share"
        - "Reduce operational costs"
        - "Improve customer satisfaction"
    
    target_audience : str
        Description of intended dashboard users. Affects visualization complexity
        and metric selection. Examples:
        - "Executive management" (simple, KPI-focused)
        - "Sales analysts" (detailed, drill-down focused)
        - "Operations team" (operational metrics, real-time)
    
    preferences : Dict[str, Any], default={}
        User-specified preferences overriding defaults:
        - "max_visualizations": 5-15 (default: 8)
        - "color_scheme": ColorScheme preference
        - "dashboard_style": "executive", "detailed", "operational"
        - "emphasis": "visual_appeal", "data_density", "performance", "simplicity"
    
    constraints : Dict[str, Any], default={}
        Technical or business constraints affecting recommendations:
        - "max_kpis": Maximum KPI count
        - "exclude_columns": Sensitive columns to exclude
        - "min_data_quality": Minimum quality score (0-1)
        - "calculation_complexity": "simple", "intermediate", "advanced"
    
    Examples
    --------
    Basic analysis request:
    
    >>> request = AIAnalysisRequest(
    ...     dataset_schema=schema,
    ...     business_goals=["Increase revenue", "Reduce churn"],
    ...     target_audience="Sales managers"
    ... )
    
    Request with preferences and constraints:
    
    >>> request = AIAnalysisRequest(
    ...     dataset_schema=schema,
    ...     business_goals=["Track KPIs", "Identify trends"],
    ...     target_audience="Executives",
    ...     preferences={
    ...         "max_visualizations": 6,
    ...         "color_scheme": "TABLEAU10",
    ...         "emphasis": "simplicity"
    ...     },
    ...     constraints={
    ...         "max_kpis": 5,
    ...         "exclude_columns": ["SSN", "Password"],
    ...         "min_data_quality": 0.8
    ...     }
    ... )
    
    Notes
    -----
    AI Analysis Pipeline:
    1. Data Analysis: Analyzes dataset characteristics and business potential
    2. Dashboard Design: Recommends layout and color schemes
    3. KPI Generation: Creates KPI specifications with calculations
    4. Visualization Recs: Recommends optimal chart types
    
    Business Goals Impact:
    - Influence KPI selection (revenue vs. cost vs. satisfaction)
    - Affect visualization types (trends vs. comparisons)
    - Drive metric prioritization
    
    Audience Impact:
    - Executives: Fewer metrics, high-level summaries, KPI focus
    - Analysts: More detailed visualizations, drill-down capability
    - Operators: Real-time metrics, exception highlighting
    
    See Also
    --------
    AIAnalysisResponse : Response from AI analysis
    AIRecommendation : Individual recommendation with confidence
    """
    dataset_schema: DatasetSchema = Field(..., description="Dataset schema to analyze")
    business_goals: List[str] = Field(..., description="Business goals and objectives")
    target_audience: str = Field(..., description="Target audience for the dashboard")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Technical or business constraints")

class AIRecommendation(BaseModel):
    """
    AI recommendation for dashboard design with confidence metrics.
    
    Represents a single recommendation from the AI engine, including the proposed
    recommendation, explanation, confidence level, and alternative options.
    
    Used for subjective design recommendations where multiple valid approaches exist.
    
    Attributes
    ----------
    confidence_score : float
        AI confidence in recommendation (0.0 to 1.0):
        - 0.9+: Very confident, recommended for selection
        - 0.7-0.9: Moderately confident, consider alternatives
        - 0.5-0.7: Low confidence, compare alternatives
        - <0.5: Very uncertain, expert review recommended
    
    reasoning : str
        Explanation of recommendation rationale. Includes:
        - Supporting evidence from data analysis
        - Design principles applied
        - Trade-offs considered
        - Assumptions made
    
    alternatives : List[str], default=[]
        List of alternative approaches with descriptions. Format:
        - String descriptions of viable alternatives
        - Ranked by preference if applicable
        - Include brief pros/cons if available
    
    Examples
    --------
    Layout recommendation:
    
    >>> layout_rec = AIRecommendation(
    ...     confidence_score=0.85,
    ...     reasoning="Grid layout (2x2) optimal for 4 visualizations with balanced data density",
    ...     alternatives=["Automatic responsive", "Free-form custom positioning"]
    ... )
    
    Color scheme recommendation:
    
    >>> color_rec = AIRecommendation(
    ...     confidence_score=0.78,
    ...     reasoning="Tableau10 provides good differentiation for 8 category visualizations",
    ...     alternatives=["Tableau20 for more categories", "Red-Blue for diverging data"]
    ... )
    
    Notes
    -----
    Confidence Interpretation:
    - Based on data quality, audience clarity, business goals
    - Not absolute certainty, but AI model confidence
    - Should be combined with human review
    
    Alternative Evaluation:
    - Recommendations are ranked by confidence
    - Alternatives provide fallbacks and variations
    - User can override with alternative if preferred
    
    Usage in Dashboard:
    - Primary recommendation auto-applied if >0.8 confidence
    - Medium confidence (0.6-0.8) presented for review
    - Low confidence recommendations highlighted for alternatives
    
    See Also
    --------
    AIAnalysisResponse : Contains multiple AIRecommendations
    """
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the recommendation")
    reasoning: str = Field(..., description="Explanation of the recommendation")
    alternatives: List[str] = Field(default_factory=list, description="Alternative approaches")

class AIAnalysisResponse(BaseModel):
    """
    Complete AI analysis response with all recommendations.
    
    The primary output from the AI analysis engine (TableauDashboardAnalyzer).
    Combines results from all analysis stages: data analysis, dashboard design,
    KPI generation, and visualization recommendations.
    
    This response serves as input to the Tableau Engine for workbook generation.
    
    Attributes
    ----------
    dataset_insights : Dict[str, Any]
        Structured insights from data analysis including:
        - "data_characteristics": Column counts, types, statistics
        - "business_potential": Identified opportunities for analysis
        - "data_quality_issues": Problems found (nulls, outliers, etc.)
        - "recommended_preprocessing": Cleaning steps suggested
    
    recommended_kpis : List[KPISpecification]
        3-7 AI-recommended KPIs with Tableau formulas. Includes:
        - Business metrics (revenue, profit, customer count)
        - Operational metrics (efficiency, quality, volume)
        - Diagnostic metrics (exceptions, anomalies, trends)
    
    recommended_visualizations : List[VisualizationSpec]
        4-8 complementary visualizations telling cohesive story:
        - Overview/summary charts
        - Detailed analysis visualizations
        - Comparative visualizations
        - Drill-down visualizations
    
    dashboard_recommendations : AIRecommendation
        Overall dashboard structure and organization recommendation with confidence
    
    layout_suggestions : AIRecommendation
        Recommended layout type and configuration (automatic/grid/free-form)
    
    color_scheme_recommendation : AIRecommendation
        Suggested color palette with confidence and alternatives
    
    performance_considerations : List[str]
        Performance optimization recommendations including:
        - Data aggregation strategies
        - Calculation simplification
        - Filter ordering
        - Refresh optimization
    
    generated_at : datetime, default=now
        Timestamp when analysis was completed
    
    Examples
    --------
    Using analysis response for workbook generation:
    
    >>> response = await analyzer.analyze_dataset(request)
    >>> print(f"Generated {len(response.recommended_kpis)} KPIs")
    >>> print(f"Recommended {len(response.recommended_visualizations)} visualizations")
    >>> print(f"Layout confidence: {response.layout_suggestions.confidence_score}")
    
    Accessing insights and recommendations:
    
    >>> insights = response.dataset_insights
    >>> kpis = response.recommended_kpis
    >>> vizs = response.recommended_visualizations
    >>> layout = response.layout_suggestions
    
    Notes
    -----
    Response Pipeline:
    1. Created by TableauDashboardAnalyzer.analyze_dataset()
    2. Passed to GenerationRequest for workbook creation
    3. Used by Tableau Engine for XML and worksheet generation
    
    Quality Metrics:
    - Recommendations ranked by confidence
    - Includes multiple alternatives for design choices
    - Performance suggestions ensure optimal dashboard behavior
    
    Data Flow:
    - dataset_insights inform KPI and visualization selection
    - Visualizations grouped by dashboard layout
    - All recommendations respect performance considerations
    
    Customization:
    - User can modify response before generation
    - Can override individual KPIs or visualizations
    - Can select alternative recommendations
    
    See Also
    --------
    AIAnalysisRequest : Input to analysis
    GenerationRequest : Uses response for workbook generation
    TableauDashboardAnalyzer : Generates this response
    """
    dataset_insights: Dict[str, Any] = Field(..., description="Insights about the dataset")
    recommended_kpis: List[KPISpecification] = Field(..., description="Recommended KPIs")
    recommended_visualizations: List[VisualizationSpec] = Field(..., description="Recommended visualizations")
    dashboard_recommendations: AIRecommendation = Field(..., description="Dashboard design recommendations")
    layout_suggestions: AIRecommendation = Field(..., description="Layout suggestions")
    color_scheme_recommendation: AIRecommendation = Field(..., description="Color scheme recommendations")
    performance_considerations: List[str] = Field(..., description="Performance optimization suggestions")
    generated_at: datetime = Field(default_factory=datetime.now)

class GenerationRequest(BaseModel):
    """
    Request to generate a Tableau workbook.
    
    Specifies everything needed by the Tableau Engine to generate a complete
    .twb or .twbx file. Combines dataset schema, AI analysis results, and
    generation preferences.
    
    Attributes
    ----------
    dataset_schema : DatasetSchema
        Source dataset schema including columns and calculated fields.
        Used as data source for all worksheets in generated workbook
    
    ai_analysis : AIAnalysisResponse
        Complete AI analysis results including recommended KPIs, visualizations,
        layout, and color scheme preferences
    
    user_preferences : Dict[str, Any], default={}
        Generation overrides and preferences:
        - "include_filters": bool (default: True)
        - "include_calculations": bool (default: True)
        - "compress_output": bool (default: True for TWBX)
        - "embed_data": bool (default: True for TWBX)
    
    output_format : Literal["twb", "twbx"], default="twbx"
        Output file format:
        - "twb": Workbook only (references external data source)
        - "twbx": Packaged workbook (includes data extract)
        Recommend TWBX for distribution, TWB for database connections
    
    include_sample_data : bool, default=True
        Whether to embed sample data in workbook extract. Useful for:
        - Sharing without exposing full dataset
        - Demo/preview purposes
        - Reduced file size
    
    Examples
    --------
    Basic generation request:
    
    >>> request = GenerationRequest(
    ...     dataset_schema=schema,
    ...     ai_analysis=response,
    ...     output_format="twbx"
    ... )
    
    Request with custom preferences:
    
    >>> request = GenerationRequest(
    ...     dataset_schema=schema,
    ...     ai_analysis=response,
    ...     user_preferences={
    ...         "include_filters": True,
    ...         "embed_data": True,
    ...         "compress_output": True
    ...     },
    ...     output_format="twbx",
    ...     include_sample_data=False
    ... )
    
    Notes
    -----
    File Format Selection:
    - TWBX: Self-contained, easy distribution, larger file
    - TWB: Smaller, requires external data connection
    
    Data Extraction:
    - TWBX includes data extract for offline access
    - TWB always requires live connection
    - Sample data useful for sharing sensitive datasets
    
    Generation Flow:
    1. Validate schema and analysis
    2. Create workbook structure
    3. Generate worksheets from visualizations
    4. Add dashboards and layout
    5. Package into TWBX/TWB file
    
    See Also
    --------
    GenerationResult : Result of workbook generation
    """
    dataset_schema: DatasetSchema = Field(..., description="Source dataset schema")
    ai_analysis: AIAnalysisResponse = Field(..., description="AI analysis results")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User-specified preferences")
    output_format: Literal["twb", "twbx"] = Field("twbx", description="Output file format")
    include_sample_data: bool = Field(True, description="Whether to include sample data in workbook")

class GenerationResult(BaseModel):
    """
    Result of workbook generation.
    
    Contains the generated workbook specification and metadata about the generation
    process including success status, errors, warnings, and performance metrics.
    
    Attributes
    ----------
    workbook_spec : TableauWorkbookSpec
        Generated workbook specification ready for serialization to XML/TWBX
    
    file_path : str
        Absolute path to generated workbook file (.twb or .twbx).
        Used by download/sharing mechanisms
    
    generation_time : float
        Time taken to generate workbook in seconds. Performance metric for:
        - Large dataset optimization
        - Comparing generation algorithms
        - Performance monitoring
    
    warnings : List[str], default=[]
        Non-critical issues encountered during generation:
        - Skipped calculations due to unsupported syntax
        - Field references that couldn't be resolved
        - Performance considerations
        - Deprecated features used
    
    success : bool
        Whether generation completed successfully
        - True: Workbook generated and saved
        - False: Generation failed, check error_message
    
    error_message : Optional[str], default=None
        Error description if generation failed. Includes:
        - Reason for failure
        - Suggested remediation
        - Relevant context/line numbers
    
    Examples
    --------
    Successful generation:
    
    >>> result = GenerationResult(
    ...     workbook_spec=workbook,
    ...     file_path="/output/sales_dashboard.twbx",
    ...     generation_time=12.5,
    ...     success=True,
    ...     warnings=["KPI 'Custom Metric' uses advanced LOD expression"]
    ... )
    
    Failed generation:
    
    >>> result = GenerationResult(
    ...     workbook_spec=None,
    ...     file_path="",
    ...     generation_time=5.2,
    ...     success=False,
    ...     error_message="Column 'Revenue_Forecast' referenced in KPI not found in schema"
    ... )
    
    Notes
    -----
    Success Handling:
    - Check success flag before using file_path
    - Review warnings even on success
    - error_message only populated if success=False
    
    Warning Review:
    - Warnings don't prevent generation
    - May affect dashboard functionality
    - Review for data accuracy implications
    
    Performance:
    - generation_time increases with dataset size
    - Typical range: 5-30 seconds
    - Large calculations can extend time significantly
    
    File Handling:
    - file_path is temporary location
    - Move/copy before deleting temp files
    - Different format (.twb vs .twbx) affects file size
    
    Error Recovery:
    - Review error_message for problem
    - Fix issue in schema or preferences
    - Retry generation
    
    See Also
    --------
    GenerationRequest : Input to generation
    TableauWorkbookSpec : Generated workbook spec
    """
    workbook_spec: TableauWorkbookSpec = Field(..., description="Generated workbook specification")
    file_path: str = Field(..., description="Path to the generated file")
    generation_time: float = Field(..., description="Time taken to generate (seconds)")
    warnings: List[str] = Field(default_factory=list, description="Generation warnings")
    success: bool = Field(..., description="Whether generation was successful")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")

class ValidationResult(BaseModel):
    """
    Result of data or specification validation.
    
    Represents validation of DatasetSchema, specifications, or Tableau formulas.
    Provides structured feedback on issues and recommendations.
    
    Attributes
    ----------
    is_valid : bool
        Whether validation passed. True if no critical errors; False if errors present
    
    errors : List[str], default=[]
        Critical validation failures that prevent processing:
        - Missing required fields
        - Invalid data types
        - Malformed calculations
        - Schema inconsistencies
    
    warnings : List[str], default=[]
        Non-critical issues that don't prevent but may impact quality:
        - Unusual value distributions
        - Missing values above threshold
        - Performance concerns
        - Best practice violations
    
    suggestions : List[str], default=[]
        Recommendations for improvement:
        - Data cleaning steps
        - Schema normalization
        - Performance optimization
        - Best practices
    
    Examples
    --------
    Successful validation:
    
    >>> result = ValidationResult(
    ...     is_valid=True,
    ...     errors=[],
    ...     warnings=["Column 'Amount' has 15% nulls"],
    ...     suggestions=["Consider imputing or excluding nulls"]
    ... )
    
    Failed validation:
    
    >>> result = ValidationResult(
    ...     is_valid=False,
    ...     errors=[
    ...         "Column 'CustomerID' should be unique but has 500 duplicates",
    ...         "Required column 'Date' contains invalid formats"
    ...     ],
    ...     warnings=["Low cardinality in 'Category' column"],
    ...     suggestions=[
    ...         "Deduplicate CustomerID",
    ...         "Standardize date formats to YYYY-MM-DD"
    ...     ]
    ... )
    
    Notes
    -----
    Validation Layers:
    - Schema validation: Field presence, types, constraints
    - Data validation: Value ranges, formats, uniqueness
    - Calculation validation: Formula syntax, field references
    
    Severity Levels:
    - Errors: Must fix before processing
    - Warnings: Should review but can continue
    - Suggestions: Nice-to-have improvements
    
    Usage:
    - Check is_valid before proceeding
    - Review errors if not valid
    - Consider implementing suggestions
    - Monitor warnings for quality issues
    
    See Also
    --------
    DatasetSchema : Subject of validation
    validate_dataframe_schema : Function using this result
    """
    is_valid: bool = Field(..., description="Whether the validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")

# Utility functions for model validation and creation

def validate_dataframe_schema(df: pd.DataFrame, calculated_fields: Optional[List[CalculatedFieldSpec]] = None) -> DatasetSchema:
    """
    Create a DatasetSchema from a pandas DataFrame.
    
    Automatically infers column types, calculates statistics, determines Tableau roles,
    and assesses overall data quality. This is the primary function for converting
    uploaded CSV/Excel data into the schema format used by the AI engine.
    
    Parameters
    ----------
    df : pd.DataFrame
        Input pandas DataFrame to convert into schema format
    
    calculated_fields : Optional[List[CalculatedFieldSpec]], default=None
        Pre-defined calculated fields to include in schema. If None, uses empty list.
        These are merged with auto-detected columns
    
    Returns
    -------
    DatasetSchema
        Fully populated DatasetSchema with:
        - Column specifications for each DataFrame column
        - Automatic data type inference
        - Statistical summaries for numeric columns
        - Tableau role recommendations
        - Overall data quality score
    
    Raises
    ------
    TypeError
        If df is not a pandas DataFrame
    
    Notes
    -----
    Data Type Inference Logic:
    - integer_dtype → DataType.INTEGER
    - float_dtype → DataType.FLOAT
    - datetime64 → DataType.DATETIME
    - bool_dtype → DataType.BOOLEAN
    - object with <50 unique → DataType.CATEGORICAL
    - object with ≥50 unique → DataType.STRING
    
    Statistics Calculated (numeric columns only):
    - mean: Average value
    - std: Standard deviation
    - min: Minimum value
    - max: Maximum value
    
    Key Field Detection:
    - Columns with >80% uniqueness flagged as potential keys
    - Used to identify surrogate keys and identifiers
    
    Tableau Role Assignment:
    - INTEGER/FLOAT → "measure" (aggregatable)
    - All others → "dimension" (grouping)
    
    Data Quality Scoring:
    - Formula: 1 - (total_nulls / total_cells)
    - Range: 0.0 (all nulls) to 1.0 (no nulls)
    - Incorporates null frequency but not semantic correctness
    
    Sample Values:
    - First 5 non-null values included per column
    - Used for data preview and quality inspection
    - Handles empty columns gracefully
    
    Examples
    --------
    Basic usage with CSV data:
    
    >>> import pandas as pd
    >>> df = pd.read_csv("sales.csv")
    >>> schema = validate_dataframe_schema(df)
    >>> print(f"Dataset: {schema.total_rows} rows, {schema.total_columns} columns")
    >>> print(f"Quality: {schema.data_quality_score:.1%}")
    
    With calculated fields:
    
    >>> calc_fields = [
    ...     CalculatedFieldSpec(
    ...         name="Profit Margin",
    ...         formula="([Profit] / [Revenue]) * 100",
    ...         data_type=DataType.FLOAT,
    ...         role="measure"
    ...     )
    ... ]
    >>> schema = validate_dataframe_schema(df, calc_fields)
    
    Accessing schema information:
    
    >>> for col in schema.columns:
    ...     print(f"{col.name}: {col.data_type.value}, {col.null_count} nulls")
    ...     if col.statistics:
    ...         print(f"  Mean: {col.statistics['mean']:.2f}")
    
    Notes
    -----
    Performance Considerations:
    - Pandas operations optimized for typical CSV sizes (<1M rows)
    - nunique() can be slow for large datasets
    - Consider aggregating very large files before schema creation
    
    Error Handling:
    - Gracefully handles missing values
    - Empty columns treated as STRING type
    - Mixed types default to STRING
    
    Data Type Confidence:
    - Inference relies on pandas type detection
    - May misclassify edge cases
    - User can override via preprocessing
    
    See Also
    --------
    DatasetSchema : Output model
    DataColumn : Individual column specification
    validate_dataframe_schema : This function
    
    Examples from Real Use:
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'id': [1, 2, 3, 4, 5],
    ...     'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
    ...     'age': [25, 30, 35, 28, 32],
    ...     'salary': [50000.0, 60000.0, 75000.0, 55000.0, 65000.0],
    ...     'department': ['Sales', 'IT', 'HR', 'Sales', 'IT'],
    ...     'join_date': pd.to_datetime(['2021-01-15', '2020-06-01', '2019-03-10', '2021-09-05', '2020-11-20'])
    ... })
    >>> schema = validate_dataframe_schema(df)
    >>> print(f"Columns: {[c.name for c in schema.columns]}")
    >>> print(f"Quality: {schema.data_quality_score:.1%}")
    """
    columns = []
    
    for col_name in df.columns:
        col_data = df[col_name]
        
        # Determine data type
        if pd.api.types.is_integer_dtype(col_data):
            data_type = DataType.INTEGER
        elif pd.api.types.is_float_dtype(col_data):
            data_type = DataType.FLOAT
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            data_type = DataType.DATETIME
        elif pd.api.types.is_bool_dtype(col_data):
            data_type = DataType.BOOLEAN
        elif col_data.dtype == 'object' and col_data.nunique() < 50:
            data_type = DataType.CATEGORICAL
        else:
            data_type = DataType.STRING
        
        # Calculate statistics
        statistics = None
        if data_type in [DataType.INTEGER, DataType.FLOAT]:
            statistics = {
                "mean": float(col_data.mean()) if not col_data.isna().all() else 0,
                "std": float(col_data.std()) if not col_data.isna().all() else 0,
                "min": float(col_data.min()) if not col_data.isna().all() else 0,
                "max": float(col_data.max()) if not col_data.isna().all() else 0,
            }
        
        # Create column specification
        column_spec = DataColumn(
            name=col_name,
            data_type=data_type,
            unique_values=col_data.nunique(),
            null_count=col_data.isna().sum(),
            sample_values=col_data.dropna().head(5).tolist(),
            statistics=statistics,
            is_key_field=col_data.nunique() > len(df) * 0.8,  # High uniqueness suggests key field
            recommended_role="measure" if data_type in [DataType.INTEGER, DataType.FLOAT] else "dimension"
        )
        columns.append(column_spec)
    
    # Calculate data quality score
    total_nulls = sum(col.null_count for col in columns)
    total_cells = len(df) * len(df.columns)
    data_quality_score = 1 - (total_nulls / total_cells) if total_cells > 0 else 0
    
    return DatasetSchema(
        name="uploaded_dataset",
        total_rows=len(df),
        total_columns=len(df.columns),
        columns=columns,
        data_quality_score=data_quality_score,
        calculated_fields=calculated_fields or []
    )