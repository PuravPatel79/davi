import os
import sys
from dotenv import load_dotenv
import webbrowser
from src.data_processor import DataProcessor
from src.visualizer import Visualizer
from src.agent import DataAnalysisAgent

# Load environment variables from .env file if it exists
load_dotenv()

def display_menu():
    """Displays the main menu options to the user."""
    print("\n-----------------------------------")
    print("Main Menu")
    print("-----------------------------------")
    print("What would you like to do?")
    print("1. Ask informational questions about the data")
    print("2. Request data visualizations")
    print("3. Exit")
    print("-----------------------------------")

def handle_informational_queries(agent):
    """Handles the sub-menu loop for informational queries."""
    print("\n--- Informational Query Mode ---")
    print("Type your questions below. Type exactly 'back' to return to the main menu.")
    while True:
        query = input("\nEnter your informational query (or 'back'): ")
        if query.strip().lower() == 'back':
            break  # Exit informational sub-loop

        print("\nProcessing your query...")
        result = agent.process_query(query)
        
        # Display result
        if result.get("success", False):
            print("\nResult:")
            print(result["message"])
            # Check if a visualization was unexpectedly created
            if result.get("visualization") is not None:
                print("\nNote: A visualization was generated unexpectedly.")
        else:
            print("\nError:")
            print(result.get("message", "Unknown error occurred"))

def handle_visualization_requests(agent):
    """Handles the sub-menu loop for visualization requests."""
    print("\n--- Visualization Request Mode ---")
    print("Type your requests below. Type exactly 'back' to return to the main menu.")
    while True:
        query = input("\nEnter your visualization request (or 'back'): ")
        if query.strip().lower() == 'back':
            break  # Exit visualization sub-loop

        print("\nProcessing your visualization request...")
        result = agent.process_query(query)
        
        # Display result and visualization
        if result.get("success", False):
            print("\nAnalysis Result:")
            print(result["message"])
            
            # Display visualization if created
            if result.get("visualization") is not None and hasattr(result["visualization"], "write_html"):
                print("\nGenerating visualization...")
                output_file = "visualization.html"
                try:
                    result["visualization"].write_html(output_file)
                    print(f"Visualization saved to {output_file}")
                    # Try to open in browser
                    try:
                        webbrowser.open('file://' + os.path.realpath(output_file))
                        print("Visualization opened in browser.")
                    except Exception as wb_error:
                        print(f"Could not open browser automatically: {wb_error}")
                        print(f"Please open {output_file} manually.")
                except Exception as write_error:
                    print(f"Error saving visualization: {write_error}")
            else:
                print("\nNo visualization was generated for this request.")
        else:
            print("\nError:")
            print(result.get("message", "Unknown error occurred"))

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
    except Exception as e:
        print(f"An unexpected error occurred during agent initialization: {str(e)}")
        return
    
    # Example usage
    print("AI Data Analysis Agent")
    print("=====================")
    
    # Load data
    data_path = input("Enter path to your data file (CSV or Excel) or URL: ")
    try:
        data_processor.load_data(data_path)
        print(f"Data loaded successfully. Shape: {data_processor.metadata['shape']}")
        print("\nColumn information:")
        print(data_processor.get_column_info())
    except FileNotFoundError:
        print(f"Error: File not found at {data_path}")
        return
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return
    
    # Interactive menu loop
    while True:
        display_menu()
        choice = input("Enter your choice (1, 2, or 3): ")

        if choice == '1':
            handle_informational_queries(agent)
        elif choice == '2':
            handle_visualization_requests(agent)
        elif choice == '3':
            print("Exiting. Davi says Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()