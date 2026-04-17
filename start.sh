#!/usr/bin/env bash
# Start both backend and frontend dev servers

echo "=== Starting KM Analyzer ==="

# Backend
cd backend
if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! Created backend/.env — add your ANTHROPIC_API_KEY"
fi

if [ ! -d .venv ]; then
  echo "Creating Python virtualenv..."
  python -m venv .venv
fi

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
pip install -r requirements.txt -q

echo "Starting FastAPI on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend
cd ../frontend
if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting Next.js on http://localhost:3000"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID" INT
wait
