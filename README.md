# Multi-Language LSP Interface

A service that interfaces with language servers for Python, JavaScript, and Java, providing code navigation, linting, formatting, and reference finding capabilities.

## Features

- Run linter
- Run formatter
- Get definition
- Get references

## Supported Languages

- Python
- JavaScript/TypeScript
- Java

## Prerequisites

### Python Dependencies
Python 3.8+ is required along with the following Python packages:
```bash
pip install -r requirements.txt
```

### JavaScript/TypeScript Dependencies
Node.js and npm must be installed. Then install the following npm packages:
```bash
# Install TypeScript Language Server
npm install -g typescript-language-server typescript

# Install ESLint and Prettier for linting and formatting
npm install -g eslint prettier
```

### Java Dependencies
Java JDK 11+ must be installed. Additionally:

1. Eclipse JDT Language Server:
   - Download from [Eclipse JDT LS Releases](https://github.com/eclipse/eclipse.jdt.ls/releases)
   - Update the path in the code: `self.server_command = ["java", "-jar", "/path/to/eclipse.jdt.ls.jar", "--stdio"]`

2. Google Java Format:
   - Download from [Google Java Format Releases](https://github.com/google/google-java-format/releases)
   - Update the path in the code: `self.formatter_cmd = ["java", "-jar", "/path/to/google-java-format.jar"]`

3. Checkstyle:
   - Download from [Checkstyle Releases](https://github.com/checkstyle/checkstyle/releases)
   - Update the path in the code: `self.linter_cmd = ["java", "-jar", "/path/to/checkstyle.jar", "-f", "json"]`

## Installation

After installing all prerequisites:

```bash
# Install the Python package
pip install -e .
```

## Configuration

You may need to update the paths to the language servers in the code:

- For Java: Update the paths in `multilsp/servers/java_server.py`
- For JavaScript: Ensure `typescript-language-server` is in your PATH
- For Python: Ensure `pylsp` is in your PATH

## Development Setup

For development, additional tools are available:

```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

### Linting with Ruff

This project uses [Ruff](https://github.com/astral-sh/ruff) for Python linting.

To lint your code:

```bash
# Run Ruff on the entire project
ruff check .

# Run Ruff with auto-fixes
ruff check --fix .
```

### Git Hooks

To ensure code quality, you can set up Git hooks that will automatically run Ruff before each commit:

```bash
# Make the setup script executable
chmod +x scripts/setup-hooks.sh

# Install the Git hooks
./scripts/setup-hooks.sh
```

Once installed, the pre-commit hook will check your Python files with Ruff and prevent commits if any issues are found.

## Usage

```bash
python -m multilsp.service --workspace /path/to/codebase
```

Or use the CLI interface:

```bash
# Run as a server
multilsp --workspace /path/to/codebase server

# Run linter on a file
multilsp --workspace /path/to/codebase lint /path/to/file.py

# Format a file
multilsp --workspace /path/to/codebase format /path/to/file.py

# Get definition at position
multilsp --workspace /path/to/codebase definition /path/to/file.py 10 5

# Get references at position
multilsp --workspace /path/to/codebase references /path/to/file.py 10 5
```