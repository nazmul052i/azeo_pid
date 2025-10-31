"""
Setup script for PID Tuner package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text().splitlines() 
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="pid-tuner",
    version="1.0.0",
    author="PID Tuner Development Team",
    author_email="",
    description="Comprehensive PID control library for process control applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pid-tuner",
    packages=find_packages(exclude=["tests", "docs", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "streamlit": [
            "streamlit>=1.30.0",
            "plotly>=5.18.0",
        ],
        "opc": [
            "asyncua>=1.0.0",
            # "OpenOPC",  # Optional, Windows only
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pid-tuner-streamlit=streamlit_ui.run:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pid_tuner.storage": ["schema.sql"],
    },
    zip_safe=False,
)