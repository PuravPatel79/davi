# Phase 1: Foundational Backend - The Secure Sandbox
# Task 1.2: Develop the Sandbox Executor Module

import docker
from docker.types import Mount
import uuid
import os
import threading
import traceback
import json
import io
import tarfile

# --- Configuration ---
# These settings are loaded from environment variables for production-ready flexibility.
# Default values are provided for local development.
SANDBOX_IMAGE_NAME = os.getenv("SANDBOX_IMAGE_NAME", "davi-sandbox:latest") # The name of the Docker image created
CPU_LIMIT_FLOAT = float(os.getenv("SANDBOX_CPU_LIMIT", "0.5")) # Limit to half a CPU core
MEMORY_LIMIT = os.getenv("SANDBOX_MEMORY_LIMIT", "512m") # Limit the number of processes
PID_LIMIT = int(os.getenv("SANDBOX_PID_LIMIT", 100)) # Limit the number of processes
EXECUTION_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_EXEC_TIMEOUT", 120)) # Max execution time for user code
MAX_SESSIONS = int(os.getenv("SANDBOX_MAX_SESSIONS", 10)) # Max concurrent containers
SESSION_CLEANUP_INTERVAL_SECONDS = int(os.getenv("SANDBOX_CLEANUP_INTERVAL", 600)) # Cleanup check every 10 mins

class SandboxExecutor:
    """
    Manages the lifecycle of secure Docker containers for executing user code.
    """
    def __init__(self):
        try:
            self.client = docker.from_env()
            # A dictionary to keep track of active session containers
            self.sessions = {}
        except docker.errors.DockerException:
            print("Error: Docker is not running or is not configured correctly.")
            print("Please ensure Docker Desktop is running.")
            self.client = None

    def start_session(self, data_filepath):
        """
        Launches a new, secure container for a user session.
        """
        if not self.client:
            raise ConnectionError("Docker client is not available.")

        session_id = str(uuid.uuid4())
        container_name = f"davi-session-{session_id}"

        try:
            print(f"Attempting to use sandbox image: {SANDBOX_IMAGE_NAME}")
            self.client.images.get(SANDBOX_IMAGE_NAME)
            print("Sandbox image found locally.")

            # --- FIX IS HERE: Use the explicit Mount object ---
            container = self.client.containers.run(
                SANDBOX_IMAGE_NAME,
                detach=True,
                name=container_name,
                network_mode="none",
                mem_limit=MEMORY_LIMIT,
                nano_cpus=int(CPU_LIMIT_FLOAT * 1_000_000_000),
                pids_limit=PID_LIMIT,
                command="sleep 3600"
            )

            # --- Now, package and stream the data directly into the container ---
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tarinfo = tarfile.TarInfo(name='data.csv')
                file_size = os.path.getsize(data_filepath)
                tarinfo.size = file_size
                with open(data_filepath, 'rb') as f:
                    tar.addfile(tarinfo, f)
            
            tar_stream.seek(0)
            container.put_archive('/home/appuser/', tar_stream)
            print(f"Data successfully copied into container {container.short_id}")

            self.sessions[session_id] = container
            print(f"Started session {session_id} in container {container.short_id}")
            return session_id
        except Exception as e:
            print("--- AN ERROR OCCURRED IN SANDBOX_EXECUTOR ---")
            traceback.print_exc()
            return None

    def execute_code(self, session_id, code):
        """
        Executes a string of Python code inside a specific session container.
        """
        if session_id not in self.sessions:
            return {"error": "Invalid or expired session."}

        container = self.sessions[session_id]
        
        result = {}
        def run_exec():
            try:
                # Checking if the container is still running
                container.reload()
                if container.status != 'running':
                    result['error'] = "The execution enviornment stopped unexpectedly. Please try starting a new session."
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                    return
                
                # Code execution inside the container    
                exit_code, output_stream = container.exec_run(
                    ["python", "-c", code],
                    user="appuser"
                )
                output_str = output_stream.decode('utf-8').strip() if output_stream else ""
                
                # Error handling for out of memory issue
                if exit_code == 0:
                    try:
                        json.loads(output_str)
                        result['output'] = {"type": "visualization", "data": output_str}
                    except json.JSONDecodeError:
                        result['output'] = {"type": "text", "data": output_str}
                elif exit_code == 137:
                    result['error'] = "Execution failed: The process was terminated due to excessive memory usage. Please start a new session."
                else:
                    result['error'] = output_str
            
            except docker.errors.APIerrors as e:
                # Catches lower-level Docker errors
                result['error'] = f"An execution enviornment error occured: {e}"
            except Exception as e:
                result['error'] = f"An unxepected error occurred during execution: {str(e)}"

        exec_thread = threading.Thread(target=run_exec)
        exec_thread.start()
        exec_thread.join(timeout=EXECUTION_TIMEOUT_SECONDS)
        
        if exec_thread.is_alive():
            # try:
            #     container.stop(timeout=5)
            #     container.remove()
            # except Exception as e:
            #     print(f"Error stopping timed-out container: {e}")
            # del self.sessions[session_id]
            # return {"error": "Execution timed out and was terminated."}
            
            # If the code times out
            # Just return an error. This allows the session to remain active
            # so the "strike system" in app.py can handle it
            print(f"Execution timed out for session {session_id}. The session remains active.")
            return {"error": "Execution timed out. Please check your code for infinite loops and try again."}
        
        return result

    def stop_session(self, session_id):
        """
        Stops and removes the container for a given session.
        """
        if session_id in self.sessions:
            container = self.sessions[session_id]
            try:
                container.stop(timeout=5)
                container.remove()
                print(f"Stopped and removed container for session {session_id}")
            except Exception as e:
                print(f"Error stopping container for session {session_id}: {e}")
            finally:
                del self.sessions[session_id]