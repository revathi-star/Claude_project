"""
Hospital Management System - Quick Setup Script
This script helps set up the project structure and files
"""

import os
import sys

def create_directory(path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"✓ Created directory: {path}")
    else:
        print(f"→ Directory already exists: {path}")

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7 or higher is required!")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['flask', 'flask_login']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is NOT installed")
    
    if missing_packages:
        print("\n📦 To install missing packages, run:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    return True

def create_project_structure():
    """Create the required project structure"""
    print("\n📁 Creating project structure...")
    
    directories = [
        'templates',
        'static'
    ]
    
    for directory in directories:
        create_directory(directory)
    
    print("\n✓ Project structure created successfully!")

def show_file_checklist():
    """Display checklist of required files"""
    print("\n📋 Required Files Checklist:")
    print("\n   Root Directory:")
    print("   [ ] app.py")
    print("   [ ] setup.py (this file)")
    
    print("\n   templates/ Directory (14 files):")
    templates = [
        'base.html',
        'login.html',
        'register.html',
        'admin_dashboard.html',
        'admin_doctors.html',
        'admin_patients.html',
        'admin_appointments.html',
        'doctor_dashboard.html',
        'doctor_appointments.html',
        'doctor_availability.html',
        'complete_appointment.html',
        'patient_dashboard.html',
        'patient_profile.html',
        'search_doctors.html',
        'book_appointment.html'
    ]
    
    for template in templates:
        exists = os.path.exists(f'templates/{template}')
        status = "✓" if exists else " "
        print(f"   [{status}] {template}")
    
    print("\n   static/ Directory:")
    css_exists = os.path.exists('static/style.css')
    status = "✓" if css_exists else " "
    print(f"   [{status}] style.css")

def show_next_steps():
    """Display next steps for the user"""
    print("\n" + "="*60)
    print("🎯 NEXT STEPS")
    print("="*60)
    
    print("\n1. Ensure all files are in place (see checklist above)")
    print("\n2. If dependencies are missing, install them:")
    print("   pip install flask flask-login")
    
    print("\n3. Run the application:")
    print("   python app.py")
    
    print("\n4. Open your browser and go to:")
    print("   http://127.0.0.1:5000")
    
    print("\n5. Login with default admin credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    
    print("\n" + "="*60)
    print("📚 For more information, see README.md")
    print("="*60)

def main():
    """Main setup function"""
    print("="*60)
    print("🏥 Hospital Management System - Setup")
    print("="*60)
    
    print("\n🔍 Checking system requirements...")
    
    # Check Python version
    if not check_python_version():
        print("\n⚠️  Please upgrade Python and try again.")
        return
    
    # Check dependencies
    dependencies_ok = check_dependencies()
    
    # Create project structure
    create_project_structure()
    
    # Show file checklist
    show_file_checklist()
    
    # Show next steps
    show_next_steps()
    
    if not dependencies_ok:
        print("\n⚠️  Some dependencies are missing. Please install them first.")
    else:
        print("\n✅ Setup complete! You're ready to run the application.")

if __name__ == "__main__":
    main()