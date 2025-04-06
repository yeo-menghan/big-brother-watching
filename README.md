# big-brother-watching

![big bro](./public//big%20brother.jpg)

![Contributors](https://img.shields.io/github/contributors/yeo-menghan/big-brother-watching?color=dark-green) ![Issues](https://img.shields.io/github/issues/yeo-menghan/big-brother-watching) ![License](https://img.shields.io/github/license/yeo-menghan/big-brother-watching)


## 🔍 Overview
Screen Activity Monitor captures data about your active applications at regular intervals, providing insights into how you spend your time on your computer. This tool helps you:

- Track which applications you use most frequently
- Analyze your productivity patterns
- Identify potential distractions
- Visualize your screen time distribution

All data is stored locally on your machine - no data is ever sent to external servers, ensuring your privacy.

## ✨ Features
- Privacy-First Approach: All monitoring and data storage happens locally on your device
- Customizable Monitoring: Set your desired capture interval and monitoring duration
- Real-Time Progress: View monitoring progress with a live status bar
- Detailed Analysis: Summarize application usage with statistics and visualizations
- Data Export: Download your activity logs as CSV files for further analysis
- Minimal Resource Usage: Designed to run in the background with minimal impact on system performance

## 🚀 Installation
Prerequisites
- Python 3.9 or higher
- pip (Python package installer)
- Running on MAC

Setting up
```bash
# Clone the repository
git clone https://github.com/yourusername/big-brother-watching.git
cd big-brother-watching

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
```

## 💻 Usage
1. Launch the application using the command `streamlit run app.py` (currently the web-app only works locally)
2. Set the capture interval (how often to take screenshots, in seconds)
3. Set the monitoring duration (how long to monitor, in minutes)
4. Start monitoring by clicking the "Start Monitoring" button
5. View results after the monitoring period completes:
    - Application usage summary
    - Detailed activity logs
    - Visual charts and metrics
6. Export data using the download buttons for further analysis

## 📊 Example Results
After monitoring your screen activity, you'll be able to see:

- Which applications you used the most
- How much time you spent on each application
- When you were most active
- Trends in your computer usage

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add some amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 📅 Future Improvements
- Cross platform support (currently runs locally on Mac)

## 🙏 Acknowledgements
Streamlit for the amazing interface framework
OpenCV for image processing capabilities
Pandas for data analysis
