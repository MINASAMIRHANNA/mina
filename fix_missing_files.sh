#!/bin/bash
# fix_missing_files.sh

echo "Fixing missing files in Docker container..."

# Stop current containers
docker-compose down

# Create multi_bot_manager.py with the content above
cat > multi_bot_manager.py << 'EOF'
# ... (paste the entire multi_bot_manager.py content from above)
EOF

# Check if all required files exist
echo "Checking required files:"
ls -la *.py

# Rebuild with no cache
echo "Rebuilding Docker containers..."
docker-compose build --no-cache

# Start the containers
echo "Starting containers..."
docker-compose up -d

echo "Fix complete! Check if the error is resolved:"
docker-compose logs -f trading-bot