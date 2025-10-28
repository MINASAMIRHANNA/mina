#!/bin/bash
# clean_setup.sh

echo "Cleaning up and setting up clean multi-bot trading system..."

# Stop any running containers
docker-compose down

# Remove any files that might have markdown artifacts
find . -name "*.py" -exec sed -i.bak '/^```/d' {} \;
find . -name "*.py" -exec sed -i.bak '/^```python/d' {} \;
find . -name "*.py.bak" -delete

# Create directory structure
mkdir -p templates logs data

# Create clean multi_bot_manager.py (using the corrected version above)
# ... (copy the corrected multi_bot_manager.py content here)

echo "Clean setup complete!"
echo "Starting the application..."
docker-compose up -d --build

echo "Multi-Bot Trading System started!"
echo "Dashboard: http://localhost:5002"