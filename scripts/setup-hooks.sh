#!/bin/bash
set -e

# Make the pre-commit script executable
chmod +x scripts/pre-commit.sh

# Set up the pre-commit hook
git_hook_dir=".git/hooks"
pre_commit_path="$git_hook_dir/pre-commit"

# Create hooks directory if it doesn't exist
mkdir -p "$git_hook_dir"

# Check if pre-commit already exists
if [ -f "$pre_commit_path" ]; then
    echo "A pre-commit hook already exists. Would you like to replace it? (y/n)"
    read -r response
    if [[ "$response" != "y" ]]; then
        echo "Aborted. Pre-commit hook was not installed."
        exit 0
    fi
fi

# Create the pre-commit hook
cat > "$pre_commit_path" << 'EOF'
#!/bin/bash
# Pre-commit hook to run Ruff checks

# Run our pre-commit script
./scripts/pre-commit.sh
EOF

# Make the hook executable
chmod +x "$pre_commit_path"

echo "Pre-commit hook has been installed successfully!"
echo "Ruff will now run automatically on Python files when you commit." 