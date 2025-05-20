# davi - Data Analyst and Visualizer

A powerful, interactive data analysis tool that combines natural language processing with advanced data analysis and visualization capabilities. Davi (Data Analyst and Visualizer) allows users to analyze data, generate visualizations, and convert natural language to SQL queries through a simple, menu-driven interface.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Informational Queries](#informational-queries)
  - [Visualization Requests](#visualization-requests)
  - [NLP to SQL Conversion](#nlp-to-sql-conversion)
- [Architecture](#architecture)
- [File Structure](#file-structure)
- [Dependencies](#dependencies)
- [Environment Variables](#environment-variables)

## Features

- **Natural Language Data Analysis**: Ask questions about your data in plain English
- **Interactive Visualizations**: Generate and view data visualizations based on natural language requests
- **Dashboard Generation**: Collect multiple visualizations in a single dashboard view
- **NLP to SQL Conversion**: Convert natural language questions into valid SQL queries
- **Flexible Data Loading**: Support for CSV, Excel files, and URLs
- **Robust Data Processing**: Filtering, aggregation, and preprocessing capabilities
- **Schema-Aware Operations**: All operations respect and validate against your data schema
- **User-Friendly Interface**: Menu-driven console interface for easy interaction

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd davi
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Google API key for Gemini:
   - Create a `.env` file in the project root directory
   - Add your Google API key: `GOOGLE_API_KEY=your_api_key_here`
   - Or set it as an environment variable: `export GOOGLE_API_KEY=your_api_key_here`

## Usage

Run the main script to start the application:
```
python main.py
```

You'll be prompted to enter the path to your data file (CSV or Excel) or a URL. For example, you can use this sample dataset:
```
https://raw.githubusercontent.com/yannie28/Global-Superstore/master/Global_Superstore(CSV).csv
```

You'll be prompted to enter the path to your data file (CSV or Excel) or a URL. After loading the data, you'll see a menu with the following options:

1. Ask informational questions about the data
2. Request data visualizations
3. Generate SQL from natural language
4. Exit

### Informational Queries

Select option 1 to ask questions about your data. Examples:

- "Calculate the total profit generated from operations in Canada."
- "Identify the customer with the highest order volume across all product categories."
- "Analyze the average transaction value segmented by geographic region."
- "Present a breakdown of the top 5 performing products by revenue contribution."
- "Summarize the dataset for me."

The agent will analyze your query, process the data accordingly, and provide a concise answer based on the actual results.

### Visualization Requests

Select option 2 to request data visualizations. Examples:

- "Generate a comparative bar chart illustrating revenue distribution across regional markets."
- "Produce a scatter plot analyzing the correlation between profit margin and order quantity."
- "Create a pie chart representation of market share distribution by product category."

After generating visualizations, you can type `show dashboard` to view all created visualizations in a single HTML dashboard that opens in your browser.

### NLP to SQL Conversion

Select option 3 to convert natural language questions into SQL queries. Examples:

- "Generate a report of cumulative profit metrics aggregated by geographical region."
- "Identify all high-value customers whose total expenditure exceeds $1000 within the current fiscal period."
- "Extract a chronological listing of all transactions originating from the Canadian market segment."
- "Perform a quantitative analysis of order frequency distributed across product categories."

The agent will generate a valid SQL query based on your question, along with an explanation of what the query does.

## Architecture 

Davi follows a modular architecture with the following components:

1. **DataAnalysisAgent**: Core component that processes user queries using LLM (Gemini)
2. **DataProcessor**: Handles data loading, filtering, aggregation, and preprocessing
3. **Visualizer**: Creates and manages data visualizations using Plotly
4. **Main Application**: Provides the user interface and coordinates the components

### Query Processing Flow

1. User inputs a query through the menu interface
2. The agent processes the query using the appropriate mode (informational, visualization, or SQL)
3. For informational queries:
   - The LLM generates a structured analysis plan
   - The data processor executes the plan (filtering, aggregation, etc.)
   - The agent generates a natural language summary of the results
4. For visualization requests:
   - The LLM generates visualization parameters
   - The visualizer creates the requested chart
   - The visualization is stored for the dashboard
5. For SQL queries:
   - The LLM converts the natural language to SQL
   - The SQL query and explanation are displayed to the user

## File Structure

- `main.py`: Entry point with menu interface and handler functions
- `src/agent.py`: Core agent implementation with LLM integration
- `src/data_processor.py`: Data loading and processing functionality
- `src/visualizer.py`: Visualization creation and management
- `.env`: Environment variables (not in repository)

## Dependencies

- **pandas**: Data manipulation and analysis
- **plotly**: Interactive visualizations
- **google-generativeai**: Google's Gemini API for LLM capabilities
- **langchain-google-genai**: LangChain integration for Gemini
- **python-dotenv**: Environment variable management
- **numpy**: Numerical operations
- **webbrowser**: Opening dashboard in browser

## Environment Variables
- `GOOGLE_API_KEY`: Required for accessing Google's Gemini API

## Advanced Features

### Filtering Capabilities

The data processor supports various filtering operations:
- Equality (`==`)
- Inequality (`!=`)
- Comparisons (`>`, `<`, `>=`, `<=`)
- List inclusion (`in`, `isin`)
- List exclusion (`not in`)

### Aggregation Functions

Supported aggregation functions:
- `sum`: Calculate the sum of values
- `mean`: Calculate the average of values
- `count`: Count the number of values
- `min`: Find the minimum value
- `max`: Find the maximum value
- `size`: Count the number of rows

### Visualization Types

The visualizer supports multiple chart types:
- Bar charts
- Line charts
- Scatter plots
- Histograms
- Pie charts
- Box plots
- Heatmaps

### Dashboard Features

The dashboard generation includes:
- Responsive layout
- Interactive Plotly charts
- Automatic browser opening
- Multiple visualizations in a single view