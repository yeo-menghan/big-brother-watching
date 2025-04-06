import streamlit as st
import pandas as pd
import time
import os
import shutil
import base64
from io import BytesIO
import threading
from datetime import datetime
import sys

# Set page title and layout
st.set_page_config(
    page_title="Screen Activity Monitor",
    page_icon="🖥️",
    layout="wide"
)

# Detect if we're running in the cloud
is_cloud_environment = (
    "STREAMLIT_SHARING" in os.environ or
    "STREAMLIT_SERVER_BASE_URL_PATH" in os.environ or
    not os.path.exists("/usr/bin/sw_vers")  # Check for macOS-specific command
)

# Only import the ScreenActivityMonitor if we're in a local environment
if not is_cloud_environment:
    try:
        from screen_monitor import ScreenActivityMonitor
        screen_monitor_available = True
    except ImportError:
        screen_monitor_available = False
else:
    screen_monitor_available = False

# Function to show instructions
def _show_instructions():
    st.markdown("""
    ### How to use this tool:

    1. Set the **Capture Interval** - how frequently to take screenshots (in seconds)
    2. Set the **Monitoring Duration** - how long to monitor (in minutes)
    3. Click **Start Monitoring** to begin
    4. Wait for the monitoring to complete
    5. View the summary and download your data
    6. Click **Clean Up Previous Data** when you're done to remove all screenshots and logs

    This tool runs entirely on your local machine and does not upload any data.
    """)

# Function to clean up data directories
def cleanup_data():
    """Remove all files from the data directories"""
    data_dir = "screen_monitor_data"
    if os.path.exists(data_dir):
        try:
            shutil.rmtree(data_dir)
            st.success("Previous monitoring data has been cleaned up")
        except Exception as e:
            st.error(f"Error cleaning up data: {e}")

# Function to load most recent data if it exists
def load_existing_data():
    output_dir = "screen_monitor_data"
    log_file = os.path.join(output_dir, "activity_log.csv")
    if os.path.exists(log_file):
        try:
            data = pd.read_csv(log_file)
            if len(data) > 0:
                app_usage = data['active_window_title'].value_counts().reset_index()
                app_usage.columns = ['Application', 'Count']
                app_usage['Percentage'] = (app_usage['Count'] / len(data) * 100).round(2)
                return data, app_usage
        except Exception as e:
            st.error(f"Error loading existing data: {e}")
    return None, None

# Function to generate sample data for cloud demos
def generate_sample_data():
    # Create sample timestamps
    # timestamps = [datetime.now() - datetime.timedelta(minutes=i) for i in range(60)]
    timestamps = [datetime.now() - pd.Timedelta(minutes=i) for i in range(60)]

    # Create sample applications and titles
    applications = [
        "Microsoft Word - Document1.docx",
        "Google Chrome - Gmail",
        "Slack",
        "VS Code - project.py",
        "Terminal",
        "Zoom Meeting",
        "Excel - Spreadsheet1.xlsx",
        "Finder",
        "Spotify"
    ]

    # Create weighted random selection (some apps appear more than others)
    weights = [0.25, 0.20, 0.15, 0.15, 0.05, 0.05, 0.05, 0.05, 0.05]

    # Generate sample data
    import random
    import numpy as np

    # Seed for reproducibility
    random.seed(42)
    np.random.seed(42)

    # Create DataFrame
    data = []
    for ts in timestamps:
        app = np.random.choice(applications, p=weights)
        data.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "active_window_title": app,
            "screen_activity": random.choice(["Active", "Idle"]),
        })

    df = pd.DataFrame(data)

    # Create summary
    app_usage = df['active_window_title'].value_counts().reset_index()
    app_usage.columns = ['Application', 'Count']
    app_usage['Percentage'] = (app_usage['Count'] / len(df) * 100).round(2)

    return df, app_usage

# Sync interval slider with text input
def update_interval_input():
    st.session_state.interval_input = st.session_state.interval_slider

def update_interval_slider():
    st.session_state.interval_slider = st.session_state.interval_input

# Sync duration slider with text input
def update_duration_input():
    st.session_state.duration_input = st.session_state.duration_slider

def update_duration_slider():
    st.session_state.duration_slider = st.session_state.duration_input

# Initialize session state variables if they don't exist
if 'monitoring_active' not in st.session_state:
    st.session_state.monitoring_active = False

if 'monitor' not in st.session_state:
    st.session_state.monitor = None

if 'results' not in st.session_state:
    st.session_state.results = None

