#!/usr/bin/env pwsh
# Fintech-Platform Initialization Script for Windows (PowerShell)

Write-Host "🚀 Initializing Fintech-Platform..." -ForegroundColor Green

# 1. Create directory structure
Write-Host "📁 Creating directories..." -ForegroundColor Cyan
$dirs = @(
    "frontend",
    "frontend/src/app",
    "frontend/src/components",
    "frontend/public",
    "backend",
    "backend/app",
    "backend/app/api",
    "backend/app/models",
    "backend/app/services",
    "supabase/migrations"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# 2. Create frontend/package.json
Write-Host "📦 Creating frontend/package.json..." -ForegroundColor Cyan
$frontendPackageJson = @{
    name = "fintech-frontend"
    version = "0.1.0"
    private = $true
    scripts = @{
        dev = "next dev"
        build = "next build"
        start = "next start"
        lint = "next lint"
    }
    dependencies = @{
        next = "16.0.0"
        react = "^19.0.0"
        "react-dom" = "^19.0.0"
    }
    devDependencies = @{
        "@types/node" = "^20"
        "@types/react" = "^19"
        "@types/react-dom" = "^19"
        typescript = "^5"
        tailwindcss = "^3.4.0"
        postcss = "^8"
        autoprefixer = "^10"
        eslint = "^9"
        "eslint-config-next" = "16.0.0"
    }
}

$frontendPackageJson | ConvertTo-Json -Depth 10 | Out-File -FilePath "frontend/package.json" -Encoding utf8

# 3. Create backend/pyproject.toml
Write-Host "🐍 Creating backend/pyproject.toml..." -ForegroundColor Cyan @"
[tool.poetry]
name = "fintech-backend"
version = "0.1.0"
description = "Fintech Platform Backend API"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
python-multipart = "^0.0.9"
pydantic = "^2.9.0"
sqlalchemy = "^2.0.35"
supabase = "^2.7.4"
redis = "^5.2.0"
python-dotenv = "^1.0.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
black = "^24.0.0"
isort = "^5.13.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"@ | Out-File -FilePath "backend/pyproject.toml" -Encoding utf8

# 4. Create docker-compose.yml
Write-Host "🐳 Creating docker-compose.yml..." -ForegroundColor Cyan @"
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  redis_data:
"@ | Out-File -FilePath "docker-compose.yml" -Encoding utf8

# 5. Create backend Dockerfile
Write-Host "📝 Creating backend/Dockerfile..." -ForegroundColor Cyan @"
FROM python:3.10-slim

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --no-dev

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@ | Out-File -FilePath "backend/Dockerfile" -Encoding utf8

# 6. Create backend/main.py
Write-Host "🐍 Creating backend/app/main.py..." -ForegroundColor Cyan @"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Fintech Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Fintech Platform API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
"@ | Out-File -FilePath "backend/app/main.py" -Encoding utf8

# 7. Create .gitignore
Write-Host "🔒 Creating .gitignore..." -ForegroundColor Cyan @"
# Python
__pycache__/
*.py[cod]
venv/
.env

# Node.js
node_modules/
.next/
dist/

# IDE
.vscode/
.idea/
"@ | Out-File -FilePath ".gitignore" -Encoding utf8

# 8. Create root README
Write-Host "📄 Creating README.md..." -ForegroundColor Cyan @"
# Fintech Platform

## Tech Stack
- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS
- **Backend**: Python 3.10+ + FastAPI + Poetry
- **Database**: Supabase (PostgreSQL)
- **Cache**: Redis

## Quick Start

### Backend
\`\`\`bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

### Docker
\`\`\`bash
docker-compose up
\`\`\`
"@ | Out-File -FilePath "README.md" -Encoding utf8

Write-Host ""
Write-Host "✅ Fintech-Platform initialized successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. cd backend && poetry install" -ForegroundColor White
Write-Host "  2. cd frontend && npm install" -ForegroundColor White
Write-Host "  3. docker-compose up" -ForegroundColor White
