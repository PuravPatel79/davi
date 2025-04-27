import os
import sys
from dotenv import load_dotenv
import webbrowser
from src.data_processor import DataProcessor
from src.visualizer import Visualizer
from src.agent import DataAnalysisAgent

# Load environment variables from .env file
load_dotenv()

def main():
    # Initialize components
    data_processor = DataProcessor()
    visualizer = Visualizer(data_processor)
    
    # Get Gemini API key from environment
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    
    # Initialize agent
    try:
        agent = DataAnalysisAgent(data_processor, visualizer, gemini_api_key)
    except ValueError as e:
        print(f"Error initializing agent: {str(e)}")
        print("Please set your GOOGLE_API_KEY environment variable or create a .env file with it.")
        return
    
    # Example usage
    print("AI Agent - Davi")
    print("=====================")
    
    # Load data
    data_path = input("Enter path to your data file (CSV or Excel) or URL: ")
    try:
        data_processor.load_data(data_path)
        print(f"Data loaded successfully. Shape: {data_processor.metadata['shape']}")
        print("\nColumn information:")
        print(data_processor.get_column_info())
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return
    
    # Interactive query loop
    print("\nYou can now ask questions about your data.")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nWhat would you like to know about your data? ")
        if query.lower() == 'exit':
            break
        
        print("\nProcessing your query...")
        result = agent.process_query(query)
        
        # Check if result is a dictionary
        if isinstance(result, dict):
            if result.get("success", False):
                print("\nAnalysis Result:")
                
                print(result["message"])
                
                # Display visualization
                if "visualization" in result and result["visualization"] is not None and hasattr(result["visualization"], "write_html"):
                    print("\nGenerating visualization...")
                    # Save visualization to HTML file
                    output_file = "visualization.html"
                    result["visualization"].write_html(output_file)
                    print(f"\nVisualization saved to {output_file}")
                    
                    # Try to open in browser
                    try:
                        webbrowser.open('file://' + os.path.realpath(output_file))
                        print("Visualization opened in browser.")
                    except:
                        print(f"Please open {output_file} in your browser to view the visualization.")
            else:
                print("\nError:")
                print(result.get("message", "Unknown error occurred"))
        else:
            # If result is not a dictionary (e.g., it's a string)
            print("\nResult:")
            print(result)

if __name__ == "__main__":
    main()