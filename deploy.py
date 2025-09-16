#!/usr/bin/env python3
"""
Deployment script for Hospital Billing System
Run this to start the server for testing
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        return False
    return True

def check_files():
    """Check if all necessary files exist"""
    required_files = [
        'app.py',
        'hospital_billing_interface.html',
        'requirements.txt',
        'src/billing_engine.py',
        'src/billing_adapter.py',
        'src/Insurance_main.py',
        'src/InsuranceDataAdapter.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found")
    return True

def create_directories():
    """Create necessary directories"""
    dirs = ['uploads', 'reports', 'src']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ Directories created")

def get_local_ip():
    """Get local IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "localhost"

def start_server():
    """Start the Flask server"""
    print("\n🚀 Starting Hospital Billing System Server...")
    print("=" * 50)
    
    local_ip = get_local_ip()
    
    print(f"🌐 Server will be available at:")
    print(f"   Local:    http://localhost:5000")
    print(f"   Network:  http://{local_ip}:5000")
    print("\n📱 For sir to access from his laptop:")
    print(f"   Share this URL: http://{local_ip}:5000")
    print("\n💡 Make sure both computers are on the same network!")
    print("=" * 50)
    print("\n📝 Server logs will appear below...")
    print("🛑 Press Ctrl+C to stop the server\n")
    
    try:
        # Import and run the Flask app
        from app import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

def main():
    print("🏥 Hospital Billing System - Deployment Script")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        return
    
    # Check files
    if not check_files():
        print("❌ Missing files. Please ensure all project files are present.")
        return
    
    # Create directories
    create_directories()
    
    # Install requirements
    if not install_requirements():
        return
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()