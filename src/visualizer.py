import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, Optional, List

class Visualizer:
    def __init__(self, data_processor):
        self.data_processor = data_processor
    
    def create_visualization(self, viz_type: str, x: Optional[str] = None, 
                            y: Optional[str] = None, color: Optional[str] = None, 
                            title: Optional[str] = None, **kwargs) -> go.Figure:
        """Create visualization based on type and parameters"""
        if self.data_processor.dataframe is None:
            return "No data loaded. Please load data first."
        
        df = self.data_processor.dataframe
        
        try:
            if viz_type == 'bar':
                fig = px.bar(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'line':
                fig = px.line(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'scatter':
                fig = px.scatter(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'histogram':
                fig = px.histogram(df, x=x, title=title, **kwargs)
            elif viz_type == 'pie':
                fig = px.pie(df, names=x, values=y, title=title, **kwargs)
            elif viz_type == 'box':
                fig = px.box(df, x=x, y=y, color=color, title=title, **kwargs)
            elif viz_type == 'heatmap':
                # For heatmap, we need to pivot the data
                if x and y and 'z' in kwargs:
                    z = kwargs.pop('z')
                    pivot_df = df.pivot(index=y, columns=x, values=z)
                    fig = px.imshow(pivot_df, title=title, **kwargs)
                else:
                    # Correlation heatmap
                    corr_df = df.select_dtypes(include=['number']).corr()
                    fig = px.imshow(corr_df, title=title or "Correlation Heatmap", **kwargs)
            else:
                return f"Visualization type '{viz_type}' not supported."
            
            return fig
        except Exception as e:
            return f"Error creating visualization: {str(e)}"
    
    def recommend_visualization(self, columns: List[str]) -> Dict[str, Any]:
        """Recommend visualization type based on columns"""
        if self.data_processor.dataframe is None:
            return "No data loaded. Please load data first."
        
        df = self.data_processor.dataframe
        metadata = self.data_processor.metadata
        
        # Check if columns exist
        for col in columns:
            if col not in df.columns:
                return f"Column '{col}' not found in the dataset."
        
        # Simple recommendation logic
        if len(columns) == 1:
            col = columns[0]
            if col in metadata.get('numeric_columns', []):
                return {'type': 'histogram', 'x': col}
            else:
                return {'type': 'bar', 'x': col}
        
        elif len(columns) == 2:
            col1, col2 = columns
            
            # Two numeric columns
            if col1 in metadata.get('numeric_columns', []) and col2 in metadata.get('numeric_columns', []):
                return {'type': 'scatter', 'x': col1, 'y': col2}
            
            # One numeric, one categorical
            elif col1 in metadata.get('numeric_columns', []) and col2 not in metadata.get('numeric_columns', []):
                return {'type': 'box', 'x': col2, 'y': col1}
            elif col2 in metadata.get('numeric_columns', []) and col1 not in metadata.get('numeric_columns', []):
                return {'type': 'box', 'x': col1, 'y': col2}
            
            # Two categorical columns
            else:
                return {'type': 'heatmap', 'x': col1, 'y': col2}
        
        return "Could not determine appropriate visualization for the given columns."