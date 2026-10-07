#!/bin/bash

set -e  # stop si erreur

#test ultra rapide api key en dur :
export GROQ_API_KEY="......"
MODEL_NAME="qwen2.5:0.5b"

if ! command -v curl &> /dev/null
then
    echo "curl not found, installing..."
    sudo apt-get update -qq
    sudo apt-get install -y curl -qq
fi

if ! command -v ollama &> /dev/null
then
    echo "Ollama not found, installing..."
    curl -fsSL https://ollama.com/install.sh | sh > /dev/null
fi

ollama serve > /dev/null 2>&1 &
sleep 5

ollama pull "$MODEL_NAME" > /dev/null

pip install --upgrade pip -q
pip install Django django-crispy-forms crispy-bootstrap4 Pillow groq ollama -q

python3 manage.py runserver

