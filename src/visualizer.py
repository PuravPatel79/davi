import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import traceback
from typing import Dict, Any, Optional, List

class Visualizer:
    def __init__(self, data_processor):
        # Store the data_processor instance if needed for other methods,
        # but create_visualization should primarily use the passed df.
        self.data_processor = data_processor 
    
    def create_visualization(self, viz_type: str, df: pd.DataFrame, 
                            x: Optional[str] = None, y: Optional[str] = None, 
                            color: Optional[str] = None, title: Optional[str] = None, 
                            **kwargs) -> Optional[go.Figure]:
        """Create visualization based on type and parameters using the provided dataframe.
        
        Args:
            viz_type: Type of chart (e.g., bar, scatter).
            df: The pandas DataFrame to use for plotting (potentially preprocessed/aggregated).
            x: Column name for the x-axis.
            y: Column name for the y-axis.
            color: Column name for coloring.
            title: Title for the chart.
            **kwargs: Additional arguments for Plotly Express functions.

        Returns:
            A Plotly Figure object if successful, None otherwise.
        """
        if df is None or df.empty:
            print("Error: Cannot create visualization with empty or None dataframe.")
            return None
        
        # Validate columns exist in the passed dataframe
        required_cols = [col for col in [x, y, color] if col is not None]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Error: Missing required columns in the provided dataframe: {missing_cols}. Available: {list(df.columns)}")
            return None
            
        fig = None # Initialize fig to None
        try:
            print(f"Visualizer attempting to create 	{viz_type}	 chart with columns: x={x}, y={y}, color={color}") # Debug print
            if viz_type == 'bar':
                fig = px.bar(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'line':
                fig = px.line(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'scatter':
                fig = px.scatter(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'histogram':
                fig = px.histogram(df, x=x, color=color, title=title, **kwargs)
            elif viz_type == 'pie':
                fig = px.pie(df, names=x, values=y, title=title, **kwargs)
            elif viz_type == 'box':
                fig = px.box(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'heatmap':
                if x and y and 'z' in kwargs:
                    z = kwargs.pop('z')
                    if z not in df.columns:
                        print(f"Error: Z-axis column 	{z}	 not found for heatmap.")
                        return None
                    try:
                        pivot_df = df.pivot(index=y, columns=x, values=z)
                        fig = px.imshow(pivot_df, title=title, **kwargs)
                    except Exception as pivot_e:
                        print(f"Error pivoting data for heatmap: {pivot_e}")
                        return None
                else:
                    numeric_df = df.select_dtypes(include=['number'])
                    if not numeric_df.empty:
                        corr_df = numeric_df.corr()
                        fig = px.imshow(corr_df, title=title or "Correlation Heatmap", **kwargs)
                    else:
                        print("Error: No numeric columns found in the provided data for correlation heatmap.")
                        return None
            else:
                print(f"Visualization type '{viz_type}' not supported.")
                return None
            
            # Check if fig is a valid Plotly Figure before returning
            if isinstance(fig, go.Figure):
                print("Successfully created Plotly figure.")
                return fig
            else:
                # This case should not be reached if px functions work
                print(f"Error: Plotly Express function for '{viz_type}' did not return a valid Figure object.")
                return None
                
        except Exception as e:
            print(f"Error creating visualization of type '{viz_type}': {str(e)}")
            traceback.print_exc() # Print full traceback for debugging
            return None
    
    # recommend_visualization might still use self.data_processor if it's meant
    # to recommend based on the *original* loaded data, which seems reasonable.
    def recommend_visualization(self, columns: List[str]) -> Dict[str, Any]:
        """Recommend visualization type based on columns in the original dataset"""
        if self.data_processor.dataframe is None:
            return {"error": "No data loaded. Please load data first."}
        
        df = self.data_processor.dataframe
        metadata = self.data_processor.metadata
        
        # Check if columns exist
        for col in columns:
            if col not in df.columns:
                return {"error": f"Column '{col}' not found in the dataset."}
        
        # Simple recommendation logic (remains unchanged)
        if len(columns) == 1:
            col = columns[0]
            if col in metadata.get('numeric_columns', []):
                return {'type': 'histogram', 'x': col}
            else:
                # Use count for categorical bar charts if y isn't specified
                return {'type': 'bar', 'x': col} 
        
        elif len(columns) == 2:
            col1, col2 = columns
            num_col1 = col1 in metadata.get('numeric_columns', [])
            num_col2 = col2 in metadata.get('numeric_columns', [])
            
            if num_col1 and num_col2:
                return {'type': 'scatter', 'x': col1, 'y': col2}
            elif num_col1 and not num_col2:
                return {'type': 'box', 'x': col2, 'y': col1}
            elif not num_col1 and num_col2:
                return {'type': 'box', 'x': col1, 'y': col2}
            else:
                # For simplicity, let's output a grouped bar chart if there is aggregation error
                return {'type': 'bar', 'x': col1, 'color': col2} # Grouped bar
        
        return {"error": "Could not determine appropriate visualization for the given columns."}