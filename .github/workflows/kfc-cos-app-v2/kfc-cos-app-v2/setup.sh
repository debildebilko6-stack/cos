#!/bin/bash
echo "🍗 KFC COS Calculator v2 - Setup"
echo "================================="

sudo apt update -qq
sudo apt install -y python3-pip python3-venv unzip wget

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start: source venv/bin/activate && gunicorn --bind 0.0.0.0:8080 app:app"
