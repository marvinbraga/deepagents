#!/bin/bash
# Script to export environment variables from .env file
# Usage: source load_env.sh [path/to/.env]

# Default to the deepagents-cli .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$SCRIPT_DIR/.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    return 1 2>/dev/null || exit 1
fi

# Export variables from .env file
# - Ignores comments (lines starting with #)
# - Ignores empty lines
# - Handles values with spaces (quoted values)
set -a
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # Remove leading/trailing whitespace
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    # Skip if line doesn't contain =
    [[ "$line" != *"="* ]] && continue

    # Export the variable
    export "$line"
done < "$ENV_FILE"
set +a

# echo "Environment variables loaded from $ENV_FILE"