if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None

# Load data for local environment, generate sample data for cloud
if is_cloud_environment:
    if st.session_state.raw_data is None or st.session_state.results is None:
        # Use sample data in cloud environment
        st.session_state.raw_data, st.session_state.results = generate_sample_data()
else:
    # Try to load existing data if available (local environment)
    if st.session_state.raw_data is None or st.session_state.results is None:
        raw_data, results = load_existing_data()
        if raw_data is not None and results is not None:
            st.session_state.raw_data = raw_data
            st.session_state.results = results

# Initialize default values
default_interval = 5
default_duration = 5

# Try to get values from URL params
if "interval" in st.query_params:
    try:
        default_interval = int(st.query_params["interval"])
    except ValueError:
        pass

if "duration" in st.query_params:
    try:
        default_duration = int(st.query_params["duration"])
    except ValueError:
        pass

# Initialize interval and duration in session state if not already set
if 'interval_slider' not in st.session_state:
    st.session_state.interval_slider = default_interval

if 'interval_input' not in st.session_state:
    st.session_state.interval_input = default_interval

if 'duration_slider' not in st.session_state:
    st.session_state.duration_slider = default_duration

if 'duration_input' not in st.session_state:
    st.session_state.duration_input = default_duration

# Main app header
st.title("🖥️ Screen Activity Monitor")
st.write("Monitor and analyze your screen activity")

# Display cloud mode banner if needed
if is_cloud_environment:
    st.warning("""
    ⚠️ **CLOUD DEMO MODE ACTIVE**

    This app is running on Streamlit Cloud, which doesn't support screen capture.
    You're viewing a demo with sample data. For full functionality, please run this app locally.

    ```
    pip install streamlit opencv-python pandas
    streamlit run app.py
    ```
    """)

# Create sidebar for monitoring controls
with st.sidebar:
    st.header("Monitoring Settings")

    # Interval settings (slider + text input)
    col1, col2 = st.columns([3, 1])
    with col1:
        interval_slider = st.slider(
            "Capture Interval (seconds)",
            min_value=1,
            max_value=60,
            key="interval_slider",
            on_change=update_interval_input,
            help="Time between captures in seconds",
            disabled=is_cloud_environment
        )
    with col2:
        interval_input = st.number_input(
            "Seconds",
            min_value=1,
            max_value=60,
            step=1,
            key="interval_input",
            on_change=update_interval_slider,
            disabled=is_cloud_environment
        )

    # Use the value from text input for interval
    interval = st.session_state.interval_input

    # Duration settings (slider + text input)
    col1, col2 = st.columns([3, 1])
    with col1:
        duration_slider = st.slider(
            "Monitoring Duration (minutes)",
            min_value=1,
            max_value=120,
            key="duration_slider",
            on_change=update_duration_input,
            help="Total monitoring time in minutes",
            disabled=is_cloud_environment
        )
    with col2:
        duration_input = st.number_input(
            "Minutes",
            min_value=1,
            max_value=120,
            step=1,
            key="duration_input",
            on_change=update_duration_slider,
            disabled=is_cloud_environment
        )

    # Use the value from text input for duration
    duration = st.session_state.duration_input

    st.markdown("---")
    output_dir = "screen_monitor_data"

    # Show a summary of the configuration
    st.markdown(f"""
    **Monitoring Configuration:**
    - Taking screenshots every **{interval} seconds**
    - Running for **{duration} minutes**
    - Total captures: ~**{int((duration * 60) / interval)}**
    """)

    # Start/stop button (disable in cloud environment)
    if not st.session_state.monitoring_active:
        start_button = st.button(
            "▶️ Start Monitoring",
            type="primary",
            use_container_width=True,
            disabled=is_cloud_environment or not screen_monitor_available
        )
        if start_button and not is_cloud_environment and screen_monitor_available:
            # Add params to URL
            st.query_params["interval"] = str(interval)
            st.query_params["duration"] = str(duration)

            # Clear previous results
            st.session_state.results = None
            st.session_state.raw_data = None

            # Initialize and start the monitor
            st.session_state.monitor = ScreenActivityMonitor(
                interval=interval,
                output_dir=output_dir,
                duration=duration
            )
            st.session_state.monitor.start()
            st.session_state.monitoring_active = True
            st.rerun()
    else:
        stop_button = st.button(
            "⏹️ Stop Monitoring",
            type="primary",
            use_container_width=True
        )
        if stop_button:
            if st.session_state.monitor:
                st.session_state.monitor.stop()
                st.session_state.monitoring_active = False

                # Load results after stopping
                raw_data, results = load_existing_data()
                if raw_data is not None and results is not None:
                    st.session_state.raw_data = raw_data
                    st.session_state.results = results

                st.rerun()

    # Add cleanup button (disabled in cloud environment)
    if st.button("🧹 Clean Up Previous Data",
                use_container_width=True,
                disabled=is_cloud_environment):
        cleanup_data()
        st.session_state.results = None
        st.session_state.raw_data = None
        # Clear query params
        st.query_params.clear()
        st.rerun()

    # Add a "Load Sample Data" button in cloud environment
    if is_cloud_environment:
        if st.button("🔄 Load New Sample Data", use_container_width=True):
            st.session_state.raw_data, st.session_state.results = generate_sample_data()
            st.rerun()

