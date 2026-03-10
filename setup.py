"""
Setup script for EduGuard
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="eduguard",
    version="1.0.0",
    description="AI-powered parental control system for Edubuntu",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="EduGuard Team",
    python_requires=">=3.8",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "psutil>=5.9.0",
        "APScheduler>=3.10.0",
        "PyYAML>=6.0",
        "ollama>=0.3.0",
        "Flask>=3.0.0",
        "Flask-WTF>=1.2.0",
        "Werkzeug>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "eduguard-daemon=eduguard.daemon.daemon:main",
            "eduguard-dashboard=eduguard.dashboard.app:run_dashboard",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
