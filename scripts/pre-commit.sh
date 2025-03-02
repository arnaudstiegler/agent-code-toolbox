#!/bin/bash
set -e

# Get the list of staged Python files
staged_files=$(git diff --name-only --cached --diff-filter=ACM | grep '\.py$' || true)

if [ -z "$staged_files" ]; then
    echo "No Python files to check."
    exit 0
fi

echo "Running Ruff on staged Python files..."

# Create a temporary directory for exit code tracking
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

# Check each file with Ruff
echo "$staged_files" | while read -r file; do
    echo "Checking $file..."
    if ! ruff check "$file"; then
        echo "Ruff found issues in $file"
        touch "$tmp_dir/failed"
    fi
done

# If any file had issues, exit with an error
if [ -f "$tmp_dir/failed" ]; then
    echo "Ruff found issues in some files. Please fix them before committing."
    exit 1
fi

echo "All Python files passed Ruff checks!"
exit 0 