import cv2
import numpy as np
import pandas as pd
import time
import os
from datetime import datetime
from PIL import Image, ImageGrab
import threading
import argparse
import pytesseract  # For OCR text extraction
import platform

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
        self.region_shots_dir = os.path.join(output_dir, "regions")
        self.log_file = os.path.join(output_dir, "activity_log.csv")
        self.running = False
        self.activity_data = []
        self.duration = duration * 60 if duration else None  # Convert minutes to seconds

        # Browser-specific regions (approximate, may need tuning)
        self.browser_regions = {
            "chrome": (300, 80, 1000, 120),    # Chrome URL bar region (x, y, width, height)
            "safari": (300, 80, 1000, 120),    # Safari URL bar region
            "firefox": (300, 80, 1000, 120),   # Firefox URL bar region
        }

        # Create output directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.region_shots_dir, exist_ok=True)

        # Check if tesseract is available
        try:
            pytesseract.get_tesseract_version()
            self.ocr_available = True
        except Exception as e:
            print(f"Warning: OCR (pytesseract) not available: {e}")
            print("Install Tesseract OCR and pytesseract for better app/website detection.")
            print("  pip install pytesseract")
            print("  brew install tesseract (on macOS)")
            self.ocr_available = False

        # Initialize log file if it doesn't exist
        if not os.path.exists(self.log_file):
            pd.DataFrame(columns=[
                'timestamp',
                'active_window_title',
                'screenshot_path',
                'url',
                'notes'
            ]).to_csv(self.log_file, index=False)

    def capture_screenshot(self):
        """Capture a full screenshot of the current screen"""
        screenshot = ImageGrab.grab()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        screenshot.save(filepath)
        return filepath, screenshot

    def capture_menubar_region(self, full_screenshot=None):
        """Capture the top left corner where the app name appears in the menu bar"""
        if full_screenshot is None:
            full_screenshot = ImageGrab.grab()

        # Top left corner region (adjust as needed for your screen)
        # Format: (left, top, right, bottom)
        menubar_region = full_screenshot.crop((0, 0, 400, 25))

        # Save region for debugging purposes
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"menubar_{timestamp}.png"
        filepath = os.path.join(self.region_shots_dir, filename)
        menubar_region.save(filepath)

        # Extract text if OCR is available
        if self.ocr_available:
            try:
                # Convert to grayscale and apply some preprocessing for better OCR
                menubar_np = np.array(menubar_region)
                gray = cv2.cvtColor(menubar_np, cv2.COLOR_BGR2GRAY)

                # Extract text
                text = pytesseract.image_to_string(gray).strip()

                # Clean up text - get the first part which is usually the app name
                if text:
                    app_name = text.split('\n')[0].strip()
                    return app_name, filepath
            except Exception as e:
                print(f"OCR error on menubar: {e}")

        return "Unknown App", filepath

    def is_browser(self, app_name):
        """Check if the app is a known web browser"""
        browsers = ["chrome", "safari", "firefox", "edge", "brave", "opera"]
        return any(browser in app_name.lower() for browser in browsers)

    def capture_url_bar(self, app_name, full_screenshot=None):
        """Capture the URL bar region for web browsers"""
        if full_screenshot is None:
            full_screenshot = ImageGrab.grab()

        # Determine which browser region to use
        region = None
        for browser_name, browser_region in self.browser_regions.items():
            if browser_name in app_name.lower():
                x, y, w, h = browser_region
                region = (x, y, x+w, y+h)
                break

        # Use a default region if specific browser not identified
        if region is None:
            # Default URL bar region
            region = (300, 80, 1300, 120)

        # Crop the URL bar region
        url_bar = full_screenshot.crop(region)

        # Save region for debugging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"urlbar_{timestamp}.png"
        filepath = os.path.join(self.region_shots_dir, filename)
        url_bar.save(filepath)

        # Extract text if OCR is available
        if self.ocr_available:
            try:
                # Preprocess image for better OCR
                url_np = np.array(url_bar)
                gray = cv2.cvtColor(url_np, cv2.COLOR_BGR2GRAY)

                # Extract text
                text = pytesseract.image_to_string(gray).strip()

                # Look for URL patterns (simple approach)
                lines = text.split('\n')
                for line in lines:
                    if '.com' in line or '.org' in line or '.net' in line or '.edu' in line or 'http' in line:
                        return line, filepath

                return text, filepath
            except Exception as e:
                print(f"OCR error on URL bar: {e}")

        return "Unknown URL", filepath

    def log_activity(self, timestamp, window_title, screenshot_path, url="", notes=""):
        """Log the current activity to the dataframe"""
        self.activity_data.append({
            'timestamp': timestamp,
            'active_window_title': window_title,
            'screenshot_path': screenshot_path,
            'url': url,
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

    def show_terminal_status(self, active=True, count=0, elapsed=0, total=0):
        """Show status in the terminal"""
        if active:
            remaining = ""
            if total > 0:
                remaining_sec = max(0, total - elapsed)
                remaining = f" - {remaining_sec/60:.1f}min remaining"

            print(f"\r🔴 Recording... ({count} captures{remaining})", end="")
        else:
            print("\r⚫ Recording stopped                      ")

    def monitor_loop(self):
        """Main monitoring loop"""
        start_time = time.time()
        capture_count = 0

        while self.running:
            try:
                # Check if duration has elapsed
                current_time = time.time()
                elapsed_time = current_time - start_time

                if self.duration and (elapsed_time >= self.duration):
                    print(f"\nMonitoring duration of {self.duration/60:.1f} minutes completed.")
                    self.running = False
                    break

                # Show terminal status
                self.show_terminal_status(
                    active=True,
                    count=capture_count,
                    elapsed=elapsed_time,
                    total=self.duration
                )

                # Get current timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Capture full screenshot
                screenshot_path, full_screenshot = self.capture_screenshot()

                # Capture and analyze menubar to identify app
                app_name, _ = self.capture_menubar_region(full_screenshot)

                # For browsers, also capture URL bar
                url = ""
                if self.is_browser(app_name):
                    url, _ = self.capture_url_bar(app_name, full_screenshot)

                # Generate a more informative window title
                if url and "Unknown URL" not in url:
                    window_title = f"{app_name} - {url}"
                else:
                    window_title = app_name

                # Log the activity
                self.log_activity(timestamp, window_title, screenshot_path, url)

                # Increment capture count
                capture_count += 1

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
        self.show_terminal_status(active=False)
        print("\nMonitoring stopped. Data saved.")

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

    def analyze_data(self):
        """Analyze the collected data and return a summary"""
        if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
            return "No data available for analysis."

        data = pd.read_csv(self.log_file)

        # Basic analysis
        total_records = len(data)

        if total_records == 0:
            return "No data available for analysis."

        unique_apps = data['active_window_title'].nunique()
        time_span = pd.to_datetime(data['timestamp'])

        if len(time_span) < 2:
            return "Not enough data for analysis. Only one record found."

        total_time = (time_span.max() - time_span.min()).total_seconds() / 3600  # in hours

        # App usage breakdown
        app_usage = data['active_window_title'].value_counts()
        app_percentage = (app_usage / total_records * 100).round(2)

        # Identify top domains for web browsing
        urls = data['url'].dropna().astype(str)
        domains = []
        for url in urls:
            if not url or url == "nan" or url == "Unknown URL":
                continue

            # Extract domain from URL (simple approach)
            domain = url.lower()
            for prefix in ["http://", "https://", "www."]:
                if domain.startswith(prefix):
                    domain = domain[len(prefix):]

            # Get the domain part (before first /)
            if "/" in domain:
                domain = domain.split("/")[0]

            domains.append(domain)

        # Top domains
        domain_counts = pd.Series(domains).value_counts()

        # Format results
        results = f"Screen Activity Analysis:\n"
        results += f"- Monitoring period: {total_time:.2f} hours\n"
        results += f"- Total records: {total_records}\n"
        results += f"- Unique applications/websites: {unique_apps}\n\n"

        results += "Top 5 applications/websites by usage:\n"
        for app, pct in app_percentage.head(5).items():
            results += f"- {app}: {pct}%\n"

        if not domain_counts.empty:
            results += "\nTop 5 web domains visited:\n"
            for domain, count in domain_counts.head(5).items():
                results += f"- {domain}: {count} times\n"

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
