#!/usr/bin/env python3
"""Setup script for the Multi-Language LSP Interface package."""

import sys

from setuptools import find_packages, setup

# Read version from the package
with open("multilsp/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "0.0.0"

# Read long description from README
with open("README.md") as f:
    long_description = f.read()

# Display warning about external dependencies
print("""
IMPORTANT: This package requires external dependencies that cannot be installed via pip:
- For JavaScript/TypeScript support: Node.js packages installed via npm
- For Java support: JDK and various JAR files

Please refer to the README.md for complete installation instructions.
""", file=sys.stderr)

setup(
    name="multilsp",
    version=version,
    description="Multi-Language LSP Interface for code navigation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/multilsp",
    packages=find_packages(),
    install_requires=[
        "pygls>=1.1.0",
        "python-lsp-server>=1.7.0",
        "jedi>=0.18.0",
        "pyright>=1.1.316",
        "pylint>=2.17.0",
        "black>=23.3.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
    ],
    entry_points={
        "console_scripts": [
            "multilsp=multilsp.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
