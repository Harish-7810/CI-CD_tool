#!/usr/bin/env python3
"""
Test script for Jenkins UI installation
"""

import sys
import os
from dotenv import load_dotenv

def test_python_version():
    """Test Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python version {version.major}.{version.minor} is too old. Need 3.7+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def test_dependencies():
    """Test if all dependencies are installed"""
    required_packages = [
        'flask',
        'jenkins',
        'requests',
        'flask_cors',
        'python_dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def test_environment():
    """Test environment configuration"""
    load_dotenv()
    
    required_vars = ['JENKINS_URL', 'JENKINS_USERNAME', 'JENKINS_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\nMissing environment variables: {', '.join(missing_vars)}")
        print("Create a .env file based on env.example")
        return False
    
    return True

def test_jenkins_connection():
    """Test Jenkins connection"""
    try:
        import jenkins
        from dotenv import load_dotenv
        
        load_dotenv()
        
        jenkins_url = os.getenv('JENKINS_URL')
        username = os.getenv('JENKINS_USERNAME')
        password = os.getenv('JENKINS_PASSWORD')
        
        server = jenkins.Jenkins(jenkins_url, username=username, password=password)
        info = server.get_info()
        print(f"✅ Connected to Jenkins {info.get('version', 'Unknown')}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Jenkins: {e}")
        return False

def test_flask_app():
    """Test Flask app creation"""
    try:
        from app import app
        print("✅ Flask app created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create Flask app: {e}")
        return False

def main():
    """Run all tests"""
    print("Jenkins UI - Installation Test")
    print("=" * 30)
    
    tests = [
        ("Python Version", test_python_version),
        ("Dependencies", test_dependencies),
        ("Environment", test_environment),
        ("Jenkins Connection", test_jenkins_connection),
        ("Flask App", test_flask_app)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  {test_name} test failed")
    
    print(f"\n{'=' * 30}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Installation is complete.")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 