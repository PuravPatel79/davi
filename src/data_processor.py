import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional

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

    def filter_data(self, filters: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Filter dataframe based on conditions specified in a structured dictionary.

        Args:
            filters: A dictionary where keys are column names and values are dictionaries
                     specifying the 'operator' and 'value'.
                     Example: {
                         'Age': {'operator': '>', 'value': 30},
                         'City': {'operator': '==', 'value': 'New York'},
                         'Status': {'operator': 'isin', 'value': ['Active', 'Pending']}
                     }
                     Supported operators: '==', '!=', '>', '<', '>=', '<=', 'isin'
        """
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")

        filtered_df = self.dataframe.copy()
        for column, condition in filters.items():
            if column not in filtered_df.columns:
                print(f"Warning: Filter column '{column}' not found in dataframe. Skipping filter.")
                continue

            operator = condition.get('operator')
            value = condition.get('value')

            if operator is None or value is None:
                print(f"Warning: Invalid filter condition for column '{column}'. Missing 'operator' or 'value'. Skipping filter.")
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

    def aggregate_data(self, group_by_columns: List[str], agg_specs: Dict[str, str]) -> pd.DataFrame:
        """Aggregate dataframe by grouping and applying aggregation functions.

        Args:
            group_by_columns: A list of column names to group by.
            agg_specs: A dictionary where keys are the names for the aggregated columns
                       and values are the aggregation functions to apply (e.g., 'sum', 'mean', 'count', 'size').
                       Example: {'OrderQuantity': 'sum', 'OrderCount': 'size'}

        Returns:
            A pandas DataFrame with the aggregated results.
        """
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")

        # Validate group_by columns
        for col in group_by_columns:
            if col not in self.dataframe.columns:
                raise ValueError(f"Group by column '{col}' not found in dataframe.")

        try:
            grouped_data = self.dataframe.groupby(group_by_columns)
            
            # Prepare aggregation dictionary for pandas
            pandas_agg_dict = {}
            for new_col_name, agg_func in agg_specs.items():
                if agg_func.lower() != 'size':
                    original_col = new_col_name # Default assumption
                    if original_col not in self.dataframe.columns:
                         if new_col_name.lower().endswith(agg_func.lower()):
                             potential_col = new_col_name[:-len(agg_func)]
                             if potential_col in self.dataframe.columns:
                                 original_col = potential_col
                             else:
                                 raise ValueError(f"Could not determine original column for aggregation '{agg_func}' on '{new_col_name}'. Column '{original_col}' not found.")
                         else:
                             raise ValueError(f"Could not determine original column for aggregation '{agg_func}' on '{new_col_name}'. Column '{original_col}' not found.")
                    
                    if original_col not in self.dataframe.columns:
                         raise ValueError(f"Column '{original_col}' specified for aggregation '{agg_func}' not found.")
                         
                    pandas_agg_dict[new_col_name] = pd.NamedAgg(column=original_col, aggfunc=agg_func.lower())
                else:
                    pass # Handle size later
            
            if pandas_agg_dict:
                aggregated_df = grouped_data.agg(**pandas_agg_dict).reset_index()
            else:
                # If only size was requested, or no other aggregations, get unique group keys
                aggregated_df = grouped_data.first().reset_index()[group_by_columns] 

            size_specs = {name: func for name, func in agg_specs.items() if func.lower() == 'size'} 
            if size_specs:
                size_df = grouped_data.size().reset_index(name=list(size_specs.keys())[0])
                if len(size_specs) > 1:
                    print("Warning: Multiple 'size' aggregations requested. Using name from first one.")
                
                # Merge size results with other aggregations if they exist
                # Check if aggregated_df only contains group_by columns (case where only size was requested initially)
                if set(aggregated_df.columns) == set(group_by_columns) and not pandas_agg_dict:
                     aggregated_df = size_df # Replace with size results
                elif not aggregated_df.empty:
                     aggregated_df = pd.merge(aggregated_df, size_df, on=group_by_columns, how='left')
                else: # Should not happen if group_by_columns is valid
                     aggregated_df = size_df

            return aggregated_df

        except Exception as e:
            print(f"Error during aggregation: {str(e)}")
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