# backend/app.py
import json
import sys
import os
import uuid
import redis
import pandas as pd
import pickle
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import plotly.graph_objects as go

# --- More robust path handling ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(BASE_DIR, 'src'))

# --- Import all necessary classes ---
from agent import DataAnalysisAgent
from data_processor import DataProcessor
from visualizer import Visualizer

load_dotenv(os.path.join(BASE_DIR, '.env'))

app = Flask(__name__)
CORS(app)

# --- Connect to Redis ---
try:
    # Read the Redis host from an environment variable. Enables us to launch the app in multiple ways.
    # Default to 'localhost' if the variable is not set (for AWS ECS).
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    
    redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=False)
    redis_client.ping()
    print(f"Successfully connected to Redis at {redis_host}.")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None


@app.route('/')
def home():
    return "Hello, World! This is the davi API."

@app.route('/load', methods=['POST'])
def load():
    if not redis_client:
        return jsonify({"error": "Cannot connect to Redis cache. Please check server configuration."}), 503

    data = request.get_json()
    if not data or 'dataset_url' not in data:
        return jsonify({"error": "Missing 'dataset_url' in request body"}), 400

    dataset_url = data['dataset_url']
    if not dataset_url:
        return jsonify({"error": "Dataset URL cannot be empty."}), 400

    try:
        data_processor = DataProcessor()
        data_processor.load_data(dataset_url)
        dataframe = data_processor.dataframe

        session_id = str(uuid.uuid4())
        
        serialized_df = pickle.dumps(dataframe)
        redis_client.setex(session_id, 3600, serialized_df)

        data_info = data_processor.get_column_info()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "data_info": data_info,
            "message": f"Successfully loaded data with {dataframe.shape[0]} rows and {dataframe.shape[1]} columns."
        })

    except Exception as e:
        print(f"Failed to load data from URL: {dataset_url}. Error: {e}")
        return jsonify({"error": f"Could not load data from the provided URL. Please check the link and ensure it is a valid CSV/Excel file."}), 400

@app.route('/analyze', methods=['POST'])
def analyze():
    if not redis_client:
        return jsonify({"error": "Cannot connect to Redis cache. Please check server configuration."}), 503
        
    data = request.get_json()
    if not data or 'query' not in data or 'session_id' not in data:
        return jsonify({"error": "Missing 'query' or 'session_id' in request body"}), 400

    user_query = data['query']
    session_id = data['session_id']
    mode = data.get('mode', 'informational')

    serialized_df = redis_client.get(session_id)
    if serialized_df is None:
        return jsonify({"error": "Invalid or expired session. Please load your data again."}), 400

    try:
        dataframe = pickle.loads(serialized_df)

        data_processor = DataProcessor()
        data_processor.dataframe = dataframe
        data_processor._extract_metadata() 
        
        visualizer = Visualizer(data_processor)
        agent = DataAnalysisAgent(data_processor, visualizer)
        
        result = agent.process_query(user_query, mode=mode)

        if result and result.get("visualization"):
            fig = result["visualization"]
            result["visualization"] = fig.to_json()

        if result and result.get("success"):
            return jsonify(result)
        else:
            error_message = result.get("message", "An unknown error occurred in the agent.")
            return jsonify({"error": error_message}), 500

    except Exception as e:
        print(f"An error occurred in /analyze endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True)