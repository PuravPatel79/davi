import os
import json
import re
import traceback
from typing import Dict, Any, List, Optional, Union
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class DataAnalysisAgent:
    def __init__(self, data_processor, visualizer, gemini_api_key=None):
        self.data_processor = data_processor
        self.visualizer = visualizer
        
        # Set API key
        if gemini_api_key:
            os.environ["GOOGLE_API_KEY"] = gemini_api_key
            print("Using provided Gemini API key")
        elif "GOOGLE_API_KEY" in os.environ:
            print("Using Gemini API key from environment variables")
        else:
            raise ValueError("Gemini API key is required. Please provide it or set the GOOGLE_API_KEY environment variable.")
        
        try:
            # Configure the Google Generative AI library
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            
            # Initialize LLM with Gemini 2.5 model (Use 'gemini-1.5-flash' as an option)
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-exp-03-25", temperature=0)
            
            # Test the connection
            _ = self.llm.invoke("Test connection")
            print("Successfully connected to Gemini API")
        except Exception as e:
            print(f"Error connecting to Gemini API: {str(e)}")
            print("Please check your API key and internet connection")
            raise
        
        # Flexible prompt template that can handle any data-related query
        self.query_template = """
You are an expert data analyst assistant. Your task is to analyze the following dataset and respond to the user's query.

DATASET INFORMATION:
{data_info}

USER QUERY:
{query}

First, determine what type of information the user is looking for:
1. Basic dataset information (columns, rows, structure, etc.)
2. Statistical information (mean, median, counts, etc.)
3. Visualization request (show, plot, visualize data, etc.)
4. Complex analysis (patterns, relationships, insights, etc.)

For visualization requests, respond with a JSON object in this format:
{{
  "response_type": "visualization",
  "columns": ["column1", "column2"],
  "visualization": "chart_type",
  "title": "Chart Title",
  "x": "x_column",
  "y": "y_column",
  "color": "color_column"
}}

For statistical requests, respond with a JSON object in this format:
{{
  "response_type": "statistic",
  "operation": "mean|median|max|min|count|sum|std",
  "column": "column_name"
}}

For all other requests, provide a clear, concise answer in plain text.

Remember to only use columns that actually exist in the dataset.
"""
        
        # Initialize prompt template and chain
        self.query_prompt = PromptTemplate(
            input_variables=["data_info", "query"],
            template=self.query_template
        )
        
        # Initialize chain
        self.query_chain = LLMChain(llm=self.llm, prompt=self.query_prompt)
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process any data-related query and return appropriate results"""
        try:
            # Pre-process the query to check for simple column value requests
            simple_result = self._check_simple_column_query(query)
            if simple_result:
                return simple_result
            
            # Get data info
            data_info = self.data_processor.get_column_info()
            
            # First, try using the LLM
            try:
                # Call the LLM with the query prompt
                response = self.query_chain.invoke({"data_info": data_info, "query": query})
                
                # Extract the text from the response
                response_text = self._extract_response_text(response)
                
                # Check if the response contains a visualization JSON
                viz_plan = self._extract_visualization_plan(response_text)
                
                if viz_plan:
                    if viz_plan.get("response_type") == "visualization":
                        # This is a visualization request
                        return self._handle_visualization_request(viz_plan)
                    elif viz_plan.get("response_type") == "statistic":
                        # This is a statistical request
                        return self._handle_statistic_request(viz_plan)
                
                # If no JSON plan was found or processed, return the text response
                return {
                    "success": True,
                    "message": self._clean_response(response_text),
                    "visualization": None
                }
                
            except Exception as e:
                print(f"Error processing with LLM: {str(e)}")
                traceback.print_exc()
                
                # If LLM fails, fall back to pandas operations
                print("Falling back to pandas operations")
                result = self._pandas_query_handling(query)
                if result:
                    return result
                
                return {
                    "success": False,
                    "message": f"Error processing your query: {str(e)}",
                    "visualization": None
                }
                
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error processing query: {str(e)}",
                "visualization": None
            }
    
    def _check_simple_column_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Check if the query is asking for a simple column value or statistic"""
        query_lower = query.lower()
        
        # Check for "what is [column]" pattern
        what_is_match = re.search(r"what is (?:the )?(\w+)(?:\s+\w+)?", query_lower)
        if what_is_match:
            col_name = what_is_match.group(1)
            
            # Check if this is a column name
            for actual_col in self.data_processor.metadata['columns']:
                if col_name in actual_col.lower():
                    # If it's a numeric column, return statistics
                    if actual_col in self.data_processor.metadata.get('numeric_columns', []):
                        stats = self.data_processor.dataframe[actual_col].describe().to_dict()
                        return {
                            "success": True,
                            "message": f"Statistics for {actual_col}:\n" + 
                                      f"Mean: {stats['mean']:.4f}\n" +
                                      f"Median: {stats['50%']:.4f}\n" +
                                      f"Min: {stats['min']:.4f}\n" +
                                      f"Max: {stats['max']:.4f}",
                            "visualization": None
                        }
                    else:
                        # For categorical columns, return value counts
                        value_counts = self.data_processor.dataframe[actual_col].value_counts().head(10).to_dict()
                        value_str = "\n".join([f"{k}: {v}" for k, v in value_counts.items()])
                        return {
                            "success": True,
                            "message": f"Top values for {actual_col}:\n{value_str}",
                            "visualization": None
                        }
        
        return None
    
    def _extract_response_text(self, response: Any) -> str:
        """Extract text from LLM response object"""
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, dict) and 'text' in response:
            return response['text']
        else:
            return str(response)
    
    def _extract_visualization_plan(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON plan from response if present"""
        # Try to find JSON in the response
        json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
        if not json_match:
            return None
        
        try:
            plan = json.loads(json_match.group(0))
            return plan
        except json.JSONDecodeError:
            print("Found JSON-like pattern but couldn't parse it")
            print(f"Pattern found: {json_match.group(0)}")
            
            # Try to extract information from malformed JSON
            if "{" in response_text and "}" in response_text:
                # Check for statistical operations
                stat_match = re.search(r'"operation":\s*"(\w+)"', response_text)
                col_match = re.search(r'"column":\s*"(\w+)"', response_text)
                
                if stat_match and col_match:
                    return {
                        "response_type": "statistic",
                        "operation": stat_match.group(1),
                        "column": col_match.group(1)
                    }
            
            return None
    
    def _clean_response(self, text: str) -> str:
        """Clean up the response text by removing JSON and other artifacts"""
        # Remove any JSON blocks
        text = re.sub(r'\{.*?\}', '', text, flags=re.DOTALL)
        
        # Remove any markdown code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def _handle_visualization_request(self, viz_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a visualization request"""
        try:
            # Get columns from the dataset
            available_columns = self.data_processor.metadata['columns']
            
            # Check if the requested columns exist
            requested_columns = viz_plan.get("columns", [])
            if not requested_columns:
                # If no columns specified, try to use x and y
                x_col = viz_plan.get("x")
                y_col = viz_plan.get("y")
                if x_col:
                    requested_columns.append(x_col)
                if y_col and y_col != x_col:
                    requested_columns.append(y_col)
            
            # If still no columns, use the first column
            if not requested_columns and available_columns:
                requested_columns = [available_columns[0]]
            
            # Validate columns exist
            valid_columns = [col for col in requested_columns if col in available_columns]
            if not valid_columns:
                return {
                    "success": False,
                    "message": f"None of the requested columns {requested_columns} exist in the dataset.",
                    "visualization": None
                }
            
            # Get visualization type
            viz_type = viz_plan.get("visualization", "bar")
            
            # Get x and y columns
            x_col = viz_plan.get("x", valid_columns[0])
            y_col = viz_plan.get("y")
            
            # If y is not specified but we have multiple columns, use the second one
            if not y_col and len(valid_columns) > 1:
                y_col = valid_columns[1]
            
            # Create visualization
            viz_params = {
                "viz_type": viz_type,
                "x": x_col,
                "y": y_col,
                "color": viz_plan.get("color"),
                "title": viz_plan.get("title", f"Analysis of {', '.join(valid_columns)}")
            }
            
            # Generate visualization
            visualization = self.visualizer.create_visualization(**viz_params)
            
            # Generate explanation
            explanation = f"Created a {viz_type} chart "
            if y_col:
                explanation += f"showing {y_col} by {x_col}"
            else:
                explanation += f"showing distribution of {x_col}"
            
            if viz_params['color']:
                explanation += f", colored by {viz_params['color']}"
            
            return {
                "success": True,
                "message": explanation,
                "visualization": visualization
            }
        except Exception as e:
            print(f"Error creating visualization: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error creating visualization: {str(e)}",
                "visualization": None
            }
    
    def _handle_statistic_request(self, stat_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a statistical request"""
        operation = stat_plan.get("operation")
        column = stat_plan.get("column")
        
        if not operation or not column:
            return {
                "success": False,
                "message": "Missing operation or column in statistical request",
                "visualization": None
            }
        
        return self._handle_column_stat(column, operation, operation)
    
    def _pandas_query_handling(self, query: str) -> Optional[Dict[str, Any]]:
        """Handle queries using pandas operations"""
        try:
            # Get the dataframe
            df = self.data_processor.dataframe
            columns = self.data_processor.metadata['columns']
            
            # Lowercase query for easier matching
            query_lower = query.lower()
            
            # Dictionary of query patterns and their corresponding pandas operations
            query_patterns = {
                # Column count patterns
                r"how many columns|number of columns|column count|total columns": 
                    lambda: {
                        "success": True,
                        "message": f"The dataset has {len(columns)} columns: {', '.join(columns)}",
                        "visualization": None
                    },
                
                # Row count patterns
                r"how many rows|number of rows|row count|data points|sample size|how many records|total records": 
                    lambda: {
                        "success": True,
                        "message": f"The dataset has {len(df)} rows (data points).",
                        "visualization": None
                    },
                
                # Mean/average patterns
                r"(average|mean)\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(2), "mean", "average"),
                
                # Median patterns
                r"median\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(1), "median", "median"),
                
                # Max patterns
                r"(maximum|max)\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(2), "max", "maximum"),
                
                # Min patterns
                r"(minimum|min)\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(2), "min", "minimum"),
                
                # Count patterns
                r"count\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(1), "count", "count"),
                
                # Sum patterns
                r"sum\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(1), "sum", "sum"),
                
                # Standard deviation patterns
                r"(std|standard deviation)\s+(?:of\s+)?(\w+)": 
                    lambda match: self._handle_column_stat(match.group(2), "std", "standard deviation"),
                
                # Describe column patterns
                r"describe\s+(?:column\s+)?(\w+)": 
                    lambda match: self._handle_column_description(match.group(1)),
                
                # What is column patterns
                r"what is (?:the )?(\w+)(?:\s+\w+)?": 
                    lambda match: self._handle_column_description(match.group(1))
            }
            
            # Check each pattern
            for pattern, handler in query_patterns.items():
                match = re.search(pattern, query_lower)
                if match:
                    return handler(match) if callable(handler) and match.groups() else handler()
            
            # No direct handling possible
            return None
                
        except Exception as e:
            print(f"Error in pandas query handling: {str(e)}")
            traceback.print_exc()
            return None

    def _handle_column_stat(self, col_name: str, stat_name: str, display_name: str) -> Dict[str, Any]:
        """Handle statistical operation on a column"""
        # Find the actual column name (case-insensitive match)
        for actual_col in self.data_processor.metadata['columns']:
            if col_name.lower() in actual_col.lower():
                if actual_col in self.data_processor.metadata.get('numeric_columns', []):
                    try:
                        # Get the pandas Series
                        series = self.data_processor.dataframe[actual_col]
                        
                        # Apply the statistical method
                        if stat_name == "mean":
                            stat_value = series.mean()
                        elif stat_name == "median":
                            stat_value = series.median()
                        elif stat_name == "max":
                            stat_value = series.max()
                        elif stat_name == "min":
                            stat_value = series.min()
                        elif stat_name == "count":
                            stat_value = series.count()
                        elif stat_name == "sum":
                            stat_value = series.sum()
                        elif stat_name == "std":
                            stat_value = series.std()
                        else:
                            return {
                                "success": False,
                                "message": f"Unsupported statistical operation: {stat_name}",
                                "visualization": None
                            }
                        
                        return {
                            "success": True,
                            "message": f"The {display_name} of {actual_col} is {stat_value:.4f}",
                            "visualization": None
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "message": f"Error calculating {display_name} of {actual_col}: {str(e)}",
                            "visualization": None
                        }
        
        return {
            "success": False,
            "message": f"Could not find column matching '{col_name}' or it's not a numeric column",
            "visualization": None
        }

    def _handle_column_description(self, col_name: str) -> Dict[str, Any]:
        """Handle column description request"""
        # Find the actual column name (case-insensitive match)
        for actual_col in self.data_processor.metadata['columns']:
            if col_name.lower() in actual_col.lower():
                if actual_col in self.data_processor.metadata.get('numeric_columns', []):
                    stats = self.data_processor.dataframe[actual_col].describe().to_dict()
                    return {
                        "success": True,
                        "message": f"Statistics for column '{actual_col}':\n" + 
                                  f"Count: {stats['count']}\n" +
                                  f"Mean: {stats['mean']:.4f}\n" +
                                  f"Std: {stats['std']:.4f}\n" +
                                  f"Min: {stats['min']:.4f}\n" +
                                  f"25%: {stats['25%']:.4f}\n" +
                                  f"50%: {stats['50%']:.4f}\n" +
                                  f"75%: {stats['75%']:.4f}\n" +
                                  f"Max: {stats['max']:.4f}",
                        "visualization": None
                    }
                else:
                    value_counts = self.data_processor.dataframe[actual_col].value_counts().head(10).to_dict()
                    value_str = "\n".join([f"{k}: {v}" for k, v in value_counts.items()])
                    return {
                        "success": True,
                        "message": f"Top values for column '{actual_col}':\n{value_str}",
                        "visualization": None
                    }
        
        return {
            "success": False,
            "message": f"Could not find column matching '{col_name}'",
            "visualization": None
        }