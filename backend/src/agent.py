import os
import json
import re
import traceback
from typing import Dict, Any, List, Optional, Union, Literal
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd

from data_processor import DataProcessor
from visualizer import Visualizer

class DataAnalysisAgent:
    def __init__(self, data_processor: DataProcessor, visualizer: Visualizer, gemini_api_key: Optional[str] = None):
        self.data_processor = data_processor
        self.visualizer = visualizer

        if gemini_api_key:
            os.environ["GOOGLE_API_KEY"] = gemini_api_key
        elif "GOOGLE_API_KEY" not in os.environ:
            raise ValueError("Gemini API key is required. Please provide it or set the GOOGLE_API_KEY environment variable.")

        try:
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
        except Exception as e:
            print(f"Error connecting to Gemini API: {str(e)}")
            raise

        self.informational_instructions = """
INSTRUCTIONS:
- Analyze the user query based on the dataset information.
- If the query requires calculations (like finding the customer with the most items, summing quantities, counting orders, calculating ratios), respond ONLY with a JSON object in this format. 
- The `summary_text` field MUST be an empty string "" in this initial plan. The actual summary will be generated later based on the results.
- IMPORTANT: For total or overall aggregations (like total profit, total sales), ALWAYS use an empty list ([]) as the group_by value, NOT null or omitting it.

```json
{
    "response_type": "analysis",
    "summary_text": "",
    "filters": [
        {"column": "column_name", "operator": "operator_symbol", "value": "value_to_filter"}
      // Example: [{ "column": "Country", "operator": "==", "value": "India" }]
    ],
    "aggregation": {
    "group_by": [],  // EMPTY LIST ([]) for overall totals, e.g., "total profit for India"
    "agg_specs": { "OutputColumnName": { "agg_func": "sum|mean|count|...", "source_column": "ExactColumnNameFromDataset" } }
    // Example for 'total profit for India': { "group_by": [], "agg_specs": { "TotalProfit": { "agg_func": "sum", "source_column": "Profit" } } }
    },
    "post_aggregation": {
    "calculations": [
        { "name": "NewCalculatedColumnName", "formula": "Operand1Column / Operand2Column" } 
      // Supported operations: /, *, +, -
      // Ensure Operand1Column and Operand2Column exist in the aggregated data.
    ]
    },
    "sort_by": { "column": "OutputColumnNameOrNewCalculatedColumnName", "ascending": false },
  "limit": 1 // Only apply limit if explicitly asked for top N, otherwise omit or set to null for total/sum queries.
}
```
- For simple informational requests (like column names, row count) or if you cannot perform the calculation/analysis yourself, provide a clear, concise answer in plain text.
- **IMPORTANT: Do NOT generate a plan for data visualization in this mode.**
"""

        # --- UPDATED VISUALIZATION INSTRUCTIONS ---
        self.visualization_instructions = """
INSTRUCTIONS:
- Analyze the user query based on the dataset information.
- Generate ONLY a JSON object describing the necessary data preprocessing (if any), aggregation (if any), and visualization parameters needed to create the requested visualization. Use this format:
```json
{
    "response_type": "visualization",
    "preprocessing": [
        {"operation": "operation_name", "column": "source_column", "new_column": "new_column_name"}
    ],
    "aggregation": {
        "group_by": ["group_column1", "group_column2"],
        "agg_specs": { "NewAggregatedColumnName": { "agg_func": "sum|mean|count|...", "source_column": "ExactColumnNameFromDataset" } }
    },
    "visualization_params": {
        "viz_type": "chart_type",
        "title": "Chart Title",
        "x": "x_column",
        "y": "y_column",
        "color": "color_column",
        "z": "z_column_for_heatmap"
    }
}
```
- **CRITICAL RULE 1:** For stacked bar charts, you MUST use `viz_type: "bar"` and specify the stacking category in the `color` parameter.
- **CRITICAL RULE 2:** For heatmaps, you MUST use `viz_type: "heatmap"` and provide `x`, `y`, and `z` parameters. The `z` parameter is the numeric value for the color intensity.
- **IMPORTANT: Only output the JSON block, nothing else.**
"""

        self.sql_instructions = """
INSTRUCTIONS:
- You are an expert SQL query generator. Your task is to convert natural language questions into valid SQL queries.
- Analyze the dataset information provided and generate a SQL query that answers the user's question.
- CRITICAL: ONLY use column names that EXACTLY match those listed in the DATASET INFORMATION section. Do not invent, rename, or assume any columns.
- The SQL query should be valid, efficient, and directly answer the user's question.
- Use proper SQL syntax with appropriate SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, and LIMIT clauses as needed.
- Assume the dataset is stored in a table called 'data'.
- For aggregation functions, use standard SQL functions like SUM, AVG, COUNT, MIN, MAX.
- For filtering, use appropriate WHERE conditions with proper operators (=, >, <, >=, <=, LIKE, IN, etc.).
- For string comparisons, use single quotes (e.g., WHERE Country = 'USA').
- For date operations, use appropriate date functions based on the database system.
- Include comments to explain complex parts of the query.
- Format the SQL query with proper indentation for readability.
- Provide a brief explanation of what the query does and how it answers the user's question.

Example response format:
```sql
-- Query to find total sales by country
SELECT Country, SUM(Sales) as TotalSales
FROM data
GROUP BY Country
ORDER BY TotalSales DESC;
```

This query calculates the total sales for each country by summing the Sales column, grouping the results by Country, and sorting them in descending order of total sales.
"""

        self.code_generation_instructions = """
INSTRUCTIONS:
- You are an expert Python data scientist. Your task is to write a Python script to answer the user's query.
- **CRITICAL RULE 1**: The script MUST start by importing pandas and loading the dataset from 'data.csv' into a DataFrame named `df`. Example: `import pandas as pd\\ndf = pd.read_csv('data.csv')`
- The script should be self-contained and perform all necessary analysis.
- **CRITICAL RULE 2**: Do NOT include any explanations, comments, or markdown formatting. Output ONLY the raw Python code.
- For data analysis (e.g., calculating totals, filtering), the script MUST end by printing the final DataFrame to stdout (e.g., `print(result_df.to_string())`).
- **CRITICAL FOR VISUALIZATIONS**: For visualization requests, the script MUST generate a Plotly figure object and assign it to a variable named `fig` (e.g., `fig = px.bar(...)`). The script MUST then end by printing the figure's JSON representation to stdout (e.g., `print(fig.to_json())`).
- Use only the libraries available: pandas, plotly.express as px, plotly.graph_objects as go.
"""

        self.base_template = """
You are an expert data analyst assistant. Your task is to analyze the following dataset and respond to the user's query based on the provided instructions.

DATASET INFORMATION:
{data_info}

USER QUERY:
{query}

{mode_instructions}

--- GENERAL GUIDELINES ---
- CRITICAL: ONLY use columns that EXACTLY match those listed in the DATASET INFORMATION section. Do not invent, rename, or assume any columns.
- When generating JSON, ensure it is valid and strictly follows the specified format for the given mode.
- Ensure all necessary components (preprocessing, aggregation, post_aggregation, visualization_params/analysis_params) are included as needed for the request.
"""

    def _is_greeting_or_casual_message(self, query: str) -> bool:
        """Detect if the query is a greeting or casual message not related to data analysis."""
        # Convert to lowercase for case-insensitive matching
        query_lower = query.lower().strip()
        
        # Common greeting patterns
        greeting_patterns = [
            r'^hi\b', r'^hello\b', r'^hey\b', r'^greetings\b', 
            r'^good morning\b', r'^good afternoon\b', r'^good evening\b',
            r'^how are you\b', r'^how\'s it going\b', r'^what\'s up\b',
            r'^how was your day\b', r'^how is your day\b'
        ]
        
        # Check if query matches any greeting pattern
        for pattern in greeting_patterns:
            if re.search(pattern, query_lower):
                return True
                
        # Check for very short queries that are likely not data-related
        if len(query_lower.split()) <= 3 and not any(data_term in query_lower for data_term in 
                                                    ['data', 'profit', 'sales', 'total', 'customer', 'country', 'column']):
            return True
            
        return False

    def process_query(self, query: str, mode: Literal["informational", "visualization", "sql", "code_execution"]) -> Dict[str, Any]:
        try:
            # Check if the query is a greeting or casual message
            if self._is_greeting_or_casual_message(query):
                return {"success": True, "message": "Hello! How can I help you with your data today?"}
            
            data_info = self.data_processor.get_column_info()
            
            # Selects the appropriate instructions based on the mode
            if mode == "informational":
                mode_instructions = self.informational_instructions
            elif mode == "visualization":
                mode_instructions = self.visualization_instructions
            elif mode == "sql":
                mode_instructions = self.sql_instructions
            elif mode == "code_execution":
                mode_instructions = self.code_generation_instructions
            else:
                return {"success": False, "message": f"Unsupported mode: {mode}", "visualization": None}
            
            final_prompt = self.base_template.format(
                data_info=data_info,
                query=query,
                mode_instructions=mode_instructions
            )
            
            response = self.llm.invoke(final_prompt)
            response_text = self._extract_response_text(response)
            
            # Handle SQL and Code Generation mode differently since it doesn't use JSON
            if mode == "code_execution":
                # The response is the raw code, so just cleaning it up
                cleaned_code = self._clean_code_response(response_text)
                return {"success": True, "message": cleaned_code}
            
            if mode == "sql":
                return self._handle_sql_request(response_text)
                
            parsed_plan = self._extract_json_plan(response_text)

            if parsed_plan:
                response_type = parsed_plan.get("response_type")
                if response_type == "visualization" and mode == "visualization":
                    return self._handle_visualization_request(parsed_plan)
                elif response_type == "analysis" and mode == "informational":
                    return self._handle_analysis_request(parsed_plan, query)
                else:
                    print(f"Warning: JSON response type '{response_type}' mismatch or unexpected for mode '{mode}'.")
                    return {"success": True, "message": self._clean_response(response_text), "visualization": None}
            else:
                if mode == "informational":
                    return {"success": True, "message": self._clean_response(response_text), "visualization": None}
                else:
                    print(f"Warning: Expected JSON in visualization mode, got plain text.")
                    return {"success": False, "message": f"Expected JSON plan, got: {self._clean_response(response_text)}", "visualization": None}

        except Exception as e:
            print(f"Error processing query: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error processing query: {str(e)}", "visualization": None}

    def _handle_sql_request(self, response_text: str) -> Dict[str, Any]:
        """Handle SQL query generation requests."""
        try:
            # Extract SQL query from response
            sql_match = re.search(r"```sql\n(.*?)\n```", response_text, re.DOTALL)
            
            if sql_match:
                sql_query = sql_match.group(1).strip()
                
                # Extract explanation (everything after the SQL code block)
                explanation = re.sub(r".*?```sql.*?```", "", response_text, flags=re.DOTALL).strip()
                
                # Validate that SQL only uses columns from the dataset
                if self.data_processor.dataframe is not None:
                    actual_columns = set(self.data_processor.dataframe.columns)
                    # Simple regex to extract column names from SQL (not perfect but catches most cases)
                    potential_columns = re.findall(r'(?:SELECT|WHERE|GROUP BY|ORDER BY|HAVING)\s+([^,;()]+)', sql_query, re.IGNORECASE)
                    for col_ref in potential_columns:
                        # Clean up the column reference
                        col_parts = col_ref.strip().split()
                        for part in col_parts:
                            # Skip SQL keywords, functions, and aliases
                            if (part.upper() in ['AS', 'FROM', 'AND', 'OR', 'ON', 'BY', 'DESC', 'ASC'] or 
                                part.upper().startswith(('SUM', 'AVG', 'COUNT', 'MIN', 'MAX')) or
                                part == '*'):
                                continue
                            # Check if this might be a column name
                            if part not in actual_columns and not part.isdigit():
                                print(f"Warning: Potential invalid column '{part}' in SQL query")
                
                return {
                    "success": True, 
                    "message": sql_query,
                    "explanation": explanation,
                    "visualization": None
                }
            else:
                # If no SQL code block found, return the whole response as the SQL query
                return {
                    "success": True, 
                    "message": response_text.strip(),
                    "visualization": None
                }
        except Exception as e:
            print(f"Error handling SQL request: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error generating SQL query: {str(e)}", "visualization": None}

    def _extract_response_text(self, response: Any) -> str:
        if hasattr(response, 'content'): return response.content
        # if isinstance(response, dict) and 'text' in response: return response['text']
        return str(response)

    def _extract_json_plan(self, response_text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"```json\n(\{.*?\})\n```", response_text, re.DOTALL)
        json_str = match.group(1) if match else response_text.strip()
        if not (json_str.startswith("{") and json_str.endswith("}")):
            return None
        try:
            return json.loads(json_str.replace("\n", ""))
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e} for string: {json_str}")
            return None

    def _clean_response(self, text: str) -> str:
        text = re.sub(r"```json\n\{.*?\}\n```", "", text, flags=re.DOTALL)
        text = re.sub(r"^\s*\{.*?\}\s*$", "", text, flags=re.DOTALL | re.MULTILINE)
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def _clean_code_response(self, text: str) -> str:
        """Cleans the response to extract only the raw Python code."""
        match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback for cases where markdown is missing
        return text.strip()

    def _handle_visualization_request(self, viz_plan: Dict[str, Any]) -> Dict[str, Any]:
        try:
            current_df = self.data_processor.get_data()
            if current_df is None: 
                return {"success": False, "message": "No data loaded for visualization.", "visualization": None}

            # Apply preprocessing if specified
            preprocessing_steps = viz_plan.get("preprocessing")
            if preprocessing_steps:
                print(f"Applying preprocessing: {preprocessing_steps}")
                current_df = self.data_processor.preprocess_data(list(preprocessing_steps), df_input=current_df.copy())
            
            # Apply aggregation if specified
            aggregation_plan = viz_plan.get("aggregation")
            df_to_visualize = current_df
            if aggregation_plan:
                group_by = aggregation_plan.get("group_by")
                agg_specs_llm = aggregation_plan.get("agg_specs")
                if group_by is not None and agg_specs_llm:
                    processed_agg_specs = self._process_llm_agg_specs(agg_specs_llm)
                    if processed_agg_specs:
                        print(f"Applying aggregation: group by {group_by}, specs {processed_agg_specs}")
                        try:
                            df_to_visualize = self.data_processor.aggregate_data(
                                group_by_columns=group_by, 
                                agg_specs=processed_agg_specs, 
                                df=current_df.copy()
                            )
                            print("Aggregation successful.")
                        except Exception as agg_error:
                            print(f"Error during aggregation: {str(agg_error)}")
                            return {"success": False, "message": f"Error during aggregation: {str(agg_error)}", "visualization": None}
                    else: 
                        print("Warning: No valid aggregation specs for visualization. Skipping aggregation.")
                else: 
                    print("Warning: Aggregation plan missing 'group_by' or 'agg_specs'. Skipping.")
            
            # Validate visualization parameters
            viz_params_plan = viz_plan.get("visualization_params")
            if not viz_params_plan: 
                return {"success": False, "message": "Missing 'visualization_params'.", "visualization": None}

            # Verify that columns specified in visualization parameters exist
            available_cols = list(df_to_visualize.columns)
            for col_key in ["x", "y", "color", "z"]:
                col_val = viz_params_plan.get(col_key)
                if col_val and col_val not in available_cols:
                    if col_key == "color": 
                        print(f"Warning: Color column '{col_val}' not found. Ignoring.")
                        viz_params_plan[col_key] = None
                    else: 
                        return {"success": False, "message": f"Column '{col_val}' for '{col_key}' not in available data: {available_cols}", "visualization": None}
            
            # Create visualization
            viz_params = {
                "viz_type": viz_params_plan.get("viz_type", "bar"),
                "df": df_to_visualize,
                "x": viz_params_plan.get("x"),
                "y": viz_params_plan.get("y"),
                "color": viz_params_plan.get("color"),
                "title": viz_params_plan.get("title", "Visualization"),
                "z": viz_params_plan.get("z") # Pass z param for heatmap
            }
            visualization = self.visualizer.create_visualization(**viz_params)
            explanation = f"Created {viz_params['viz_type']} chart: {viz_params['title']}."
            return {"success": True, "message": explanation, "visualization": visualization}
        except Exception as e:
            print(f"Error in _handle_visualization_request: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error creating visualization: {str(e)}", "visualization": None}

    def _handle_analysis_request(self, analysis_plan: Dict[str, Any], query: str) -> Dict[str, Any]:
        try:
            df = self.data_processor.get_data()
            if df is None: 
                return {"success": False, "message": "No data loaded for analysis.", "visualization": None}
            
            current_df = df.copy()

            # Normalize and Apply Filters 
            filters_from_plan = analysis_plan.get("filters", [])
            normalized_filters = self._normalize_filters(filters_from_plan)
            
            if normalized_filters:
                print(f"Applying normalized filters: {normalized_filters}")
                try:
                    current_df = self.data_processor.filter_data(normalized_filters, df=current_df)
                    print(f"Shape after filtering: {current_df.shape}")
                except Exception as filter_error:
                    print(f"Error during filtering: {str(filter_error)}")
                    return {"success": False, "message": f"Error filtering data: {str(filter_error)}", "visualization": None}
            elif filters_from_plan:  # If there was a filter plan but none were valid after normalization
                print(f"No valid filters to apply after normalization. Original filter plan was: {filters_from_plan}")

            # Apply Aggregation 
            aggregation_plan = analysis_plan.get("aggregation")
            if aggregation_plan:
                # Default to empty list for group_by if not provided (for total calculations)
                group_by = aggregation_plan.get("group_by", [])
                agg_specs_llm = aggregation_plan.get("agg_specs")
                
                if agg_specs_llm:
                    processed_agg_specs = self._process_llm_agg_specs(agg_specs_llm)
                    if processed_agg_specs:
                        print(f"Applying aggregation: group by {group_by}, specs {processed_agg_specs}")
                        try:
                            current_df = self.data_processor.aggregate_data(
                                group_by_columns=group_by, 
                                agg_specs=processed_agg_specs, 
                                df=current_df
                            )
                            print("Aggregation successful.")
                        except Exception as agg_error:
                            print(f"Error during aggregation: {str(agg_error)}")
                            return {"success": False, "message": f"Error during aggregation: {str(agg_error)}", "visualization": None}
                    else:
                        print("Warning: No valid aggregation specs. Skipping aggregation.")
                else:
                    print("Warning: Aggregation plan missing 'agg_specs'. Skipping.")

            # Apply Post-Aggregation Calculations
            post_aggregation_plan = analysis_plan.get("post_aggregation")
            if post_aggregation_plan and isinstance(post_aggregation_plan, dict):
                calculations = post_aggregation_plan.get("calculations")
                if calculations and isinstance(calculations, list):
                    print(f"Applying post-aggregation calculations: {calculations}")
                    for calc in calculations:
                        if isinstance(calc, dict) and "name" in calc and "formula" in calc:
                            col_name = calc["name"]
                            formula = calc["formula"]
                            parts = re.match(r"\s*([\w.\s]+)\s*([/*+-])\s*([\w.\s]+)\s*", formula)  # Allow spaces and dots in column names
                            if parts:
                                op1_col, operator, op2_col = map(str.strip, parts.groups())  # Strip spaces from matched column names
                                if op1_col in current_df.columns and op2_col in current_df.columns:
                                    try:
                                        op1 = pd.to_numeric(current_df[op1_col], errors='coerce')
                                        op2 = pd.to_numeric(current_df[op2_col], errors='coerce')
                                        if operator == '/':
                                            current_df[col_name] = op1.div(op2).replace([float('inf'), -float('inf')], pd.NA)
                                        elif operator == '*':
                                            current_df[col_name] = op1 * op2
                                        elif operator == '+':
                                            current_df[col_name] = op1 + op2
                                        elif operator == '-':
                                            current_df[col_name] = op1 - op2
                                        else:
                                            print(f"Warning: Unsupported operator '{operator}' in formula '{formula}'. Skipping calculation.")
                                    except Exception as calc_error:
                                        print(f"Error during calculation '{formula}': {str(calc_error)}")
                                else:
                                    print(f"Warning: One or both columns in formula '{formula}' not found in data. Skipping calculation.")
                            else:
                                print(f"Warning: Could not parse formula '{formula}'. Skipping calculation.")
                        else:
                            print(f"Warning: Invalid calculation specification: {calc}. Skipping calculation.")

            # Apply Sorting
            sort_plan = analysis_plan.get("sort_by")
            if sort_plan and isinstance(sort_plan, dict):
                sort_col = sort_plan.get("column")
                ascending = sort_plan.get("ascending", False)
                if sort_col:
                    if sort_col in current_df.columns:
                        print(f"Sorting by {sort_col} (ascending={ascending})")
                        try:
                            current_df = current_df.sort_values(by=sort_col, ascending=ascending)
                        except Exception as sort_error:
                            print(f"Error during sorting: {str(sort_error)}")
                    else:
                        print(f"Warning: Sort column '{sort_col}' not found in processed data. Skipping sorting.")

            # Apply Limit
            limit_val = analysis_plan.get("limit")
            if limit_val is not None:
                try:
                    limit_val = int(limit_val)
                    if limit_val > 0:
                        print(f"Applying limit: {limit_val}")
                        current_df = current_df.head(limit_val)
                    else:
                        print(f"Warning: Invalid limit value: {limit_val}. Must be positive. Skipping limit.")
                except (ValueError, TypeError):
                    print(f"Warning: Invalid limit value '{limit_val}'. Must be an integer. Skipping limit.")
            
            # Generate Summary Text
            summary_prompt_template = """
Based on the user's query: '{user_query}'
And the following data result:
{data_result_string}

Generate a concise, direct natural language sentence summarizing this specific result in response to the original query. 
Focus on the data. Do not mention the process of analysis.
Example for 'Which customer ordered the most items?': 'Customer [Customer Name/ID] ordered the most items with a total of [Quantity] items.'
Example for 'What is the total profit for Canada?': 'The total profit for Canada is [Total Profit].'
"""
            
            data_result_str_for_summary = current_df.to_string(index=True, max_rows=10)  # Provide a sample for summary
            
            summary_generation_prompt = summary_prompt_template.format(
                user_query=query,
                data_result_string=data_result_str_for_summary
            )

            summary_response = self.llm.invoke(summary_generation_prompt)
            generated_summary_text = self._extract_response_text(summary_response).strip()

            if not generated_summary_text:
                print("Warning: LLM did not generate a summary text. Using a default message.")
                generated_summary_text = "The analysis is complete. Please see the detailed data below."
            
            print("Debug - Generated summary:")
            print(current_df.to_string(index=True))
            
            return {
                "success": True, 
                "message": generated_summary_text, 
                "data": current_df.to_dict(orient='records'), 
                "visualization": None
            }

        except Exception as e:
            print(f"Error handling analysis request: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"An unexpected error occurred during analysis: {str(e)}", "visualization": None}

    def _process_llm_agg_specs(self, agg_specs_llm: Dict[str, Any]) -> Dict[str, Any]:
        """Process aggregation specifications from LLM response into the format expected by data_processor
        
        Args:
            agg_specs_llm: Dictionary from LLM with output column names as keys and specs as values
            
        Returns:
            Dictionary mapping output column names to (source_column, agg_function) tuples
        """
        processed_specs = {}
        
        if not isinstance(agg_specs_llm, dict):
            print(f"Warning: LLM agg_specs is not a dictionary: {agg_specs_llm}. Skipping.")
            return processed_specs
            
        for output_col, spec in agg_specs_llm.items():
            # Handle the case where spec is a dictionary with agg_func and source_column
            if isinstance(spec, dict) and "agg_func" in spec and "source_column" in spec:
                source_col = spec["source_column"]
                agg_func = spec["agg_func"].lower()
                
                # Verify the column exists
                if source_col in self.data_processor.get_column_names():
                    processed_specs[output_col] = (source_col, agg_func)
                else:
                    print(f"Warning: Source column '{source_col}' not found in dataset. Skipping '{output_col}'.")
            else:
                print(f"Warning: Invalid format for aggregation spec item '{output_col}': {spec}. Skipping.")
                
        return processed_specs

    def _normalize_filters(self, filters_from_plan):
        """Normalize filter specifications from LLM response
        
        Args:
            filters_from_plan: List or dict of filter specifications from LLM
            
        Returns:
            List of normalized filter dictionaries
        """
        normalized_filters = []
        
        if not filters_from_plan:
            return normalized_filters
            
        # Ensure filters_from_plan is a list
        if not isinstance(filters_from_plan, list):
            if isinstance(filters_from_plan, dict):
                filters_from_plan = [filters_from_plan]
            else:
                print(f"Warning: 'filters' in plan is not a list or dict: {filters_from_plan}. Skipping all filters.")
                return normalized_filters
        
        for f_item in filters_from_plan:
            if isinstance(f_item, dict) and all(k in f_item for k in ["column", "operator", "value"]):
                normalized_filters.append(f_item)
            else:
                print(f"Warning: Invalid filter item format: {f_item}. Skipping this filter item.")
                
        return normalized_filters