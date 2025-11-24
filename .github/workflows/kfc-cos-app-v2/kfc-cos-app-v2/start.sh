#!/bin/bash
echo "🍗 KFC COS Calculator v2"
echo "========================"
echo ""
echo "Pokretanje aplikacije..."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python app.py

