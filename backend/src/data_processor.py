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
            if file_path.startswith("http://") or file_path.startswith("https://"):
                print(f"Loading data from URL: {file_path}")
                if file_path.endswith(".csv"):
                    self.dataframe = pd.read_csv(file_path)
                    print("Successfully loaded CSV from URL")
                elif file_path.endswith((".xls", ".xlsx")):
                    self.dataframe = pd.read_excel(file_path)
                    print("Successfully loaded Excel from URL")
                else:
                    try:
                        self.dataframe = pd.read_csv(file_path)
                        print("Successfully loaded CSV from URL")
                    except pd.errors.ParserError:
                        try:
                            self.dataframe = pd.read_csv(file_path, sep=";")
                            print("Successfully loaded CSV with semicolon delimiter from URL")
                        except pd.errors.ParserError:
                            try:
                                self.dataframe = pd.read_csv(file_path, sep="\t")
                                print("Successfully loaded CSV with tab delimiter from URL")
                            except pd.errors.ParserError:
                                try:
                                    self.dataframe = pd.read_csv(file_path, engine="python")
                                    print("Successfully loaded CSV with python engine from URL")
                                except Exception as url_csv_err:
                                    raise ValueError(f"Could not parse URL content as CSV/Excel: {file_path}") from url_csv_err
            elif os.path.exists(file_path):
                if file_path.endswith(".csv"):
                    loaded = False
                    try:
                        self.dataframe = pd.read_csv(file_path)
                        loaded = True
                    except pd.errors.ParserError:
                        print("ParserError with default CSV settings, trying semicolon delimiter...")
                        try:
                            self.dataframe = pd.read_csv(file_path, sep=";")
                            loaded = True
                        except pd.errors.ParserError:
                            print("ParserError with semicolon delimiter, trying tab delimiter...")
                            try:
                                self.dataframe = pd.read_csv(file_path, sep="\t")
                                loaded = True
                            except pd.errors.ParserError:
                                print("ParserError with tab delimiter, trying python engine...")
                                try:
                                    self.dataframe = pd.read_csv(file_path, engine="python")
                                    loaded = True
                                except Exception as final_e:
                                    print(f"Failed to load CSV with python engine: {final_e}")
                                    raise ValueError(f"Could not parse CSV file {file_path} with any engine.") from final_e
                    if loaded:
                        print(f"Successfully loaded local CSV file: {file_path}")
                    else:
                        raise ValueError(f"Failed to load CSV file: {file_path}")
                elif file_path.endswith((".xls", ".xlsx")):
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
        if self.dataframe is not None:
            self.metadata["columns"] = list(self.dataframe.columns)
            self.metadata["shape"] = self.dataframe.shape
            self.metadata["dtypes"] = {col: str(dtype) for col, dtype in self.dataframe.dtypes.items()}
            numeric_columns = self.dataframe.select_dtypes(include=[np.number]).columns
            self.metadata["numeric_columns"] = list(numeric_columns)
            categorical_columns = self.dataframe.select_dtypes(include=["object", "category"]).columns
            self.metadata["categorical_columns"] = list(categorical_columns)
            if len(numeric_columns) > 0:
                self.metadata["statistics"] = self.dataframe[numeric_columns].describe().to_dict()

    def get_column_info(self) -> str:
        if self.dataframe is None:
            return "No data loaded yet."
        info = []
        for col in self.dataframe.columns:
            dtype = self.metadata["dtypes"][col]
            if col in self.metadata.get("numeric_columns", []):
                min_val = self.dataframe[col].min()
                max_val = self.dataframe[col].max()
                info.append(f"{col} (numeric, {dtype}): range {min_val} to {max_val}")
            else:
                unique_vals = self.dataframe[col].nunique()
                info.append(f"{col} (categorical, {dtype}): {unique_vals} unique values")
        return "\n".join(info)

    def filter_data(self, filters: List[Dict[str, Any]], df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Filter dataframe based on conditions specified in a list of dictionaries.

        Args:
            filters: A list of dictionaries, each specifying a filter condition.
            df: Optional dataframe to perform filtering on. If None, uses self.dataframe.
        """
        dataframe_to_filter = df if df is not None else self.dataframe

        if dataframe_to_filter is None:
            raise ValueError("No data available to filter. Load data first or provide a DataFrame.")

        filtered_df = dataframe_to_filter.copy()
        for condition in filters:
            if not isinstance(condition, dict):
                print(f"Warning: Invalid filter condition format: {condition}. Expected a dictionary. Skipping filter.")
                continue
            column = condition.get("column")
            operator = condition.get("operator")
            value = condition.get("value")

            if not column or not operator or value is None:
                print(f"Warning: Invalid filter condition: {condition}. Missing 'column', 'operator', or 'value'. Skipping filter.")
                continue
                
            if column not in filtered_df.columns:
                print(f"Warning: Filter column '{column}' not found in dataframe. Skipping filter.")
                continue

            try:
                col_series = filtered_df[column]
                if operator in [">", "<", ">=", "<="] and col_series.dtype == "object":
                    try:
                        col_series = pd.to_numeric(col_series, errors="coerce")
                        value = pd.to_numeric(value)
                    except (ValueError, TypeError):
                        print(f"Warning: Could not convert column '{column}' or value '{value}' to numeric for comparison. Skipping filter.")
                        continue

                if operator == "==":
                    filtered_df = filtered_df[col_series == value]
                elif operator == "!=":
                    filtered_df = filtered_df[col_series != value]
                elif operator == ">":
                    filtered_df = filtered_df[col_series > value]
                elif operator == "<":
                    filtered_df = filtered_df[col_series < value]
                elif operator == ">=":
                    filtered_df = filtered_df[col_series >= value]
                elif operator == "<=":
                    filtered_df = filtered_df[col_series <= value]
                elif operator == "isin":
                    if isinstance(value, list):
                        filtered_df = filtered_df[col_series.isin(value)]
                    else:
                        print(f"Warning: 'isin' operator requires a list value for column '{column}'. Skipping filter.")
                # Add support for 'in' operator (same as 'isin')
                elif operator == "in":
                    if isinstance(value, list):
                        filtered_df = filtered_df[col_series.isin(value)]
                    else:
                        print(f"Warning: 'in' operator requires a list value for column '{column}'. Skipping filter.")
                # Add support for 'not in' operator
                elif operator == "not in":
                    if isinstance(value, list):
                        filtered_df = filtered_df[~col_series.isin(value)]
                    else:
                        print(f"Warning: 'not in' operator requires a list value for column '{column}'. Skipping filter.")
                else:
                    print(f"Warning: Unsupported operator '{operator}' for column '{column}'. Skipping filter.")
            except Exception as e:
                print(f"Error applying filter on column '{column}' with operator '{operator}' and value '{value}': {str(e)}")
                continue
        
        print(f"Shape after filtering: {filtered_df.shape}")
        return filtered_df

    def aggregate_data(self, group_by_columns: List[str], agg_specs: Dict[str, tuple], df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Aggregate data based on group_by columns and aggregation specifications.
        
        This method supports both grouped aggregations and overall totals (when group_by_columns is empty).
        
        Args:
            group_by_columns: List of column names to group by (can be empty for totals)
            agg_specs: Dictionary mapping output column names to (source_column, agg_function) tuples
            df: Optional dataframe to perform aggregation on. If None, uses self.dataframe
            
        Returns:
            Aggregated DataFrame
        """
        dataframe_to_agg = df if df is not None else self.dataframe
        
        if dataframe_to_agg is None:
            raise ValueError("No data loaded yet. Either load data first or provide a dataframe.")
        
        # Handle empty group_by_columns
        if not group_by_columns:
            result_df = pd.DataFrame()
            for output_col, (source_col, agg_func) in agg_specs.items():
                if source_col not in dataframe_to_agg.columns:
                    raise ValueError(f"Source column '{source_col}' not found in dataframe.")
                    
                agg_func_lower = agg_func.lower()
                if agg_func_lower == 'sum':
                    result_df[output_col] = [dataframe_to_agg[source_col].sum()]
                elif agg_func_lower == 'mean':
                    result_df[output_col] = [dataframe_to_agg[source_col].mean()]
                elif agg_func_lower == 'count':
                    result_df[output_col] = [dataframe_to_agg[source_col].count()]
                elif agg_func_lower == 'min':
                    result_df[output_col] = [dataframe_to_agg[source_col].min()]
                elif agg_func_lower == 'max':
                    result_df[output_col] = [dataframe_to_agg[source_col].max()]
                elif agg_func_lower == 'size':
                    result_df[output_col] = [len(dataframe_to_agg)]
                else:
                    raise ValueError(f"Unsupported aggregation function: {agg_func}")
            return result_df
        
        # Process grouped aggregations
        for col in group_by_columns:
            if col not in dataframe_to_agg.columns:
                raise ValueError(f"Group by column '{col}' not found in the dataframe being aggregated.")
                
        try:
            grouped_data = dataframe_to_agg.groupby(group_by_columns)
            pandas_agg_dict = {}
            size_specs = {}
            
            for output_col, (source_col, agg_func) in agg_specs.items():
                agg_func_lower = agg_func.lower()
                if agg_func_lower == 'size':
                    size_specs[output_col] = 'size'
                else:
                    if source_col not in dataframe_to_agg.columns:
                        raise ValueError(f"Source column '{source_col}' not found in dataframe.")
                    pandas_agg_dict[output_col] = pd.NamedAgg(column=source_col, aggfunc=agg_func_lower)
                    
            if pandas_agg_dict:
                aggregated_df = grouped_data.agg(**pandas_agg_dict).reset_index()
            else:
                if not dataframe_to_agg.empty:
                    aggregated_df = grouped_data.first().reset_index()[group_by_columns]
                else:
                    aggregated_df = pd.DataFrame(columns=group_by_columns)
                    
            if size_specs:
                size_col_name = list(size_specs.keys())[0]
                if len(size_specs) > 1:
                    print(f"Warning: Multiple 'size' aggregations requested. Using name '{size_col_name}' from the first one.")
                size_df = grouped_data.size().reset_index(name=size_col_name)
                if set(aggregated_df.columns) == set(group_by_columns) and not pandas_agg_dict:
                    aggregated_df = size_df
                elif not aggregated_df.empty:
                    if not size_df.empty:
                        aggregated_df = pd.merge(aggregated_df, size_df, on=group_by_columns, how='left')
                elif not size_df.empty:
                    aggregated_df = size_df
            return aggregated_df
        except Exception as e:
            print(f"Error during aggregation: {str(e)}")
            raise

    def preprocess_data(self, steps: List[Dict[str, str]], df_input: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Apply preprocessing steps to the dataframe. 
            If df_input is provided, it operates on that and returns the modified df.
            Otherwise, it modifies self.dataframe in place and returns it.
        """
        df_to_process = df_input.copy() if df_input is not None else self.dataframe

        if df_to_process is None:
            print("Warning: No data loaded or provided. Cannot preprocess.")
            return None # Or raise error

        for step in steps:
            operation = step.get('operation')
            column = step.get('column')
            new_column = step.get('new_column')
            value = step.get('value')
            old_name = step.get('old_name')
            new_name = step.get('new_name')

            if not operation:
                print(f"Warning: Preprocessing step missing 'operation'. Skipping: {step}")
                continue
            if column and column not in df_to_process.columns and operation not in ['rename_column']:
                print(f"Warning: Column '{column}' not found for operation '{operation}'. Skipping: {step}")
                continue
            if operation == 'rename_column' and (not old_name or old_name not in df_to_process.columns or not new_name):
                print(f"Warning: Invalid 'rename_column' spec. 'old_name' must exist and 'new_name' must be provided. Skipping: {step}")
                continue
            try:
                if operation == 'extract_month':
                    if not new_column: print(f"Warning: 'new_column' not specified for 'extract_month'. Skipping: {step}"); continue
                    df_to_process[new_column] = pd.to_datetime(df_to_process[column]).dt.month
                elif operation == 'extract_year':
                    if not new_column: print(f"Warning: 'new_column' not specified for 'extract_year'. Skipping: {step}"); continue
                    df_to_process[new_column] = pd.to_datetime(df_to_process[column]).dt.year
                elif operation == 'extract_day':
                    if not new_column: print(f"Warning: 'new_column' not specified for 'extract_day'. Skipping: {step}"); continue
                    df_to_process[new_column] = pd.to_datetime(df_to_process[column]).dt.day
                elif operation == 'extract_dayofweek':
                    if not new_column: print(f"Warning: 'new_column' not specified for 'extract_dayofweek'. Skipping: {step}"); continue
                    df_to_process[new_column] = pd.to_datetime(df_to_process[column]).dt.dayofweek
                elif operation == 'fill_na':
                    if value is None: print(f"Warning: 'value' not specified for 'fill_na'. Skipping: {step}"); continue
                    df_to_process[column].fillna(value, inplace=True)
                elif operation == 'drop_na':
                    df_to_process.dropna(subset=[column], inplace=True)
                elif operation == 'rename_column':
                    df_to_process.rename(columns={old_name: new_name}, inplace=True)
                    if df_input is None: # Only update metadata if modifying self.dataframe
                        if old_name in self.metadata.get('columns', []):
                            self.metadata['columns'] = [new_name if c == old_name else c for c in self.metadata['columns']]
                            if old_name in self.metadata.get('dtypes', {}):
                                self.metadata['dtypes'][new_name] = self.metadata['dtypes'].pop(old_name)
                elif operation == 'drop_column':
                    df_to_process.drop(columns=[column], inplace=True)
                    if df_input is None: # Only update metadata if modifying self.dataframe
                        if column in self.metadata.get('columns', []):
                            self.metadata['columns'].remove(column)
                            self.metadata['dtypes'].pop(column, None)
                            self.metadata.get('numeric_columns', []).remove(column) if column in self.metadata.get('numeric_columns', []) else None
                            self.metadata.get('categorical_columns', []).remove(column) if column in self.metadata.get('categorical_columns', []) else None
                else:
                    print(f"Warning: Unsupported preprocessing operation '{operation}'. Skipping: {step}")
            except Exception as e:
                print(f"Error during preprocessing operation '{operation}' on column '{column}': {str(e)}")
        
        if df_input is None:
            self.dataframe = df_to_process
            self._extract_metadata()
            print("Preprocessing applied successfully to self.dataframe.")
        return df_to_process

    def sort_data(self, df: pd.DataFrame, by: Union[str, List[str]], ascending: Union[bool, List[bool]] = True) -> pd.DataFrame:
        """Sort dataframe by column(s)
        
        Args:
            df: DataFrame to sort
            by: Column name or list of column names to sort by
            ascending: Whether to sort ascending (True) or descending (False)
            
        Returns:
            Sorted DataFrame
        """
        if df is None: 
            raise ValueError("DataFrame to sort is None.")
        if not by: 
            raise ValueError("Sort column(s) must be specified.")
            
        if isinstance(by, str):
            if by not in df.columns:
                matching_cols = [col for col in df.columns if col.lower() == by.lower()]
                if matching_cols:
                    by = matching_cols[0]
                    print(f"Warning: Sort column '{by}' (original) not found. Using case-insensitive match: {by}")
                else:
                    raise ValueError(f"Sort column '{by}' not found in DataFrame. Available: {list(df.columns)}")
        elif isinstance(by, list):
            processed_by = []
            for col_name in by:
                if col_name not in df.columns:
                    matching_cols = [c for c in df.columns if c.lower() == col_name.lower()]
                    if matching_cols:
                        processed_by.append(matching_cols[0])
                        print(f"Warning: Sort column '{col_name}' not found. Using case-insensitive match: {matching_cols[0]}")
                    else:
                        raise ValueError(f"Sort column '{col_name}' not found in DataFrame. Available: {list(df.columns)}")
                else:
                    processed_by.append(col_name)
            by = processed_by
        else:
            raise TypeError("Sort column(s) must be a string or a list of strings.")
            
        try:
            return df.sort_values(by=by, ascending=ascending)
        except Exception as e:
            print(f"Error during sorting by {by}: {str(e)}")
            raise

    def limit_data(self, df: pd.DataFrame, n: int) -> pd.DataFrame:
        """Limit dataframe to first n rows
        
        Args:
            df: DataFrame to limit
            n: Number of rows to return
            
        Returns:
            Limited DataFrame
        """
        if df is None: 
            raise ValueError("DataFrame to limit is None.")
        if not isinstance(n, int) or n <= 0: 
            raise ValueError("Limit n must be a positive integer.")
            
        try:
            return df.head(n)
        except Exception as e:
            print(f"Error limiting data to {n} rows: {str(e)}")
            raise

    def get_data(self) -> Optional[pd.DataFrame]:
        """Get a copy of the loaded dataframe
        
        Returns:
            Copy of the dataframe or None if no data loaded
        """
        if self.dataframe is None:
            print("Warning: Dataframe is not loaded.")
            return None
        return self.dataframe.copy()

    def get_data_preview(self, n: int = 5) -> Optional[str]:
        """Get a preview of the first n rows of the dataframe
        
        Args:
            n: Number of rows to preview
            
        Returns:
            String representation of the preview
        """
        if self.dataframe is None: 
            return "No data loaded yet."
        if not isinstance(n, int) or n <= 0: 
            return "Number of rows (n) must be a positive integer."
            
        try:
            return self.dataframe.head(n).to_string()
        except Exception as e:
            return f"Error generating data preview: {str(e)}"

    def reset_data(self) -> None:
        """Reset the dataframe and metadata"""
        self.dataframe = None
        self.metadata = {}
        print("DataProcessor has been reset. Load new data to continue.")

    def get_column_names(self) -> List[str]:
        """Get list of column names from the loaded dataframe
        
        Returns:
            List of column names or empty list if no data loaded
        """
        if self.dataframe is None:
            print("Warning: No data loaded. Cannot get column names.")
            return []
        return list(self.dataframe.columns)