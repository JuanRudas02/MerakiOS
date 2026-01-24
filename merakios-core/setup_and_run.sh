#!/bin/bash

# MerakiOS Unified Startup Script
# Usage: ./setup_and_run.sh

echo "========================================"
echo "🚀 MerakiOS: Iniciando Protocolo de Arranque"
echo "========================================"

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Deteniendo servicios..."
    kill $(jobs -p) 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

# 1. Backend Setup & Seeding
echo ""
echo "🔧 [1/3] Configurando Backend..."
cd backend

# Ensure critical dependencies are present
echo "📦 Instalando dependencias críticas..."
python3 -m pip install -q -r requirements.txt
python3 -m pip install -q greenlet sqlmodel psycopg2-binary passlib python-jose

# Seed Database
echo "🌱 Sembrando usuarios en Base de Datos..."
# We run this in a loop to wait for DB readiness if needed, but for now direct execution
python3 seed_users.py
if [ $? -ne 0 ]; then
    echo "❌ Error en el seeding. Revisa los logs de Docker para asegurar que la DB está corriendo."
    echo "   Intenta: docker-compose up -d db redis"
    exit 1
fi

# 2. Start Backend
echo ""
echo "🧠 [2/3] Iniciando Backend (Puerto 8001)..."
uvicorn main:app --reload --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

# 3. Start Frontend
echo ""
echo "💻 [3/3] Iniciando Frontend (Puerto 5174)..."
cd ../frontend
npm install --silent
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "✅ SISTEMA OPERATIVO"
echo "   👉 Frontend: http://localhost:5174"
echo "   👉 Backend:  http://localhost:8001"
echo "   👤 Usuario:  juan1007120484@gmail.com"
echo "   🔑 Clave:    2527Juan@"
echo "========================================"
echo "Presiona Ctrl+C para detener todo."

wait
