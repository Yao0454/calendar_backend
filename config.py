import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-vl:30b")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5522"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))
