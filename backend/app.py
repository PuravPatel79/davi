import json
import sys
import os
import uuid
import redis
import pandas as pd
import pickle
import io
import boto3
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
from flask_socketio import SocketIO, emit

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(BASE_DIR, 'src'))

from agent import DataAnalysisAgent
from data_processor import DataProcessor
from visualizer import Visualizer

EXECUTION_MODE = os.getenv("EXECUTION_MODE", "local")

if EXECUTION_MODE == "aws":
    from sandbox_exec_aws import SandboxExecutorAWS as SandboxExecutor
else:
    from sandbox_exec import SandboxExecutor

load_dotenv(os.path.join(BASE_DIR, '.env'))

app = Flask(__name__)
CORS(app)
# Initiaize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins="*")

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

# Initialize the Sandbox Executor
sandbox_executor = SandboxExecutor()
# Dictionary to map WebSocket session IDs to our sandbox session IDs
socket_to_sandbox_map = {}
session_strikes = {}
STRIKE_LIMIT = 3

@app.route('/')
def home():
    return "Yo! This is the davi - API."

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
    mode = data.get('mode', 'informational') # Defaults to 'informational' mode

    if mode == 'code_execution' and EXECUTION_MODE == 'aws':
        return handle_aws_code_execution(session_id, user_query)

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
            # Ensure visualization is JSON serializable
            result["visualization"] = result["visualization"].to_json()

        return jsonify(result)

    except Exception as e:
        print(f"An error occurred in /analyze endpoint: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500
    
def handle_aws_code_execution(session_id, query):
    """Handles the synchronous code execution flow for the AWS environment."""
    try:
        serialized_df = redis_client.get(session_id)
        if not serialized_df:
            return jsonify({"error": "Invalid or expired session."}), 400
        df = pickle.loads(serialized_df)

        data_processor = DataProcessor()
        data_processor.dataframe = df
        data_processor._extract_metadata()
        agent = DataAnalysisAgent(data_processor, None)
        initial_code_response = agent.process_query(query, mode="code_execution")
        initial_code = initial_code_response['message']

        s3_client = boto3.client('s3', region_name=os.getenv("AWS_REGION"))
        s3_bucket = os.getenv("S3_BUCKET_NAME")
        data_s3_key = f"data/{session_id}/data.csv"

        with io.StringIO() as csv_buffer:
            df.to_csv(csv_buffer, index=False)
            s3_client.put_object(Bucket=s3_bucket, Key=data_s3_key, Body=csv_buffer.getvalue())

        result = sandbox_executor.execute_code(session_id, initial_code, data_s3_key)

        if 'error' in result and result['error']:
            return jsonify({"success": False, "message": result['error']})

        output_data = result.get('output', {})
        if output_data.get('type') == 'visualization':
            return jsonify({"success": True, "visualization": output_data.get('data')})
        else:
            return jsonify({"success": True, "data": [{"output": output_data.get('data', '')}]})

    except Exception as e:
        print(f"An error occurred in handle_aws_code_execution: {e}")
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred during AWS code execution."}), 500

# Endpoint for Dynamic Analysis (Direct Code Execution mode)

@app.route('/execute/start', methods=['POST'])
def execute_start():
    data = request.get_json()
    session_id = data.get('session_id')
    query = data.get('query')
    
    if not all([session_id, query]):
        return jsonify({"error": "Missing 'session_id' or 'query'."}), 400
    
    # 1. Retrieve and save data to a temporary file for the sandbox
    serialized_df = redis_client.get(session_id)
    if not serialized_df:
        return jsonify({"error": "Invalid or expired session."}), 400
    
    df = pickle.loads(serialized_df)
    
    # Create a temporary directory for session files
    temp_dir = os.path.join(BASE_DIR, "temp_data")
    os.makedirs(temp_dir, exist_ok=True) # <-- FIX IS HERE
    temp_filepath = os.path.join(temp_dir, f"{session_id}.csv")
    df.to_csv(temp_filepath, index=False)
    
    # 2. Generate initial code with the agent
    data_processor = DataProcessor()
    data_processor.dataframe = df
    data_processor._extract_metadata()
    agent = DataAnalysisAgent(data_processor, None)
    initial_code = agent.process_query(query, mode="code_execution")
    
    # 3. Start a secure sandbox session
    sandbox_session_id = sandbox_executor.start_session(temp_filepath)
    if not sandbox_session_id:
        return jsonify({"error": "Failed to start safe execution sandbox"}), 500
    
    session_strikes[sandbox_session_id] = 0 # Starting session strikes at 0
    
    # 4. Run the initial code
    initial_result = sandbox_executor.execute_code(sandbox_session_id, initial_code['message'])
    
    # The websocket URL is in the same server, so just returning the session ID
    return jsonify({
        "success": True,
        "sandbox_session_id": sandbox_session_id,
        "initial_code": initial_code['message'],
        "initial_result": initial_result
    })
    
# --- WebSocket Event Handlers for Interactive Visuals ---

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('register_session')
def handle_register_session(data):
    """Links a websocket SID to a sandbox session ID."""
    sandbox_session_id = data.get('sandbox_session_id')
    if sandbox_session_id:
        socket_to_sandbox_map[request.sid] = sandbox_session_id
        print(f"Registered socket {request.sid} to sandbox {sandbox_session_id}")
    
@socketio.on('execute_code')
def handle_execute_code(data):
    """Receives code from the client and runs it in the sandbox."""
    sandbox_session_id = data.get('sandbox_session_id')
    code = data.get('code')
    
    if sandbox_session_id and code:
        result = sandbox_executor.execute_code(sandbox_session_id, code)
        
        if 'error' in result:
            # Increment the strike count for this session
            if sandbox_session_id in session_strikes:
                session_strikes[sandbox_session_id] += 1
                print(f"Strike {session_strikes[sandbox_session_id]} for session {sandbox_session_id}")
                
            # Check if the strike limit has been reached
            if session_strikes.get(sandbox_session_id, 0) >= STRIKE_LIMIT:
                result['error'] = "Session terminated due to multiple execution errors."
                emit('code_result', result) # Send final error message
                sandbox_executor.stop_session(sandbox_session_id)
                # socketio.disconnect(request.sid) 
                return

        elif 'output' in result:
            # If execution was successful, reset the strike counter
            if sandbox_session_id in session_strikes:
                session_strikes[sandbox_session_id] = 0
        
        emit('code_result', result) # Send result back to the client

@socketio.on('disconnect')
def handle_disconnect():
    """Cleans up when a client disconnects."""
    print(f"Client disconnected: {request.sid}")
    if request.sid in socket_to_sandbox_map:
        sandbox_session_id = socket_to_sandbox_map[request.sid]
        print(f"Cleaning up sandbox session: {sandbox_session_id}")
        sandbox_executor.stop_session(sandbox_session_id)
        
        # Clean up the temporary data file
        temp_filepath = os.path.join(BASE_DIR, "temp_data", f"{sandbox_session_id}.csv")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            
        del socket_to_sandbox_map[request.sid]
        
        if sandbox_session_id in session_strikes:
            del session_strikes[sandbox_session_id]
            
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)