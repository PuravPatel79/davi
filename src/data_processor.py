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
            if file_path.startswith('http://')  or file_path.startswith('https://') :
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
                                self.dataframe = pd.read_csv(file_path, engine='python')
                                print("Successfully loaded CSV with python engine from URL")
            
            # Handle local files
            elif os.path.exists(file_path):
                if file_path.endswith('.csv'):
                    try:
                        self.dataframe = pd.read_csv(file_path)
                    except pd.errors.ParserError:
                        try:
                            self.dataframe = pd.read_csv(file_path, sep=';')
                        except pd.errors.ParserError:
                            try:
                                self.dataframe = pd.read_csv(file_path, sep='\t')
                            except pd.errors.ParserError:
                                self.dataframe = pd.read_csv(file_path, engine='python')
                    print(f"Successfully loaded local CSV file: {file_path}")
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
    
    def filter_data(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Filter dataframe based on conditions"""
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")
        
        filtered_df = self.dataframe.copy()
        for column, value in filters.items():
            if column in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[column] == value]
        
        return filtered_df
    
    def get_data(self) -> pd.DataFrame:
        """Get the current dataframe"""
        if self.dataframe is None:
            raise ValueError("No data loaded yet.")
        return self.dataframe