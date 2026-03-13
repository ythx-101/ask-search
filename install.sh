#!/bin/bash
# ask-search install script
# Installs ask-search as a global command + optionally sets up SearxNG

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_BIN="${1:-/usr/local/bin}"

echo "=== ask-search installer ==="

# Check dependencies
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required"
    exit 1
fi
if ! command -v curl &>/dev/null; then
    echo "ERROR: curl is required"
    exit 1
fi

# Install global command
echo "Installing ask-search to $INSTALL_BIN ..."

# Create wrapper with hardcoded path (single-quotes prevent $@ expansion in heredoc)
WRAPPER=$(cat << 'WRAPPEREOF'
#!/bin/bash
exec python3 "COREPATH" "$@"
WRAPPEREOF
)

# Replace placeholder with actual path
WRAPPER="${WRAPPER/COREPATH/$SCRIPT_DIR/scripts/core.py}"

# Use mktemp to prevent /tmp race condition
WRAPPER_FILE=$(mktemp)
echo "$WRAPPER" > "$WRAPPER_FILE"

install -m 755 "$WRAPPER_FILE" "$INSTALL_BIN/ask-search"
rm -f "$WRAPPER_FILE"
echo "✓ ask-search installed to $INSTALL_BIN/ask-search"

# Test
echo ""
echo "Testing connection to SearxNG at ${SEARXNG_URL:-http://localhost:8080} ..."
if python3 "$SCRIPT_DIR/scripts/core.py" "test" --num 1 &>/dev/null; then
    echo "✓ SearxNG reachable — ask-search is ready!"
else
    echo "⚠ SearxNG not reachable at ${SEARXNG_URL:-http://localhost:8080}"
    echo "  Set SEARXNG_URL env var or deploy SearxNG first."
    echo "  See README for SearxNG setup instructions."
fi

echo ""
echo "Usage: ask-search \"your query\""