# Main content area - monitoring in progress
if st.session_state.monitoring_active and not is_cloud_environment:
    # Create a progress bar for the monitoring duration
    progress_container = st.container()
    with progress_container:
        # Calculate total seconds for monitoring
        total_seconds = duration * 60

        st.markdown("### 🔴 Monitoring in Progress")

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📸 Capturing every **{interval} seconds**")
        with col2:
            st.info(f"⏱️ Total duration: **{duration} minutes**")

        progress_bar = st.progress(0.0)
        status_text = st.empty()
        est_captures = st.empty()

        # Display the monitoring parameters
        st.markdown("""
        Screenshots are being saved locally. Do not close this browser window.
        You'll be able to download the results once monitoring completes.
        """)

        # Add a divider
        st.markdown("---")

        # Update the progress bar
        start_time = time.time()
        while st.session_state.monitoring_active:
            elapsed = time.time() - start_time

            if elapsed > total_seconds:
                # Time's up, stop monitoring
                if st.session_state.monitor and st.session_state.monitor.running:
                    st.session_state.monitor.stop()
                    st.session_state.monitoring_active = False

                    # Load the results
                    raw_data, results = load_existing_data()
                    if raw_data is not None and results is not None:
                        st.session_state.raw_data = raw_data
                        st.session_state.results = results

                    break

            # Update progress indicators
            progress = min(elapsed / total_seconds, 1.0)
            progress_bar.progress(progress)

            remaining = max(0, total_seconds - elapsed)
            minutes_remaining = int(remaining // 60)
            seconds_remaining = int(remaining % 60)
            status_text.markdown(f"### ⏱️ Time remaining: **{minutes_remaining}:{seconds_remaining:02d}**")

            # Check if there's partial data to display
            if os.path.exists(os.path.join(output_dir, "activity_log.csv")):
                # Try to load and display partial results
                try:
                    curr_data = pd.read_csv(os.path.join(output_dir, "activity_log.csv"))
                    captures_completed = len(curr_data)
                    est_captures.markdown(f"📊 **{captures_completed}** screenshots captured so far")
                except:
                    # Fallback to estimate if file can't be read
                    captures_completed = int(elapsed // interval)
                    est_captures.markdown(f"📊 Approximately **{captures_completed}** screenshots captured so far")
            else:
                # Fallback to estimate if file doesn't exist
                captures_completed = int(elapsed // interval)
                est_captures.markdown(f"📊 Approximately **{captures_completed}** screenshots captured so far")

            # Don't overwhelm the UI with updates
            time.sleep(1)

        # Update UI after completion
        progress_bar.progress(1.0)
        status_text.markdown("### ✅ Monitoring completed!")
        st.rerun()  # Refresh to show results

else:
    # Display results if available
    if st.session_state.results is not None and st.session_state.raw_data is not None:
        if is_cloud_environment:
            st.success("📊 Viewing sample data - in demo mode")
        else:
            st.success("✅ Previous monitoring data found")

        # Create tabs for different views
        tab1, tab2 = st.tabs(["Summary", "Raw Data"])

        with tab1:
            st.header("Application Usage Summary")

            # Show summary stats
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Captures", len(st.session_state.raw_data))

            with col2:
                unique_apps = st.session_state.raw_data['active_window_title'].nunique()
                st.metric("Unique Applications", unique_apps)

            with col3:
                time_span = pd.to_datetime(st.session_state.raw_data['timestamp'])
                if len(time_span) >= 2:
                    total_time = (time_span.max() - time_span.min()).total_seconds() / 60  # in minutes
                    st.metric("Monitoring Period", f"{total_time:.1f} minutes")

            # Show summary table
            st.subheader("Application Distribution")
            st.dataframe(st.session_state.results, use_container_width=True)

            # Add bar chart
            st.subheader("Top Applications by Usage")
            top_apps = st.session_state.results.head(10)  # Top 10 apps
            st.bar_chart(top_apps.set_index('Application')['Percentage'])

            # Add download button for summary (disabled in cloud environment)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download Summary Report",
                    data=st.session_state.results.to_csv(index=False).encode('utf-8'),
                    file_name="application_summary.csv",
                    mime="text/csv",
                    use_container_width=True,
                    disabled=is_cloud_environment
                )

        with tab2:
            st.header("Raw Activity Data")
            st.dataframe(st.session_state.raw_data, use_container_width=True)

            # Add download button for raw data (disabled in cloud environment)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download Complete Activity Log",
                    data=st.session_state.raw_data.to_csv(index=False).encode('utf-8'),
                    file_name="activity_log.csv",
                    mime="text/csv",
                    use_container_width=True,
                    disabled=is_cloud_environment
                )

            # Button to clean up data (disabled in cloud environment)
            st.markdown("---")
            if st.button("🔄 Clear Data and Start New Session",
                        use_container_width=True,
                        disabled=is_cloud_environment):
                cleanup_data()
                st.session_state.results = None
                st.session_state.raw_data = None
                # Clear query params
                st.query_params.clear()
                st.rerun()
    else:
        # For local environment - check for existing data
        if not is_cloud_environment:
            # Try to load existing data
            output_dir = "screen_monitor_data"
            log_file = os.path.join(output_dir, "activity_log.csv")

            if os.path.exists(log_file):
                # Load the existing data and show it
                try:
                    data = pd.read_csv(log_file)

                    if len(data) > 0:
                        st.success("✅ Found existing monitoring data")

                        # Generate summary
                        app_usage = data['active_window_title'].value_counts().reset_index()
                        app_usage.columns = ['Application', 'Count']
                        app_usage['Percentage'] = (app_usage['Count'] / len(data) * 100).round(2)

                        # Show summary stats
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Total Captures", len(data))

                        with col2:
                            unique_apps = data['active_window_title'].nunique()
                            st.metric("Unique Applications", unique_apps)

                        with col3:
                            time_span = pd.to_datetime(data['timestamp'])
                            if len(time_span) >= 2:
                                total_time = (time_span.max() - time_span.min()).total_seconds() / 60  # in minutes
                                st.metric("Monitoring Period", f"{total_time:.1f} minutes")

                        # Show summary table
                        st.subheader("Application Distribution")
                        st.dataframe(app_usage, use_container_width=True)

                        # Add bar chart
                        st.subheader("Top Applications by Usage")
                        top_apps = app_usage.head(10)  # Top 10 apps
                        st.bar_chart(top_apps.set_index('Application')['Percentage'])

                        # Add download buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="⬇️ Download Summary Report",
                                data=app_usage.to_csv(index=False).encode('utf-8'),
                                file_name="application_summary.csv",
                                mime="text/csv"
                            )
                        with col2:
                            st.download_button(
                                label="⬇️ Download Complete Activity Log",
                                data=data.to_csv(index=False).encode('utf-8'),
                                file_name="activity_log.csv",
                                mime="text/csv"
                            )

                        # Button to clean up data
                        st.markdown("---")
                        if st.button("🔄 Clear Data and Start New Session", use_container_width=True):
                            cleanup_data()
                            st.rerun()
                    else:
                        # Show instructions when no monitoring is active
                        st.info("👈 Configure and start monitoring using the sidebar controls")
                        _show_instructions()
                except Exception as e:
                    # Show instructions when no monitoring is active
                    st.error(f"Error reading existing data: {e}")
                    st.info("👈 Configure and start monitoring using the sidebar controls")
                    _show_instructions()
            else:
                # Show instructions when no monitoring is active
                st.info("👈 Configure and start monitoring using the sidebar controls")
                _show_instructions()
        else:
            # This is a cloud environment with no data loaded yet
            # Generate sample data for the demo
            if st.session_state.raw_data is None or st.session_state.results is None:
                st.session_state.raw_data, st.session_state.results = generate_sample_data()
                st.rerun()

# Footer
st.markdown("---")
st.caption("Screen Activity Monitor - Privacy-focused tracking of your screen time")
if is_cloud_environment:
    st.caption("Running in demo mode. For full functionality, install and run locally.")
