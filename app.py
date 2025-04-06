import streamlit as st
import pandas as pd
import time
import os
import shutil
import base64
from io import BytesIO
import threading
from datetime import datetime

# Import your existing ScreenActivityMonitor class
from screen_monitor import ScreenActivityMonitor  # Make sure this file is in the same directory

# Set page title and layout
st.set_page_config(
    page_title="Screen Activity Monitor",
    page_icon="🖥️",
    layout="wide"
)

# Define function to create a download link for dataframe
def get_csv_download_link(df, filename="activity_data.csv", link_text="Download CSV"):
    """Generate a download link for a dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

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

# Create a session state to track monitoring status
if 'monitoring_active' not in st.session_state:
    st.session_state.monitoring_active = False

if 'monitor' not in st.session_state:
    st.session_state.monitor = None

if 'results' not in st.session_state:
    st.session_state.results = None

if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None

# Main app header
st.title("🖥️ Screen Activity Monitor")
st.write("Monitor and analyze your screen activity")

# Create sidebar for monitoring controls
with st.sidebar:
    st.header("Monitoring Settings")
    interval = st.slider("Capture Interval (seconds)",
                        min_value=1,
                        max_value=60,
                        value=5,
                        help="Time between captures in seconds")

    duration = st.slider("Monitoring Duration (minutes)",
                        min_value=1,
                        max_value=120,
                        value=5,
                        help="Total monitoring time in minutes")

    output_dir = "screen_monitor_data"

    # Start/stop button
    if not st.session_state.monitoring_active:
        if st.button("Start Monitoring"):
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
            st.rerun()  # Updated from experimental_rerun
    else:
        if st.button("Stop Monitoring"):
            if st.session_state.monitor:
                st.session_state.monitor.stop()
                st.session_state.monitoring_active = False

                # Load results after stopping
                try:
                    log_file = os.path.join(output_dir, "activity_log.csv")
                    if os.path.exists(log_file):
                        data = pd.read_csv(log_file)
                        st.session_state.raw_data = data

                        # Generate summary
                        if len(data) > 0:
                            app_usage = data['active_window_title'].value_counts().reset_index()
                            app_usage.columns = ['Application', 'Count']
                            app_usage['Percentage'] = (app_usage['Count'] / len(data) * 100).round(2)
                            st.session_state.results = app_usage
                except Exception as e:
                    st.error(f"Error loading results: {e}")

                st.rerun()  # Updated from experimental_rerun

    # Add cleanup button
    if st.button("Clean Up Previous Data"):
        cleanup_data()
        st.session_state.results = None
        st.session_state.raw_data = None

# Main content area
if st.session_state.monitoring_active:
    # Create a progress bar for the monitoring duration
    progress_container = st.container()
    with progress_container:
        # Calculate total seconds for monitoring
        total_seconds = duration * 60
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        # Update progress in a loop
        placeholder = st.empty()
        placeholder.markdown("""
        ### 🔴 Monitoring Active
        Please wait while screen activity is being monitored.

        * Screenshots are being captured every {} seconds
        * Total monitoring duration: {} minutes
        * Do not close this browser window
        """.format(interval, duration))

        # Update the progress bar
        start_time = time.time()
        while st.session_state.monitoring_active:
            elapsed = time.time() - start_time

            if elapsed > total_seconds:
                # Time's up, stop monitoring
                if st.session_state.monitor and st.session_state.monitor.running:
                    st.session_state.monitor.stop()
                    st.session_state.monitoring_active = False
                    break

            # Update progress indicators
            progress = min(elapsed / total_seconds, 1.0)
            progress_bar.progress(progress)

            remaining = max(0, total_seconds - elapsed)
            status_text.text(f"⏱️ {int(remaining // 60)}:{int(remaining % 60):02d} remaining")

            # Don't overwhelm the UI with updates
            time.sleep(1)

        # Update UI after completion
        progress_bar.progress(1.0)
        status_text.text("✅ Monitoring completed!")

else:
    # Display results if available
    if st.session_state.results is not None and st.session_state.raw_data is not None:
        st.success("✅ Monitoring completed!")

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

            # Add download button for summary
            st.download_button(
                label="⬇️ Download Summary",
                data=top_apps.to_csv(index=False).encode('utf-8'),
                file_name="application_summary.csv",
                mime="text/csv"
            )

        with tab2:
            st.header("Raw Activity Data")
            st.dataframe(st.session_state.raw_data, use_container_width=True)

            # Add download button for raw data
            st.download_button(
                label="⬇️ Download Raw Data",
                data=st.session_state.raw_data.to_csv(index=False).encode('utf-8'),
                file_name="activity_log.csv",
                mime="text/csv"
            )

            # Button to clean up data
            if st.button("Clear Data and Start New Session"):
                cleanup_data()
                st.session_state.results = None
                st.session_state.raw_data = None
                st.rerun()  # Updated from experimental_rerun
    else:
        # Show instructions when no monitoring is active
        st.info("👈 Configure and start monitoring using the sidebar controls")

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

# Footer
st.markdown("---")
st.caption("Screen Activity Monitor - Privacy-focused tracking of your screen time")
