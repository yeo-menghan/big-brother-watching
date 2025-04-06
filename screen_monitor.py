import cv2
import numpy as np
import pandas as pd
import time
import os
import subprocess
from datetime import datetime
from PIL import ImageGrab
import threading
import argparse

class ScreenActivityMonitor:
    def __init__(self, interval=60, output_dir="screen_monitor_data", duration=None):
        """
        Initialize the Screen Activity Monitor

        Parameters:
        - interval: Time in seconds between captures (default: 60 seconds)
        - output_dir: Directory to store logs and screenshots
        - duration: Duration in minutes to run the monitor (default: None, runs until stopped)
        """
        self.interval = interval
        self.output_dir = output_dir
        self.screenshots_dir = os.path.join(output_dir, "screenshots")
        self.log_file = os.path.join(output_dir, "activity_log.csv")
        self.running = False
        self.activity_data = []
        self.duration = duration * 60 if duration else None  # Convert minutes to seconds

        # Create output directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # Initialize log file if it doesn't exist
        if not os.path.exists(self.log_file):
            pd.DataFrame(columns=[
                'timestamp',
                'active_window_title',
                'screenshot_path',
                'notes'
            ]).to_csv(self.log_file, index=False)

    def show_notification(self, title, message):
        """Show a macOS notification"""
        try:
            cmd = f"""osascript -e 'display notification "{message}" with title "{title}"'"""
            subprocess.run(cmd, shell=True)
        except Exception as e:
            print(f"Failed to show notification: {e}")

    def capture_screenshot(self):
        """Capture a screenshot of the current screen"""
        screenshot = ImageGrab.grab()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        screenshot.save(filepath)
        return filepath

    def get_active_window_macos(self):
        """Get the title of the currently active window on macOS"""
        try:
            # AppleScript to get frontmost application name
            cmd = """osascript -e 'tell application "System Events"
                        set frontApp to name of first application process whose frontmost is true
                    end tell'"""
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            app_name = result.stdout.strip()

            # Try to get more detailed window title if possible
            cmd_window = f"""osascript -e 'tell application "{app_name}"
                                try
                                    set window_name to name of front window
                                    return "{app_name} - " & window_name
                                on error
                                    return "{app_name}"
                                end try
                            end tell'"""
            result_window = subprocess.run(cmd_window, shell=True, capture_output=True, text=True)
            if result_window.returncode == 0 and result_window.stdout.strip():
                return result_window.stdout.strip()
            else:
                return app_name
        except Exception as e:
            print(f"Error getting active window: {e}")
            return "Unknown"

    def log_activity(self, timestamp, window_title, screenshot_path, notes=""):
        """Log the current activity to the dataframe"""
        self.activity_data.append({
            'timestamp': timestamp,
            'active_window_title': window_title,
            'screenshot_path': screenshot_path,
            'notes': notes
        })

    def save_log(self):
        """Save the activity log to CSV file"""
        if self.activity_data:
            new_data = pd.DataFrame(self.activity_data)

            # Check if the file exists and has content
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > 0:
                existing_data = pd.read_csv(self.log_file)
                updated_data = pd.concat([existing_data, new_data], ignore_index=True)
            else:
                updated_data = new_data

            updated_data.to_csv(self.log_file, index=False)
            self.activity_data = []  # Clear after saving

    def show_status_icon(self, active=True):
        """Create a small floating window as a visual indicator"""
        try:
            # Use AppleScript to show a small floating icon in the menubar
            if active:
                message = f"Recording active - {len(self.activity_data)} captures"
                self.show_notification("Screen Recorder", message)
                print(f"\r🔴 Recording... ({len(self.activity_data)} captures)", end="")
            else:
                print("\r⚫ Recording stopped                      ")
        except Exception as e:
            print(f"Error showing status: {e}")

    def monitor_loop(self):
        """Main monitoring loop"""
        start_time = time.time()
        capture_count = 0
        notification_interval = max(60, self.interval * 10)  # Show notification every 10 captures or at least every minute

        # Show initial recording notification
        self.show_notification("Screen Monitor", "Recording started")

        while self.running:
            try:
                # Check if duration has elapsed
                current_time = time.time()
                elapsed_time = current_time - start_time

                if self.duration and (elapsed_time >= self.duration):
                    print(f"\nMonitoring duration of {self.duration/60:.1f} minutes completed.")
                    self.running = False
                    break

                # Show visual indicator
                self.show_status_icon(active=True)

                # Get current timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Capture screenshot
                screenshot_path = self.capture_screenshot()

                # Get active window title (macOS specific)
                active_window = self.get_active_window_macos()

                # Log the activity
                self.log_activity(timestamp, active_window, screenshot_path)

                # Increment capture count
                capture_count += 1

                # Show periodic notification
                if capture_count % 10 == 0 or (current_time - start_time) % notification_interval < self.interval:
                    remaining = ""
                    if self.duration:
                        remaining_sec = max(0, self.duration - elapsed_time)
                        remaining = f" - {remaining_sec/60:.1f} min remaining"

                    self.show_notification("Screen Monitor",
                                          f"Still recording{remaining}\n{capture_count} captures so far")

                # Save periodically (every 5 captures)
                if len(self.activity_data) >= 5:
                    self.save_log()

                # Wait for the next interval
                time.sleep(self.interval)

            except Exception as e:
                print(f"\nError in monitoring loop: {e}")
                time.sleep(self.interval)  # Still wait before retry

        # Make sure to save any remaining data when the loop exits
        self.save_log()
        self.show_status_icon(active=False)
        print("\nMonitoring stopped. Data saved.")
        self.show_notification("Screen Monitor", "Recording completed")

    def start(self):
        """Start the monitoring process"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()

            duration_msg = f" for {self.duration/60:.1f} minutes" if self.duration else ""
            print(f"Screen activity monitoring started{duration_msg}. Capturing every {self.interval} seconds.")
            print(f"Screenshots saved to: {self.screenshots_dir}")
            print(f"Activity log saved to: {self.log_file}")
            print("Press Ctrl+C at any time to stop monitoring.")
            print("🔴 Recording started...")

    def stop(self):
        """Stop the monitoring process"""
        self.running = False
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=self.interval+5)

        # Save any remaining data
        self.save_log()
        print("\nScreen activity monitoring stopped.")
        self.show_notification("Screen Monitor", "Recording stopped by user")

    def analyze_data(self):
        """Analyze the collected data and return a summary"""
        if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
            return "No data available for analysis."

        data = pd.read_csv(self.log_file)

        # Basic analysis
        total_records = len(data)
        unique_apps = data['active_window_title'].nunique()
        time_span = pd.to_datetime(data['timestamp'])

        if len(time_span) < 2:
            return "Not enough data for analysis. Only one record found."

        total_time = (time_span.max() - time_span.min()).total_seconds() / 3600  # in hours

        # App usage breakdown
        app_usage = data['active_window_title'].value_counts()
        app_percentage = (app_usage / total_records * 100).round(2)

        # Format results
        results = f"Screen Activity Analysis:\n"
        results += f"- Monitoring period: {total_time:.2f} hours\n"
        results += f"- Total records: {total_records}\n"
        results += f"- Unique applications: {unique_apps}\n\n"

        results += "Top 5 applications by usage:\n"
        for app, pct in app_percentage.head(5).items():
            results += f"- {app}: {pct}%\n"

        return results


def main():
    parser = argparse.ArgumentParser(description="Local Screen Activity Monitor")
    parser.add_argument("--interval", type=int, default=60,
                        help="Capture interval in seconds (default: 60)")
    parser.add_argument("--duration", type=int, default=None,
                        help="Duration to run in minutes (default: run until stopped)")
    parser.add_argument("--output", type=str, default="screen_monitor_data",
                        help="Output directory for logs and screenshots")
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze existing data instead of starting monitoring")
    args = parser.parse_args()

    monitor = ScreenActivityMonitor(
        interval=args.interval,
        output_dir=args.output,
        duration=args.duration
    )

    if args.analyze:
        print(monitor.analyze_data())
    else:
        try:
            monitor.start()

            # Wait for duration to complete or until interrupted
            if monitor.duration:
                # Add a small buffer to let the thread complete naturally
                time.sleep(monitor.duration + 5)
            else:
                # No duration specified, wait indefinitely
                while monitor.running:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nMonitoring interrupted by user.")
            monitor.stop()


if __name__ == "__main__":
    main()
