import os
import subprocess
import streamlit as st
import threading
import time
import queue # Import queue for thread-safe communication

# Set page configuration
st.set_page_config(page_title="Honey-Girl", layout="wide")

# UI control state initialization
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.logs = ""
    st.session_state.process_started = False # New flag to indicate if app.py was attempted to start
    st.session_state.process_output_queue = queue.Queue() # Thread-safe queue for logs
    st.session_state.backend_process = None # Store the Popen object here

st.title("🌐 Honey-Girl")

# Environment variables (unchanged)
envs = {
    "BOT_TOKEN": st.secrets.get("BOT_TOKEN", ""),
    "CHAT_ID": st.secrets.get("CHAT_ID", ""),
    "ARGO_AUTH": st.secrets.get("ARGO_AUTH", ""),
    "ARGO_DOMAIN": st.secrets.get("ARGO_DOMAIN", ""),
    "NEZHA_KEY": st.secrets.get("NEZHA_KEY", ""),
    "NEZHA_PORT": st.secrets.get("NEZHA_PORT", ""),
    "NEZHA_SERVER": st.secrets.get("NEZHA_SERVER", ""),
}

# Write .env file (unchanged)
with open("./env.sh", "w") as shell_file:
    shell_file.write("#!/bin/bash\n")
    for k, v in envs.items():
        os.environ[k] = v
        shell_file.write(f"export {k}='{v}'\n")

# Function to run backend in a separate thread
# This function should NOT directly access st.session_state
def start_backend_process(output_queue):
    output_queue.put("⚙️ Starting backend process...\n")
    try:
        # Give execute permission to app.py
        output_queue.put("chmod +x app.py ...\n")
        subprocess.run("chmod +x app.py", shell=True, check=True, capture_output=True, text=True)
        output_queue.put("✅ chmod +x app.py completed\n")

        # IMPORTANT: pip install -r requirements.txt should ideally be done in Dockerfile
        # or before Streamlit starts. Running it repeatedly can be inefficient.
        # For robustness, we will remove it here, assuming Dockerfile handles it.
        # If you must run it here, ensure it only runs once per app lifecycle.
        # output_queue.put("pip install -r requirements.txt ...\n")
        # install_result = subprocess.run("pip install -r requirements.txt", shell=True, check=True, capture_output=True, text=True)
        # output_queue.put(install_result.stdout)
        # output_queue.put("✅ Dependencies installed (if not already by Dockerfile)\n")


        # Start app.py in background
        output_queue.put("Starting python app.py ...\n")
        # Store the Popen object directly in st.session_state from the main thread
        # This is tricky because the Popen object is created in the thread.
        # We need to return it or set it in a way the main thread can pick up.
        # For now, let's keep it simple: the thread directly interacts with the process.
        process = subprocess.Popen(["python", "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        output_queue.put("✅ Backend service successfully launched!\n")

        # Read output continuously
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()

            if stdout_line:
                output_queue.put(stdout_line)
            if stderr_line:
                output_queue.put(f"ERROR: {stderr_line}")

            if not stdout_line and not stderr_line and process.poll() is not None:
                # Process has exited and no more output
                break
            time.sleep(0.05) # Small delay to prevent busy-waiting

        output_queue.put(f"\nBackend process exited with code {process.returncode}\n")
        # Mark as not running from the main thread's perspective later
        output_queue.put("__PROCESS_EXITED__") # Special marker for main thread
    except subprocess.CalledProcessError as e:
        output_queue.put(f"\n❌ Command execution error: {e}\n")
        output_queue.put(f"stdout:\n{e.stdout}\n")
        output_queue.put(f"stderr:\n{e.stderr}\n")
        output_queue.put("__PROCESS_EXITED_ERROR__")
    except Exception as e:
        output_queue.put(f"\n❌ An unknown error occurred during startup: {e}\n")
        output_queue.put("__PROCESS_EXITED_ERROR__")


# --- Main Streamlit App Logic ---

# Function to process queue and update session state
def update_logs_from_queue():
    while not st.session_state.process_output_queue.empty():
        log_entry = st.session_state.process_output_queue.get()
        if log_entry == "__PROCESS_EXITED__":
            st.session_state.running = False
            st.session_state.backend_process = None
            st.session_state.logs += "\nBackend process has finished."
        elif log_entry == "__PROCESS_EXITED_ERROR__":
            st.session_state.running = False
            st.session_state.backend_process = None
            st.session_state.logs += "\nBackend process exited with an error."
        else:
            st.session_state.logs += log_entry
    if st.session_state.backend_process and st.session_state.backend_process.poll() is not None and st.session_state.running:
        # If the process finished but the state hasn't been updated yet
        st.session_state.running = False
        st.session_state.backend_process = None
        st.session_state.logs += "\nBackend process terminated unexpectedly."


# Check if the backend process needs to be started
if not st.session_state.process_started: # Use a new flag for initial launch attempt
    st.session_state.logs = "🔄 Attempting to start backend service...\n"
    st.session_state.process_started = True # Mark that we've tried to start it
    # Start the thread, passing the queue
    threading.Thread(target=start_backend_process, args=(st.session_state.process_output_queue,), daemon=True).start()
    st.warning("🔄 Initializing and starting backend service, please wait...")
    st.session_state.running = True # Assume it's running until told otherwise

# Periodically update logs from the queue
update_logs_from_queue()

# Rerun the Streamlit app periodically to update logs
if st.session_state.running:
    st.info("Backend service is running. Checking for updates...")
    time.sleep(1) # Wait a bit before rerunning to avoid excessive refreshes
    st.rerun() # This will re-execute the script and check the queue again
else:
    if st.session_state.process_started: # Only show success/failure after initial attempt
        if st.session_state.backend_process is None: # Process has exited
            st.error("❌ Backend service is not running or has terminated.")
        else:
            st.success("✅ Backend service is running (initialized).") # Should not hit this if running is false

# Display logs
st.subheader("Deployment Logs")
st.code(st.session_state.logs, language="bash", height=300)

# Display videos and images (unchanged)
video_paths = ["./meinv.mp4", "./mv2.mp4"]
for path in video_paths:
    if os.path.exists(path):
        st.video(path)

image_path = "./mv.jpg"
if os.path.exists(image_path):
    st.image(image_path, caption="南音", use_container_width=True)
