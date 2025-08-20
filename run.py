#!/usr/bin/env python3
"""
Jenkins UI - Alternative Interface
Startup script for easy deployment
"""

import os
import sys
from dotenv import load_dotenv

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import flask
        import jenkins
        import requests
        print("✓ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if environment is properly configured"""
    load_dotenv()
    
    required_vars = ['JENKINS_URL', 'JENKINS_USERNAME', 'JENKINS_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"✗ Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file based on env.example")
        return False
    
    print("✓ Environment variables are configured")
    return True

def test_jenkins_connection():
    """Test connection to Jenkins server"""
    try:
        import jenkins
        from dotenv import load_dotenv
        
        load_dotenv()
        
        jenkins_url = os.getenv('JENKINS_URL')
        username = os.getenv('JENKINS_USERNAME')
        password = os.getenv('JENKINS_PASSWORD')
        
        server = jenkins.Jenkins(jenkins_url, username=username, password=password)
        server.get_info()
        print("✓ Successfully connected to Jenkins")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Jenkins: {e}")
        print("Please check your Jenkins URL and credentials")
        return False

def main():
    """Main startup function"""
    print("Jenkins UI - Alternative Interface")
    print("=" * 40)
    
    # Check if --test-only flag is provided
    test_only = '--test-only' in sys.argv
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test Jenkins connection
    if not test_jenkins_connection():
        if test_only:
            sys.exit(1)
        else:
            print("\nYou can still run the application, but some features may not work.")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    if test_only:
        print("✅ All tests passed!")
        sys.exit(0)
    
    # Start the application
    print("\nStarting Jenkins UI...")
    print("Access the application at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("-" * 40)
    
    # Import and run the Flask app
    from app import app
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main() 