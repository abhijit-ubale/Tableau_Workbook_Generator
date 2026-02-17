"""
Data processing utilities for the Tableau Dashboard Generator.
Handles file uploads, data validation, and preprocessing.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json

from ..models.schemas import DatasetSchema, ValidationResult, validate_dataframe_schema
from .logger import get_logger

logger = get_logger(__name__)

class DataProcessor:
    """
    Handles data processing operations including file loading, validation, and preprocessing.
    """
    
    def __init__(self, config):
        self.config = config
        self.supported_formats = config.data_processing.supported_formats
        self.max_file_size_mb = config.data_processing.max_file_size_mb
        self.sample_rows = config.data_processing.sample_rows_for_analysis
        self.null_threshold = config.data_processing.null_threshold
    
    def load_data_file(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Load data from a file into a pandas DataFrame.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            Loaded DataFrame
            
        Raises:
            ValueError: If file format is not supported or file is too large
            Exception: If file cannot be loaded
        """
        file_path = Path(file_path)
        
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Validate file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise ValueError(f"File too large: {file_size_mb:.1f}MB (max: {self.max_file_size_mb}MB)")
        
        # Validate file format
        file_extension = file_path.suffix.lower().lstrip('.')
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        logger.info(f"Loading data file: {file_path} ({file_size_mb:.1f}MB)")
        
        try:
            if file_extension == 'csv':
                return self._load_csv(file_path)
            elif file_extension == 'xlsx':
                return self._load_excel(file_path)
            elif file_extension == 'json':
                return self._load_json(file_path)
            elif file_extension == 'parquet':
                return self._load_parquet(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            logger.error(f"Failed to load data file {file_path}: {e}")
            raise
    
    def _load_csv(self, file_path: Path) -> pd.DataFrame:
        """Load CSV file with automatic encoding detection"""
        encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                logger.info(f"Successfully loaded CSV with encoding: {encoding}")
                return df
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Unable to load CSV file with any supported encoding")
    
    def _load_excel(self, file_path: Path) -> pd.DataFrame:
        """Load Excel file"""
        # Try to load first sheet by default
        try:
            # Get sheet names to choose the best one
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Prefer first sheet or one with 'data' in name
            sheet_name = sheet_names[0]
            for name in sheet_names:
                if 'data' in name.lower():
                    sheet_name = name
                    break
            
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            logger.info(f"Loaded Excel sheet: {sheet_name}")
            return df
        except Exception as e:
            raise ValueError(f"Failed to load Excel file: {e}")
    
    def _load_json(self, file_path: Path) -> pd.DataFrame:
        """Load JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # If it's a dict, try to find the data array
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                elif 'records' in data:
                    df = pd.DataFrame(data['records'])
                else:
                    # Assume it's a single record
                    df = pd.DataFrame([data])
            else:
                raise ValueError("JSON structure not supported")
            
            return df
        except Exception as e:
            raise ValueError(f"Failed to load JSON file: {e}")
    
    def _load_parquet(self, file_path: Path) -> pd.DataFrame:
        """Load Parquet file"""
        try:
            return pd.read_parquet(file_path)
        except Exception as e:
            raise ValueError(f"Failed to load Parquet file: {e}")
    
    def validate_data(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate the loaded data for dashboard generation suitability.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Check minimum requirements
        if df.empty:
            errors.append("Dataset is empty")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        if len(df.columns) < 1:
            errors.append("Dataset has no columns")
        
        if len(df) < 2:
            warnings.append("Dataset has very few rows (less than 2)")
        
        # Check data quality
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        null_percentage = null_cells / total_cells if total_cells > 0 else 0
        
        if null_percentage > self.null_threshold:
            warnings.append(f"High percentage of missing values: {null_percentage:.1%}")
            suggestions.append("Consider data cleaning or imputation")
        
        # Check column types
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns
        datetime_columns = df.select_dtypes(include=['datetime64']).columns
        
        if len(numeric_columns) == 0 and len(datetime_columns) == 0:
            warnings.append("No numeric or datetime columns found - limited visualization options")
        
        # Check for potential issues
        for col in df.columns:
            unique_values = df[col].nunique()
            total_values = len(df)
            
            # Check for high cardinality categorical columns
            if df[col].dtype == 'object' and unique_values > 100:
                warnings.append(f"Column '{col}' has high cardinality ({unique_values} unique values)")
                suggestions.append(f"Consider grouping or filtering values in '{col}'")
            
            # Check for columns with all same values
            if unique_values == 1:
                warnings.append(f"Column '{col}' has only one unique value")
                suggestions.append(f"Consider removing constant column '{col}'")
            
            # Check for potential ID columns
            if unique_values == total_values and total_values > 1:
                suggestions.append(f"Column '{col}' appears to be an identifier - may not be useful for visualization")
        
        # Check column names
        problematic_names = []
        for col in df.columns:
            if not isinstance(col, str):
                problematic_names.append(col)
            elif col.strip() != col or ' ' in col:
                suggestions.append(f"Column '{col}' has spaces or leading/trailing whitespace")
        
        if problematic_names:
            warnings.append(f"Some column names are not strings: {problematic_names}")
        
        # Check for reasonable size for visualization
        if len(df) > 1000000:  # 1M rows
            warnings.append(f"Large dataset ({len(df):,} rows) may impact performance")
            suggestions.append("Consider data sampling or aggregation for better performance")
        
        if len(df.columns) > 50:
            warnings.append(f"Many columns ({len(df.columns)}) may make dashboard complex")
            suggestions.append("Consider focusing on key columns for better dashboard clarity")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess data for better analysis and visualization.
        
        NOTE: This method NO LONGER samples data. Sampling is now done separately 
        in streamlit_app.py to keep full data for workbook generation while using
        sampled data only for AI analysis.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Preprocessed DataFrame (full dataset, no sampling)
        """
        logger.info("Starting data preprocessing")
        
        df_processed = df.copy()
        
        # Clean column names
        df_processed.columns = [self._clean_column_name(col) for col in df_processed.columns]
        
        # Handle data types
        df_processed = self._optimize_data_types(df_processed)
        
        logger.info("Data preprocessing completed")
        return df_processed
    
    def _clean_column_name(self, col_name: str) -> str:
        """Clean column name for better compatibility"""
        if not isinstance(col_name, str):
            col_name = str(col_name)
        
        # Remove leading/trailing whitespace
        col_name = col_name.strip()
        
        # Replace spaces with underscores
        col_name = col_name.replace(' ', '_')
        
        # Remove special characters except underscore
        col_name = ''.join(c for c in col_name if c.isalnum() or c == '_')
        
        # Ensure it doesn't start with a number
        if col_name and col_name[0].isdigit():
            col_name = 'col_' + col_name
        
        # Ensure it's not empty
        if not col_name:
            col_name = 'unnamed_column'
        
        return col_name
    
    def _optimize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize data types for better performance and analysis.

        Handles common real-world formatting:
        - Currency:   $1,234.56  → 1234.56
        - Percentage: 45.2%      → 45.2
        - Accounting: (100.0)    → -100.0
        - Comma-sep:  1,234      → 1234
        """
        import re

        def _try_numeric(series: pd.Series):
            """Return numeric series if ≥80% of non-null values convert, else None."""
            non_null = series.dropna()
            if len(non_null) == 0:
                return None
            result = pd.to_numeric(non_null, errors="coerce")
            if result.notna().sum() >= len(non_null) * 0.8:
                return pd.to_numeric(series, errors="coerce")
            return None

        def _strip_numeric_formatting(s: pd.Series) -> pd.Series:
            """Strip currency / percentage / accounting symbols from a string series."""
            def _clean(v):
                v = str(v).strip()
                neg = v.startswith("(") and v.endswith(")")
                v = re.sub(r"[\$,\s%]", "", v).strip("()")
                return ("-" + v) if neg else v
            return s.apply(_clean)

        for col in df.columns:
            col_data = df[col]

            if col_data.isnull().all():
                continue

            if col_data.dtype == "object":
                # 1. Try datetime
                if self._looks_like_datetime(col_data):
                    try:
                        df[col] = pd.to_datetime(col_data, infer_datetime_format=True)
                        logger.debug(f"Converted '{col}' to datetime")
                        continue
                    except Exception:
                        pass

                # 2. Try raw numeric (numbers stored as plain strings)
                converted = _try_numeric(col_data)
                if converted is not None:
                    df[col] = converted
                    logger.debug(f"Converted '{col}' to numeric")
                    continue

                # 3. Try after stripping currency / percentage / comma formatting
                stripped = _strip_numeric_formatting(col_data)
                converted = _try_numeric(stripped)
                if converted is not None:
                    df[col] = converted
                    logger.debug(f"Converted '{col}' to numeric (after symbol stripping)")
                    continue

                # 4. Low-cardinality → category
                if col_data.nunique() < 50:
                    df[col] = col_data.astype("category")
                    logger.debug(f"Converted '{col}' to category")

        return df
    
    def _looks_like_datetime(self, series: pd.Series) -> bool:
        """Check if a series looks like it contains datetime values"""
        if series.dtype != 'object':
            return False
        
        # Sample some non-null values
        sample = series.dropna().head(10)
        
        if len(sample) == 0:
            return False
        
        datetime_indicators = [
            '/', '-', ':', 'T', 'Z',  # Common datetime separators
            '2020', '2021', '2022', '2023', '2024'  # Recent years
        ]
        
        string_values = [str(val) for val in sample]
        
        # Check if any values contain datetime indicators
        for val in string_values:
            if any(indicator in val for indicator in datetime_indicators):
                return True
        
        return False
    
    def create_dataset_schema(self, df: pd.DataFrame, name: str = "dataset") -> DatasetSchema:
        """
        Create a dataset schema from a DataFrame.
        
        Args:
            df: Input DataFrame
            name: Dataset name
            
        Returns:
            DatasetSchema object
        """
        return validate_dataframe_schema(df)
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the dataset.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dictionary with data summary
        """
        summary = {
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": {
                "numeric": list(df.select_dtypes(include=[np.number]).columns),
                "categorical": list(df.select_dtypes(include=['object', 'category']).columns),
                "datetime": list(df.select_dtypes(include=['datetime64']).columns),
                "boolean": list(df.select_dtypes(include=['bool']).columns)
            },
            "missing_data": {
                "total_nulls": int(df.isnull().sum().sum()),
                "null_percentage": float(df.isnull().sum().sum() / (len(df) * len(df.columns))),
                "columns_with_nulls": df.columns[df.isnull().any()].tolist()
            },
            "memory_usage": {
                "total_mb": float(df.memory_usage(deep=True).sum() / 1024 / 1024)
            }
        }
        
        # Add column-specific info
        summary["column_details"] = {}
        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "unique_values": int(df[col].nunique()),
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": float(df[col].isnull().sum() / len(df))
            }
            
            if df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                col_info["statistics"] = {
                    "mean": float(df[col].mean()) if not df[col].isna().all() else None,
                    "median": float(df[col].median()) if not df[col].isna().all() else None,
                    "std": float(df[col].std()) if not df[col].isna().all() else None,
                    "min": float(df[col].min()) if not df[col].isna().all() else None,
                    "max": float(df[col].max()) if not df[col].isna().all() else None
                }
            
            summary["column_details"][col] = col_info
        
        return summary