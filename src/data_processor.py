import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional, Union

class DataProcessor:
    def __init__(self):
        self.dataframe = None
        self.metadata = {}

    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load data from CSV or Excel file or URL"""
        try:
            # Handle URLs
            if file_path.startswith('http://') or file_path.startswith('https://'):
                print(f"Loading data from URL: {file_path}")
                # For GitHub raw content or similar direct links
                if file_path.endswith('.csv'):
                    self.dataframe = pd.read_csv(file_path)
                    print("Successfully loaded CSV from URL")
                elif file_path.endswith(('.xls', '.xlsx')):
                    self.dataframe = pd.read_excel(file_path)
                    print("Successfully loaded Excel from URL")
                else:
                    # Try to load as CSV anyway with different parsers
                    try:
                        self.dataframe = pd.read_csv(file_path)
                        print("Successfully loaded CSV from URL")
                    except pd.errors.ParserError:
                        try:
                            self.dataframe = pd.read_csv(file_path, sep=';')
                            print("Successfully loaded CSV with semicolon delimiter from URL")
                        except pd.errors.ParserError:
                            try:
                                self.dataframe = pd.read_csv(file_path, sep='\t')
                                print("Successfully loaded CSV with tab delimiter from URL")
                            except pd.errors.ParserError:
                                try:
                                    self.dataframe = pd.read_csv(file_path, engine='python')
                                    print("Successfully loaded CSV with python engine from URL")
                                except Exception as url_csv_err:
                                    raise ValueError(f"Could not parse URL content as CSV/Excel: {file_path}") from url_csv_err

            # Handle local files
            elif os.path.exists(file_path):
                if file_path.endswith('.csv'):
                    loaded = False
                    try:
                        self.dataframe = pd.read_csv(file_path)
                        loaded = True
                    except pd.errors.ParserError:
                        print("ParserError with default CSV settings, trying semicolon delimiter...")
                        try:
                            self.dataframe = pd.read_csv(file_path, sep=';')
                            loaded = True
                        except pd.errors.ParserError:
                            print("ParserError with semicolon delimiter, trying tab delimiter...")
                            try:
                                self.dataframe = pd.read_csv(file_path, sep='\t')
                                loaded = True
                            except pd.errors.ParserError:
                                print("ParserError with tab delimiter, trying python engine...")
                                try:
                                    self.dataframe = pd.read_csv(file_path, engine='python')
                                    loaded = True
                                except Exception as final_e: # Catch any final error
                                    print(f"Failed to load CSV with python engine: {final_e}")
                                    raise ValueError(f"Could not parse CSV file {file_path} with any engine.") from final_e
                    
                    if loaded:
                        print(f"Successfully loaded local CSV file: {file_path}")
                    else: # This else should ideally not be reached if the last try/except raises
                         raise ValueError(f"Failed to load CSV file: {file_path}")
                         
                elif file_path.endswith(('.xls', '.xlsx')):
                    self.dataframe = pd.read_excel(file_path)
                    print(f"Successfully loaded local Excel file: {file_path}")
                else:
                    raise ValueError("Unsupported file format. Use CSV or Excel files.")
            else:
                raise ValueError(f"File not found: {file_path}")

            self._extract_metadata()
            return self.dataframe

        except Exception as e:
            print(f"Error loading data: {str(e)}")
            raise

    def _extract_metadata(self):
        """Extract metadata about the dataframe"""
        if self.dataframe is not None:
            # Basic metadata
            self.metadata['columns'] = list(self.dataframe.columns)
            self.metadata['shape'] = self.dataframe.shape
            self.metadata['dtypes'] = {col: str(dtype) for col, dtype in self.dataframe.dtypes.items()}

            # Statistical metadata
            numeric_columns = self.dataframe.select_dtypes(include=[np.number]).columns
            self.metadata['numeric_columns'] = list(numeric_columns)

            categorical_columns = self.dataframe.select_dtypes(include=['object', 'category']).columns
            self.metadata['categorical_columns'] = list(categorical_columns)

            # Sample statistics
            if len(numeric_columns) > 0:
                self.metadata['statistics'] = self.dataframe[numeric_columns].describe().to_dict()

    def get_column_info(self) -> str:
        """Get information about columns for the agent"""
        if self.dataframe is None:
            return "No data loaded yet."

        info = []
        for col in self.dataframe.columns:
            dtype = self.metadata['dtypes'][col]
            if col in self.metadata.get('numeric_columns', []):
                min_val = self.dataframe[col].min()
                max_val = self.dataframe[col].max()
                info.append(f"{col} (numeric, {dtype}): range {min_val} to {max_val}")
            else:
                unique_vals = self.dataframe[col].nunique()
                info.append(f"{col} (categorical, {dtype}): {unique_vals} unique values")

        return "\n".join(info)

    def filter_data(self, filters: List[Dict[str, Any]]) -> pd.DataFrame:
        """Filter dataframe based on conditions specified in a list of dictionaries.

        Args:
            filters: A list of dictionaries, each specifying a filter condition.
                     Example: [
                         {'column': 'Age', 'operator': '>', 'value': 30},
                         {'column': 'City', 'operator': '==', 'value': 'New York'},
                         {'column': 'Status', 'operator': 'isin', 'value': ['Active', 'Pending']}
                     ]
                     Supported operators: '==', '!=', '>', '<', '>=', '<=', 'isin'
        """
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")

        filtered_df = self.dataframe.copy()
        for condition in filters:
            column = condition.get('column')
            operator = condition.get('operator')
            value = condition.get('value')

            if not column or not operator or value is None:
                print(f"Warning: Invalid filter condition: {condition}. Missing 'column', 'operator', or 'value'. Skipping filter.")
                continue
                
            if column not in filtered_df.columns:
                print(f"Warning: Filter column '{column}' not found in dataframe. Skipping filter.")
                continue

            try:
                col_series = filtered_df[column]
                # Attempt type conversion for numeric comparisons if column is object type
                if operator in ['>', '<', '>=', '<='] and col_series.dtype == 'object':
                    try:
                        col_series = pd.to_numeric(col_series, errors='coerce')
                        value = pd.to_numeric(value)
                        # Drop rows where conversion failed if necessary
                        # filtered_df = filtered_df.dropna(subset=[column])
                    except (ValueError, TypeError):
                        print(f"Warning: Could not convert column '{column}' or value '{value}' to numeric for comparison. Skipping filter.")
                        continue

                if operator == '==':
                    filtered_df = filtered_df[col_series == value]
                elif operator == '!=':
                    filtered_df = filtered_df[col_series != value]
                elif operator == '>':
                    filtered_df = filtered_df[col_series > value]
                elif operator == '<':
                    filtered_df = filtered_df[col_series < value]
                elif operator == '>=':
                    filtered_df = filtered_df[col_series >= value]
                elif operator == '<=':
                    filtered_df = filtered_df[col_series <= value]
                elif operator == 'isin':
                    if isinstance(value, list):
                        filtered_df = filtered_df[col_series.isin(value)]
                    else:
                        print(f"Warning: 'isin' operator requires a list value for column '{column}'. Skipping filter.")
                else:
                    print(f"Warning: Unsupported operator '{operator}' for column '{column}'. Skipping filter.")
            except Exception as e:
                print(f"Error applying filter on column '{column}' with operator '{operator}' and value '{value}': {str(e)}")
                # Optionally skip this filter or raise the error
                continue

        return filtered_df

    def aggregate_data(self, group_by_columns: List[str], agg_specs: Dict[str, Union[str, Dict[str, str]]], df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Aggregate dataframe by grouping and applying aggregation functions.

        Args:
            group_by_columns: A list of column names to group by.
            agg_specs: A dictionary where keys are the output column names.
                       Values are either the string 'size' or a dictionary like 
                       {'source': 'SourceColumnName', 'func': 'sum|mean|count|...'}.
                       Example: {
                           'TotalQuantity': {'source': 'OrderQuantity', 'func': 'sum'},
                           'OrderCount': 'size'
                       }
            df: Optional dataframe to perform aggregation on. If None, uses self.dataframe.

        Returns:
            A pandas DataFrame with the aggregated results.
        """
        dataframe_to_agg = df if df is not None else self.dataframe # Decide which df to use

        if dataframe_to_agg is None: # Check the one we intend to use
            raise ValueError("No data loaded yet. Either load data first or provide a dataframe.")

        # Validate group_by columns against the dataframe being used
        for col in group_by_columns:
            if col not in dataframe_to_agg.columns:
                raise ValueError(f"Group by column '{col}' not found in the dataframe being aggregated.")

        try:
            grouped_data = dataframe_to_agg.groupby(group_by_columns)
            
            # Prepare aggregation dictionary for pandas
            pandas_agg_dict = {}
            size_specs = {} # Separate dict for size

            for output_col, spec in agg_specs.items():
                if isinstance(spec, str) and spec.lower() == 'size':
                    # Handle size aggregation separately
                    size_specs[output_col] = 'size'
                elif isinstance(spec, dict):
                    source_col = spec.get('source')
                    agg_func = spec.get('func')
                    
                    if not source_col or not agg_func:
                        print(f"Warning: Invalid aggregation spec for '{output_col}'. Missing 'source' or 'func'. Skipping.")
                        continue
                        
                    agg_func_lower = agg_func.lower()
                    if agg_func_lower == 'size': # Allow 'size' in dict format too
                         size_specs[output_col] = 'size'
                         continue

                    # Validate source column exists
                    if source_col not in dataframe_to_agg.columns:
                        # This is where LLM self-correction or user clarification would be triggered in the agent
                        raise ValueError(f"Source column '{source_col}' specified for aggregation '{agg_func_lower}' on output '{output_col}' not found in dataframe. Available columns: {list(dataframe_to_agg.columns)}")
                         
                    pandas_agg_dict[output_col] = pd.NamedAgg(column=source_col, aggfunc=agg_func_lower)
                else:
                    print(f"Warning: Invalid aggregation spec format for '{output_col}'. Skipping.")
            
            # Perform non-size aggregations
            if pandas_agg_dict:
                aggregated_df = grouped_data.agg(**pandas_agg_dict).reset_index()
            else:
                # If only size was requested, or no other aggregations, get unique group keys
                if not dataframe_to_agg.empty:
                    # Use .first() to get group keys without needing an aggregation column
                    # Need to handle potential empty groups if filtering resulted in empty groups
                    try:
                        aggregated_df = grouped_data.first().reset_index()[group_by_columns]
                    except IndexError: # Happens if grouped_data is empty
                        aggregated_df = pd.DataFrame(columns=group_by_columns)
                else:
                    aggregated_df = pd.DataFrame(columns=group_by_columns) # Empty df with group columns

            # Handle size aggregation
            if size_specs:
                # Use the name from the first size spec found
                size_col_name = list(size_specs.keys())[0]
                if len(size_specs) > 1:
                    print(f"Warning: Multiple 'size' aggregations requested. Using name '{size_col_name}' from the first one.")
                
                size_df = grouped_data.size().reset_index(name=size_col_name)
                
                # Merge size results with other aggregations if they exist
                if set(aggregated_df.columns) == set(group_by_columns) and not pandas_agg_dict:
                     aggregated_df = size_df # Replace with size results if only size was requested
                elif not aggregated_df.empty:
                     # Check if size_df is empty (can happen if dataframe_to_agg was empty)
                     if not size_df.empty:
                         aggregated_df = pd.merge(aggregated_df, size_df, on=group_by_columns, how='left')
                     # else: aggregated_df already contains the group keys, just no size data
                elif not size_df.empty: # Handle case where only size was requested and df wasn't empty
                     aggregated_df = size_df
                # If both aggregated_df and size_df are empty, aggregated_df remains empty df with group columns

            return aggregated_df

        except Exception as e:
            print(f"Error during aggregation: {str(e)}")
            # Add traceback for detailed debugging if needed
            # import traceback
            # traceback.print_exc()
            raise

    def preprocess_data(self, steps: List[Dict[str, str]]) -> None:
        """Apply preprocessing steps to the dataframe, modifying it in place.

        Args:
            steps: A list of dictionaries, each specifying a preprocessing step.
                   Example: [
                       {'operation': 'extract_month', 'column': 'OrderDate', 'new_column': 'OrderMonth'},
                       {'operation': 'extract_year', 'column': 'OrderDate', 'new_column': 'OrderYear'}
                   ]
                   Supported operations: 'extract_month', 'extract_year', 'extract_day', 'extract_dayofweek'
        """
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")

        for step in steps:
            operation = step.get('operation')
            column = step.get('column')
            new_column = step.get('new_column')

            if not all([operation, column, new_column]):
                print(f"Warning: Invalid preprocessing step: {step}. Missing required keys. Skipping.")
                continue

            if column not in self.dataframe.columns:
                print(f"Warning: Preprocessing source column '{column}' not found. Skipping step: {step}.")
                continue
            
            if new_column in self.dataframe.columns:
                print(f"Warning: Preprocessing target column '{new_column}' already exists. It will be overwritten.")

            try:
                # Ensure the source column is in datetime format
                date_series = pd.to_datetime(self.dataframe[column], errors='coerce')
                
                # Check for conversion errors
                if date_series.isnull().all():
                    print(f"Warning: Could not convert column '{column}' to datetime. Skipping step: {step}.")
                    continue
                elif date_series.isnull().any():
                    print(f"Warning: Some values in column '{column}' could not be converted to datetime.")

                # Apply the operation
                if operation == 'extract_month':
                    self.dataframe[new_column] = date_series.dt.month
                elif operation == 'extract_year':
                    self.dataframe[new_column] = date_series.dt.year
                elif operation == 'extract_day':
                    self.dataframe[new_column] = date_series.dt.day
                elif operation == 'extract_dayofweek':
                    self.dataframe[new_column] = date_series.dt.dayofweek # Monday=0, Sunday=6
                # Add more date operations as needed (e.g., week, quarter)
                else:
                    print(f"Warning: Unsupported preprocessing operation '{operation}'. Skipping step: {step}.")
                    continue
                
                print(f"Successfully applied preprocessing step: {step}")
                # Update metadata after adding the column
                self._extract_metadata()

            except Exception as e:
                print(f"Error during preprocessing step {step}: {str(e)}")
                # Optionally skip this step or raise the error
                continue

    def get_data(self) -> pd.DataFrame:
        """Get the current dataframe"""
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")
        return self.dataframe