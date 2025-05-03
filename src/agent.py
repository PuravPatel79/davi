import os
import json
import re
import traceback
from typing import Dict, Any, List, Optional, Union
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Assuming data_processor and visualizer are in the same directory or package
from .data_processor import DataProcessor
from .visualizer import Visualizer

class DataAnalysisAgent:
    def __init__(self, data_processor: DataProcessor, visualizer: Visualizer, gemini_api_key: Optional[str] = None):
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

            # Initialize LLM with Gemini 1.5 Flash model
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

            # Test the connection
            _ = self.llm.invoke("Test connection")
            print("Successfully connected to Gemini API")
        except Exception as e:
            print(f"Error connecting to Gemini API: {str(e)}")
            print("Please check your API key and internet connection")
            raise

        # Define a flexible prompt template that can handle any data-related query
        # Updated to include preprocessing instructions
        self.query_template = """
You are an expert data analyst assistant. Your task is to analyze the following dataset and respond to the user\s query.

DATASET INFORMATION:
{data_info}

USER QUERY:
{query}

First, determine what type of information the user is looking for:
1. Basic dataset information (columns, rows, structure)
2. Statistical information (mean, median, counts, etc.) - Perform calculations yourself if possible.
3. Visualization request (show, plot, visualize data)
4. Complex analysis (patterns, relationships, insights) - Perform calculations yourself if possible.

For visualization requests, respond ONLY with a JSON object in this format. Include preprocessing steps if necessary (e.g., extracting month from a date column):
```json
{{
  "response_type": "visualization",
  "preprocessing": [
    {{"operation": "operation_name", "column": "source_column", "new_column": "new_column_name"}} 
    // Add more steps if needed. Supported operations: extract_month, extract_year, extract_day, extract_dayofweek
  ],
  "aggregation": {{
    "group_by": ["group_column1", "group_column2"],
    "agg_specs": {{ "NewAggregatedColumnName": "agg_func" }} // e.g., {{"TotalQuantity": "sum"}} or {{"OrderCount": "size"}}
    // Aggregation is optional, only include if needed for the visualization (e.g., summing sales by month)
  }},
  "visualization_params": {{
    "viz_type": "chart_type", // e.g., bar, scatter, line, histogram, pie
    "title": "Chart Title",
    "x": "x_column", // Use new_column_name if created in preprocessing, or aggregated column name
    "y": "y_column", // Optional, use new_column_name or aggregated column name
    "color": "color_column" // Optional
  }}
}}
```

For informational or complex analysis requests that require calculations (like finding the customer with the most items), respond ONLY with a JSON object in this format:
```json
{{
  "response_type": "analysis",
  "filters": [
      {{"column": "column_name", "operator": "operator_symbol", "value": "value_to_filter"}}
      // Supported operators: ==, !=, >, <, >=, <=, isin (value must be a list for isin)
  ],
  "aggregation": {{
    "group_by": ["group_column1"],
    "agg_specs": {{ "AggregatedColumnName": "agg_func" }} // e.g., {{"TotalQuantity": "sum"}}
  }},
  "sort_by": {{ "column": "column_to_sort", "ascending": false }},
  "limit": 1 // Optional: number of top results to return
}}
```

For simple informational requests (like column names, row count) or if you cannot perform the calculation/analysis yourself, provide a clear, concise answer in plain text.

IMPORTANT: 
- Only use columns that actually exist in the dataset information provided.
- When generating JSON, ensure it is valid and strictly follows the specified format.
- For visualization or analysis JSON, ONLY output the JSON block, nothing else.
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
            # Get data info
            data_info = self.data_processor.get_column_info()

            # Call the LLM with the query prompt
            response = self.query_chain.invoke({"data_info": data_info, "query": query})
            response_text = self._extract_response_text(response)

            # Attempt to parse the response as JSON
            parsed_plan = self._extract_json_plan(response_text)

            if parsed_plan:
                response_type = parsed_plan.get("response_type")
                if response_type == "visualization":
                    return self._handle_visualization_request(parsed_plan)
                elif response_type == "analysis":
                    return self._handle_analysis_request(parsed_plan)
                else:
                    # If JSON is present but not the expected type, treat as text
                    print(f"Received unexpected JSON response type: {response_type}")
                    return {"success": True, "message": self._clean_response(response_text), "visualization": None}
            else:
                # If no valid JSON found, treat as a plain text response
                return {"success": True, "message": self._clean_response(response_text), "visualization": None}

        except Exception as e:
            print(f"Error processing query: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error processing query: {str(e)}", "visualization": None}

    def _extract_response_text(self, response: Any) -> str:
        """Extract text from LLM response object"""
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, dict) and 'text' in response:
            return response['text']
        else:
            return str(response)

    def _extract_json_plan(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON plan from response if present, looking for markdown code blocks first."""
        # Prioritize JSON within markdown code blocks
        json_match = re.search(r"```json\n(\{.*?\})\n```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback to finding any JSON-like structure
            json_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                return None
        
        try:
            # Clean potential artifacts before parsing
            json_str = json_str.replace("\n", "").strip()
            plan = json.loads(json_str)
            print(f"Successfully parsed JSON plan: {plan}") # Debug print
            return plan
        except json.JSONDecodeError as e:
            print(f"Found JSON-like pattern but couldn't parse it: {e}")
            print(f"Pattern found: {json_str}") # Debug print
            return None

    def _clean_response(self, text: str) -> str:
        """Clean up the response text by removing JSON and other artifacts if it's not pure JSON."""
        # Check if the text is likely just JSON
        if text.strip().startswith("{") and text.strip().endswith("}"):
             try:
                 json.loads(text)
                 # If it parses as JSON, return a generic message or handle differently
                 # For now, let's assume if it's just JSON, it was meant to be handled by _extract_json_plan
                 # and reaching here means it wasn't the expected format.
                 return "Received a JSON response, but it wasn't in the expected format for visualization or analysis."
             except json.JSONDecodeError:
                 pass # Not valid JSON, proceed with cleaning

        # Remove any JSON blocks within markdown
        text = re.sub(r"```json\n\{.*?\}\n```", "", text, flags=re.DOTALL)
        # Remove any standalone JSON blocks
        text = re.sub(r"^\s*\{.*?\}\s*$", "", text, flags=re.DOTALL | re.MULTILINE)
        # Remove any other markdown code blocks
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        # Clean up extra whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = text.strip()
        return text

    def _handle_visualization_request(self, viz_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a visualization request, including preprocessing and aggregation."""
        try:
            # --- 1. Apply Preprocessing --- 
            preprocessing_steps = viz_plan.get("preprocessing")
            if preprocessing_steps and isinstance(preprocessing_steps, list):
                print(f"Applying preprocessing steps: {preprocessing_steps}")
                try:
                    # Pass a copy of the steps to avoid modifying the original plan
                    self.data_processor.preprocess_data(list(preprocessing_steps))
                except Exception as preproc_e:
                    return {"success": False, "message": f"Error during preprocessing: {str(preproc_e)}", "visualization": None}
            
            # --- 2. Apply Aggregation (if specified) --- 
            aggregation_plan = viz_plan.get("aggregation")
            df_to_visualize = self.data_processor.get_data() # Start with current (potentially preprocessed) data
            if aggregation_plan and isinstance(aggregation_plan, dict):
                group_by = aggregation_plan.get("group_by")
                agg_specs = aggregation_plan.get("agg_specs")
                if group_by and agg_specs:
                    print(f"Applying aggregation: group by {group_by}, specs {agg_specs}")
                    try:
                        df_to_visualize = self.data_processor.aggregate_data(group_by_columns=group_by, agg_specs=agg_specs)
                        print("Aggregation successful.")
                    except Exception as agg_e:
                        return {"success": False, "message": f"Error during aggregation: {str(agg_e)}", "visualization": None}
                else:
                    print("Warning: Aggregation plan found but missing 'group_by' or 'agg_specs'. Skipping aggregation.")
            
            # --- 3. Prepare Visualization Parameters --- 
            viz_params_plan = viz_plan.get("visualization_params")
            if not viz_params_plan or not isinstance(viz_params_plan, dict):
                return {"success": False, "message": "Invalid visualization plan: Missing or invalid 'visualization_params'.", "visualization": None}

            # Get columns available *after* potential aggregation
            available_columns = list(df_to_visualize.columns)
            x_col = viz_params_plan.get("x")
            y_col = viz_params_plan.get("y")
            color_col = viz_params_plan.get("color")
            viz_type = viz_params_plan.get("viz_type", "bar")
            title = viz_params_plan.get("title", "Visualization")

            # Validate essential columns exist in the dataframe being visualized
            if not x_col or x_col not in available_columns:
                return {"success": False, "message": f"X-axis column '{x_col}' not found in the data to visualize (available: {available_columns}).", "visualization": None}
            if y_col and y_col not in available_columns:
                 return {"success": False, "message": f"Y-axis column '{y_col}' not found in the data to visualize (available: {available_columns}).", "visualization": None}
            if color_col and color_col not in available_columns:
                 print(f"Warning: Color column '{color_col}' not found. Ignoring color parameter.")
                 color_col = None # Ignore invalid color column

            # --- 4. Create Visualization --- 
            viz_params = {
                "viz_type": viz_type,
                "df": df_to_visualize, # Pass the potentially aggregated dataframe
                "x": x_col,
                "y": y_col,
                "color": color_col,
                "title": title
            }
            
            print(f"Creating visualization with params: {viz_params_plan}") # Debug print
            visualization = self.visualizer.create_visualization(**viz_params)
            
            # --- 5. Generate Explanation --- 
            explanation = f"Created a {viz_type} chart titled '{title}' "
            if y_col:
                explanation += f"showing {y_col} vs {x_col}"
            else:
                explanation += f"showing distribution of {x_col}"
            if color_col:
                explanation += f", colored by {color_col}"
            if aggregation_plan:
                 explanation += f" (data aggregated by {aggregation_plan.get('group_by')})"
            if preprocessing_steps:
                 explanation += f" (preprocessing applied)"

            return {"success": True, "message": explanation, "visualization": visualization}

        except Exception as e:
            print(f"Error handling visualization request: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error creating visualization: {str(e)}", "visualization": None}

    def _handle_analysis_request(self, analysis_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a complex analysis request using filtering, aggregation, sorting."""
        try:
            df = self.data_processor.get_data() # Start with original data

            # --- 1. Apply Filters --- 
            filters = analysis_plan.get("filters")
            if filters and isinstance(filters, list):
                filter_dict = {}
                for f in filters:
                    if isinstance(f, dict) and 'column' in f and 'operator' in f and 'value' in f:
                        # Convert filter list to the nested dict format expected by filter_data
                        filter_dict[f['column']] = {'operator': f['operator'], 'value': f['value']}
                    else:
                        print(f"Warning: Skipping invalid filter format: {f}")
                
                if filter_dict:
                    print(f"Applying filters: {filter_dict}")
                    try:
                        df = self.data_processor.filter_data(filter_dict)
                        print(f"Data filtered. Shape after filtering: {df.shape}")
                    except Exception as filter_e:
                        return {"success": False, "message": f"Error during filtering: {str(filter_e)}", "visualization": None}

            # --- 2. Apply Aggregation --- 
            aggregation_plan = analysis_plan.get("aggregation")
            if aggregation_plan and isinstance(aggregation_plan, dict):
                group_by = aggregation_plan.get("group_by")
                agg_specs = aggregation_plan.get("agg_specs")
                if group_by and agg_specs:
                    print(f"Applying aggregation: group by {group_by}, specs {agg_specs}")
                    try:
                        # Need a temporary processor or modify aggregate_data to accept df
                        # For now, let's assume aggregate_data works on the processor's internal df
                        # This is a limitation - ideally, operations should chain on the df
                        # Quick fix: temporarily replace processor's df, aggregate, then restore
                        original_df = self.data_processor.dataframe
                        self.data_processor.dataframe = df 
                        df = self.data_processor.aggregate_data(group_by_columns=group_by, agg_specs=agg_specs)
                        self.data_processor.dataframe = original_df # Restore original
                        print(f"Aggregation successful. Shape after aggregation: {df.shape}")
                    except Exception as agg_e:
                        # Restore original df even if aggregation fails
                        self.data_processor.dataframe = original_df 
                        return {"success": False, "message": f"Error during aggregation: {str(agg_e)}", "visualization": None}
                else:
                    print("Warning: Aggregation plan found but missing 'group_by' or 'agg_specs'. Skipping aggregation.")

            # --- 3. Apply Sorting --- 
            sort_plan = analysis_plan.get("sort_by")
            if sort_plan and isinstance(sort_plan, dict):
                sort_col = sort_plan.get("column")
                ascending = sort_plan.get("ascending", True) # Default to ascending
                if sort_col and sort_col in df.columns:
                    print(f"Sorting by {sort_col}, ascending={ascending}")
                    try:
                        df = df.sort_values(by=sort_col, ascending=ascending)
                    except Exception as sort_e:
                         return {"success": False, "message": f"Error during sorting: {str(sort_e)}", "visualization": None}
                elif sort_col:
                    print(f"Warning: Sort column '{sort_col}' not found in the current data. Skipping sort.")

            # --- 4. Apply Limit --- 
            limit = analysis_plan.get("limit")
            if limit and isinstance(limit, int) and limit > 0:
                print(f"Applying limit: {limit}")
                df = df.head(limit)

            # --- 5. Format Result --- 
            # Convert result dataframe to a string format for display
            result_message = f"Analysis complete. Result ({df.shape[0]} rows):"
            result_message += df.to_string()

            return {"success": True, "message": result_message, "visualization": None}

        except Exception as e:
            print(f"Error handling analysis request: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error performing analysis: {str(e)}", "visualization": None}

    # --- Fallback Pandas Handling (Kept for simple cases, but LLM analysis is preferred) --- 
    def _pandas_query_handling(self, query: str) -> Optional[Dict[str, Any]]:
        """Handle simple queries using pandas operations as a fallback."""
        # This function remains largely unchanged but is less likely to be called
        # if the LLM successfully returns analysis JSON.
        try:
            df = self.data_processor.dataframe
            if df is None: return None # No data loaded
            columns = self.data_processor.metadata['columns']
            query_lower = query.lower()
            
            query_patterns = {
                r"how many columns|number of columns|column count|total columns": 
                    lambda: {"success": True, "message": f"The dataset has {len(columns)} columns: {', '.join(columns)}", "visualization": None},
                r"how many rows|number of rows|row count|data points|sample size|how many records|total records": 
                    lambda: {"success": True, "message": f"The dataset has {len(df)} rows (data points).", "visualization": None},
                r"(average|mean)\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(2), "mean", "average"),
                r"median\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(1), "median", "median"),
                r"(maximum|max)\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(2), "max", "maximum"),
                r"(minimum|min)\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(2), "min", "minimum"),
                r"count\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(1), "count", "count"),
                r"sum\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(1), "sum", "sum"),
                r"(std|standard deviation)\s+(?:of\s+)?(\S+)": 
                    lambda m: self._handle_column_stat(m.group(2), "std", "standard deviation"),
                r"describe\s+(?:column\s+)?(\S+)": 
                    lambda m: self._handle_column_description(m.group(1))
            }
            
            for pattern, handler in query_patterns.items():
                match = re.search(pattern, query_lower)
                if match:
                    # Check if handler expects a match object
                    import inspect
                    sig = inspect.signature(handler)
                    if len(sig.parameters) > 0:
                        return handler(match)
                    else:
                        return handler()
            return None
        except Exception as e:
            print(f"Error in pandas query handling: {str(e)}")
            return None

    def _handle_column_stat(self, col_name: str, stat_name: str, display_name: str) -> Dict[str, Any]:
        """Handle statistical operation on a column (Fallback)."""
        # Find the actual column name (case-insensitive match, more robust)
        matched_col = None
        for actual_col in self.data_processor.metadata['columns']:
            # Simple substring match - might need refinement for exactness
            if col_name.lower() == actual_col.lower():
                 matched_col = actual_col
                 break
            # Allow partial match if only one possibility?
            # if col_name.lower() in actual_col.lower(): ... (potential ambiguity)
        
        if not matched_col:
             return {"success": False, "message": f"Could not find column matching '{col_name}'.", "visualization": None}

        if matched_col in self.data_processor.metadata.get('numeric_columns', []):
            try:
                series = self.data_processor.dataframe[matched_col]
                stat_value = getattr(series, stat_name)() # Use getattr for dynamic method call
                return {"success": True, "message": f"The {display_name} of {matched_col} is {stat_value:.4f}", "visualization": None}
            except Exception as e:
                return {"success": False, "message": f"Error calculating {display_name} of {matched_col}: {str(e)}", "visualization": None}
        else:
             return {"success": False, "message": f"Column '{matched_col}' is not numeric.", "visualization": None}

    def _handle_column_description(self, col_name: str) -> Dict[str, Any]:
        """Handle column description request (Fallback)."""
        matched_col = None
        for actual_col in self.data_processor.metadata['columns']:
            if col_name.lower() == actual_col.lower():
                 matched_col = actual_col
                 break
        
        if not matched_col:
             return {"success": False, "message": f"Could not find column matching '{col_name}'.", "visualization": None}

        try:
            description = self.data_processor.dataframe[matched_col].describe().to_string()
            return {"success": True, "message": f"Description of {matched_col}:\n{description}", "visualization": None}
        except Exception as e:
             return {"success": False, "message": f"Error describing column {matched_col}: {str(e)}", "visualization": None}