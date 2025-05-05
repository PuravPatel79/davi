import os
import json
import re
import traceback
from typing import Dict, Any, List, Optional, Union, Literal
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
# Removed LLMChain and PromptTemplate as we'll format dynamically

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

        # --- Mode-Specific Instructions --- 
        self.informational_instructions = """
INSTRUCTIONS:
- Analyze the user query based on the dataset information.
- If the query requires calculations (like finding the customer with the most items, summing quantities, counting orders), respond ONLY with a JSON object in this format:
```json
{{
  "response_type": "analysis",
  "filters": [
      {{"column": "column_name", "operator": "operator_symbol", "value": "value_to_filter"}}
      // Supported operators: ==, !=, >, <, >=, <=, isin (value must be a list for isin)
  ],
  "aggregation": {{
    "group_by": ["group_column1"],
    "agg_specs": {{ "OutputColumnName": {{ "agg_func": "sum|mean|count|...", "source_column": "ExactColumnNameFromDataset" }} }} 
    // For agg_func 'size', source_column is not needed. e.g., {{"OrderCount": {{"agg_func": "size"}}}}
    // Example: {{ "TotalQuantity": {{ "agg_func": "sum", "source_column": "OrderQuantity" }} }}
  }},
  "sort_by": {{ "column": "OutputColumnName", "ascending": false }}, // Sort by the new aggregated column name
  "limit": 1 // Optional: number of top results to return
}}
```
- For simple informational requests (like column names, row count) or if you cannot perform the calculation/analysis yourself, provide a clear, concise answer in plain text.
- **IMPORTANT: Do NOT generate a plan for data visualization in this mode.**
"""

        self.visualization_instructions = """
INSTRUCTIONS:
- Analyze the user query based on the dataset information.
- Generate ONLY a JSON object describing the necessary data preprocessing (if any), aggregation (if any), and visualization parameters needed to create the requested visualization. Use this format:
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
- **IMPORTANT: Only output the JSON block, nothing else.**
"""

        # --- Base Prompt Structure --- 
        self.base_template = """
You are an expert data analyst assistant. Your task is to analyze the following dataset and respond to the user's query based on the provided instructions.

DATASET INFORMATION:
{data_info}

USER QUERY:
{query}

{mode_instructions}

--- GENERAL GUIDELINES ---
- Only use columns that actually exist in the dataset information provided.
- When generating JSON, ensure it is valid and strictly follows the specified format for the given mode.
- Ensure all necessary components (preprocessing, aggregation, visualization_params/analysis_params) are included as needed for the request.
"""

    # Modified process_query to accept mode
    def process_query(self, query: str, mode: Literal["informational", "visualization"]) -> Dict[str, Any]:
        """Process any data-related query based on the specified mode and return appropriate results"""
        try:
            # Get data info
            data_info = self.data_processor.get_column_info()

            # Select instructions based on mode
            if mode == "informational":
                mode_instructions = self.informational_instructions
            elif mode == "visualization":
                mode_instructions = self.visualization_instructions
            else:
                # Default or error case - maybe default to informational?
                print(f"Warning: Invalid mode 	{mode}	 specified. Defaulting to informational.")
                mode_instructions = self.informational_instructions
                mode = "informational" # Correct the mode variable for later logic

            # Format the final prompt string
            final_prompt = self.base_template.format(
                data_info=data_info,
                query=query,
                mode_instructions=mode_instructions
            )
            
            # Call the LLM directly with the formatted prompt
            response = self.llm.invoke(final_prompt)
            response_text = self._extract_response_text(response)

            # Attempt to parse the response as JSON
            parsed_plan = self._extract_json_plan(response_text)

            if parsed_plan:
                response_type = parsed_plan.get("response_type")
                # Check if the response type matches the requested mode
                if response_type == "visualization" and mode == "visualization":
                    return self._handle_visualization_request(parsed_plan)
                elif response_type == "analysis" and mode == "informational":
                    return self._handle_analysis_request(parsed_plan, query, mode)
                else:
                    # Mismatch between mode and response type, or unexpected type
                    print(f"Warning: Received JSON response type 	{response_type}	 which does not match requested mode 	{mode}	 or is unexpected.")
                    # Treat as plain text, cleaning out the JSON
                    return {"success": True, "message": self._clean_response(response_text), "visualization": None}
            else:
                # If no valid JSON found, treat as a plain text response
                # This is expected for simple informational queries in informational mode
                if mode == "informational":
                     return {"success": True, "message": self._clean_response(response_text), "visualization": None}
                else: # Should have received JSON in visualization mode
                     print(f"Warning: Expected a JSON response in visualization mode, but received plain text.")
                     return {"success": False, "message": f"Expected a JSON plan for visualization, but received: {self._clean_response(response_text)}", "visualization": None}

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
            # Fallback to finding any JSON-like structure that spans most of the response
            # Avoid matching small JSON snippets within a larger text response
            if response_text.strip().startswith("{") and response_text.strip().endswith("}"):
                 json_str = response_text.strip()
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
                 return "Received a JSON response, but it wasn't in the expected format for this mode."
             except json.JSONDecodeError:
                 pass # Not valid JSON, proceed with cleaning

        # Remove any JSON blocks within markdown
        text = re.sub(r"```json\n\{.*?\}\n```", "", text, flags=re.DOTALL)
        # Remove any standalone JSON blocks that might have been missed
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

    def _handle_analysis_request(self, analysis_plan: Dict[str, Any], query: str, mode: str) -> Dict[str, Any]:
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
            df_before_agg = df.copy() # Save state before aggregation attempt
            if aggregation_plan and isinstance(aggregation_plan, dict):
                group_by = aggregation_plan.get("group_by")
                agg_specs = aggregation_plan.get("agg_specs")
                if group_by and agg_specs:
                    print(f"Applying aggregation: group by {group_by}, specs {agg_specs}")
                    try:
                        # Transform agg_specs from LLM format to a format data_processor expects
                        # Expected LLM format: { "OutputName": { "agg_func": "sum", "source_column": "SourceColumn" } } or { "CountName": { "agg_func": "size" } }
                        # Target format for data_processor: { "OutputName": {"source": "SourceColumn", "func": "sum"} } or { "CountName": "size" }
                        processed_agg_specs = {}
                        for output_col, spec_dict in agg_specs.items():
                            if isinstance(spec_dict, dict):
                                agg_func = spec_dict.get("agg_func")
                                if not agg_func:
                                    print(f"Warning: Aggregation spec for 	{output_col}	 is missing 	agg_func	. Skipping.")
                                    continue
                                
                                agg_func_lower = agg_func.lower()
                                if agg_func_lower == 'size':
                                    processed_agg_specs[output_col] = 'size'
                                else:
                                    source_col = spec_dict.get("source_column")
                                    if not source_col:
                                        print(f"Warning: Aggregation spec for 	{output_col}	 (	{agg_func}	) is missing 	 source_column	. Skipping.")
                                        continue
                                    processed_agg_specs[output_col] = {'source': source_col, 'func': agg_func_lower}
                            else:
                                print(f"Warning: Invalid format for aggregation spec 	{output_col}	. Expected a dictionary. Skipping.")

                        if not processed_agg_specs:
                            print("Warning: No valid aggregation specs found after parsing. Skipping aggregation.")
                        else:
                            print(f"Processed aggregation specs for data_processor: {processed_agg_specs}")
                            # Pass the processed specs to the data processor
                            df = self.data_processor.aggregate_data(df=df, group_by_columns=group_by, agg_specs=processed_agg_specs)
                            print("Aggregation successful.")
                            
                    except ValueError as agg_ve:
                        # Check if it's the specific source column error from data_processor
                        error_message = str(agg_ve)
                        if "Source column" in error_message and "not found in dataframe" in error_message:
                            print(f"Aggregation failed due to missing source column: {error_message}")
                            print("Attempting LLM self-correction...")
                            
                            # Construct correction prompt
                            correction_prompt = f"""
                            The previous attempt to execute the data analysis plan failed during aggregation with this error:
                            `{error_message}`
                            
                            The original user query was: `{query}`
                            The dataset columns are: {self.data_processor.metadata.get("columns", [])}
                            The previous JSON plan was:
                            ```json
                            {json.dumps(analysis_plan, indent=2)}
                            ```
                            
                            Please provide a corrected JSON plan. Pay close attention to the `source_column` within the `agg_specs` to ensure it matches an existing column from the list above, based on the original query intent. Respond ONLY with the corrected JSON object.
                            """
                            
                            try:
                                corrected_plan_str = self._get_llm_plan(correction_prompt, mode) # Use original mode
                                corrected_plan = self._parse_llm_response(corrected_plan_str)
                                
                                if corrected_plan and corrected_plan.get("response_type") == "analysis":
                                    print("Received corrected plan from LLM. Retrying aggregation...")
                                    # Extract corrected aggregation specs
                                    corrected_aggregation_plan = corrected_plan.get("aggregation")
                                    if corrected_aggregation_plan and isinstance(corrected_aggregation_plan, dict):
                                        corrected_agg_specs_raw = corrected_aggregation_plan.get("agg_specs")
                                        if corrected_agg_specs_raw:
                                            # Reprocess the corrected specs
                                            corrected_processed_specs = {}
                                            for output_col, spec_dict in corrected_agg_specs_raw.items():
                                                # (Same parsing logic as before)
                                                if isinstance(spec_dict, dict):
                                                    agg_func = spec_dict.get("agg_func")
                                                    if not agg_func: continue
                                                    agg_func_lower = agg_func.lower()
                                                    if agg_func_lower == 'size':
                                                        corrected_processed_specs[output_col] = 'size'
                                                    else:
                                                        source_col = spec_dict.get("source_column")
                                                        if not source_col: continue
                                                        corrected_processed_specs[output_col] = {"source": source_col, "func": agg_func_lower}
                                                # else: skip invalid format
                                            
                                            if corrected_processed_specs:
                                                print(f"Processed corrected specs: {corrected_processed_specs}")
                                                # Retry aggregation with corrected specs
                                                df = self.data_processor.aggregate_data(df=df_before_agg, group_by_columns=group_by, agg_specs=corrected_processed_specs)
                                                print("Aggregation successful after self-correction.")
                                                # Continue with sorting, limit etc. - need to restructure flow slightly or use flags
                                                # For now, let's assume success means we can proceed past the except block
                                                # We might need to re-apply sorting/limit if they were defined in the corrected plan too
                                                # Let's just break out of the except block for now if successful
                                                pass # Continue execution after the except block
                                            else:
                                                 raise ValueError("LLM self-correction provided invalid or empty agg_specs.")
                                        else:
                                            raise ValueError("LLM self-correction plan missing agg_specs.")
                                    else:
                                         # If no aggregation in corrected plan, maybe it decided it wasn't needed?
                                         # For now, treat as failure to correct aggregation.
                                         raise ValueError("LLM self-correction plan missing aggregation section.")
                                else:
                                    raise ValueError("LLM self-correction did not return a valid analysis JSON plan.")

                            except Exception as correction_e:
                                print(f"LLM self-correction failed: {str(correction_e)}")
                                traceback.print_exc()
                                
                                # --- User Clarification Fallback ---
                                user_clarification_text = (
                                    f"I encountered an issue while trying to aggregate the data for your query: 	{query}	\n"
                                    f"The initial error was: 	{error_message}	\n"
                                    f"I asked the AI to correct the plan, but that also failed with error: 	{str(correction_e)}	\n\n"
                                    f"The available columns are: {self.data_processor.metadata.get("columns", [])}\n\n"
                                    f"Could you please specify which column should be used for the aggregation (e.g., sum, count)? Or perhaps rephrase your query to be more specific about the column names?"
                                )
                                
                                # Ask the user for clarification. We cannot directly use the response here,
                                # so we ask them to re-query.
                                # In a more advanced setup, we might store state and handle the response.
                                return {"success": False, "message": user_clarification_text, "visualization": None, "ask_user": True} # Add a flag to indicate we need user input
                        else:
                            # It was a different ValueError, re-raise or handle differently
                            print(f"Non-source-column ValueError during aggregation: {error_message}")
                            traceback.print_exc()
                            return {"success": False, "message": f"Error during aggregation: {error_message}", "visualization": None}
                            
                    except Exception as agg_e: # Catch other non-ValueError exceptions during initial aggregation
                        print(f"General error during aggregation: {str(agg_e)}")
                        traceback.print_exc()
                        return {"success": False, "message": f"Error during aggregation: {str(agg_e)}", "visualization": None}
                else:
                    print("Warning: Aggregation plan found but missing 'group_by' or 'agg_specs'. Skipping aggregation.")
            
            # --- 3. Apply Sorting --- 
            sort_plan = analysis_plan.get("sort_by")
            if sort_plan and isinstance(sort_plan, dict):
                sort_col = sort_plan.get("column")
                ascending = sort_plan.get("ascending", True)
                if sort_col and sort_col in df.columns:
                    print(f"Sorting by {sort_col}, ascending={ascending}")
                    try:
                        df = df.sort_values(by=sort_col, ascending=ascending)
                    except Exception as sort_e:
                        return {"success": False, "message": f"Error during sorting: {str(sort_e)}", "visualization": None}
                else:
                    print(f"Warning: Sort column '{sort_col}' not found or not specified. Skipping sorting.")

            # --- 4. Apply Limit --- 
            limit = analysis_plan.get("limit")
            if limit and isinstance(limit, int) and limit > 0:
                print(f"Applying limit: {limit}")
                df = df.head(limit)

            # --- 5. Format Result --- 
            # Convert the resulting dataframe (or relevant parts) to a string message
            if df.empty:
                message = "The analysis resulted in no data matching the criteria."
            else:
                # Provide a summary or the full data if small
                if len(df) <= 10:
                    message = f"Analysis Result:\n{df.to_string()}"
                else:
                    message = f"Analysis Result (first 10 rows):\n{df.head(10).to_string()}\n... ({len(df)} total rows)"
            
            return {"success": True, "message": message, "visualization": None}

        except Exception as e:
            print(f"Error handling analysis request: {str(e)}")
            traceback.print_exc()
            return {"success": False, "message": f"Error performing analysis: {str(e)}", "visualization": None}