#!/bin/bash
# EATS CLI Setup Script

echo "================================"
echo "EATS CLI Setup"
echo "================================"
echo

# Create symlink for easy access
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "1. Creating 'eats' command..."
if [ -L /usr/local/bin/eats ]; then
    echo "   Removing existing symlink..."
    sudo rm /usr/local/bin/eats
fi

sudo ln -s "$SCRIPT_DIR/eats_cli.py" /usr/local/bin/eats
echo "   ✓ Created: /usr/local/bin/eats"

# Initialize configuration
echo
echo "2. Initializing configuration..."
python3 "$SCRIPT_DIR/eats_cli.py" config init

# Check for Ollama
echo
echo "3. Checking for Ollama..."
if command -v ollama &> /dev/null; then
    echo "   ✓ Ollama is installed"

    # Check if codellama is available
    if ollama list | grep -q codellama; then
        echo "   ✓ codellama model available"
    else
        echo "   ⚠ codellama not found. Install with:"
        echo "     ollama pull codellama"
    fi
else
    echo "   ✗ Ollama not found"
    echo "   Install from: https://ollama.ai/"
fi

# Summary
echo
echo "================================"
echo "Setup Complete!"
echo "================================"
echo
echo "Next steps:"
echo
echo "1. Configure API keys (if using Claude Code or Codex):"
echo "   eats config set api_keys.anthropic YOUR_KEY"
echo "   eats config set api_keys.openai YOUR_KEY"
echo
echo "2. Start using EATS:"
echo "   eats list workflows"
echo "   eats run code-review --file mycode.py"
echo
echo "3. Read the guide:"
echo "   cat docs/CLI_GUIDE.md"
echo
