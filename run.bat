@echo off
echo Starting DebateX...
echo.

REM Start backend
echo Starting backend on http://localhost:8001...
start "DebateX Backend" cmd /c "uv sync && uv run python -m backend.main"

REM Wait a bit for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend
echo Starting frontend on http://localhost:5173...
start "DebateX Frontend" cmd /c "cd frontend && npm install && npm run dev"

echo.
echo DebateX is starting!
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo.
echo Close the newly opened windows to stop the servers.
pause
