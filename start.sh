#!/bin/bash

echo "Starting Multi-Bot Trading System with Docker Compose..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with your Binance API keys"
    exit 1
fi

# Build and start containers
docker-compose up -d --build

echo "Multi-Bot Trading System is starting up..."
echo "Dashboard will be available at: http://localhost:5002"
echo "Available Bots:"
echo "  - ScalpingBot: Traditional scalping strategy"
echo "  - NewListingBot: Buys new coin listings immediately"
echo "  - HighVolumeBot: Trades coins with high volume/scores"
echo "  - LongShortBot: ML-based long/short predictions"
echo ""
echo "To view logs: docker-compose logs -f trading-bot"
echo "To stop: ./stop.sh"