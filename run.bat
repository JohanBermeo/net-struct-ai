@echo off
rem Asegurar que el directorio de trabajo es el del script
cd /d "%~dp0"

echo =======================================================
echo   Iniciando Motor PERT/CPM y Auditoria de IA (Qwen)
echo =======================================================
echo.

rem 1. Verificar si Ollama responde en su puerto por defecto
curl -s -I http://localhost:11434 >nul
if %errorlevel% neq 0 (
    echo [INFO] Ollama no esta activo. Iniciando servidor de Ollama en segundo plano...
    start "" /b ollama serve
    rem Esperar unos segundos a que el servidor inicialice
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] El servicio de Ollama ya se esta ejecutando.
)

rem 2. Verificar si el modelo qwen2.5:3b esta instalado
echo [INFO] Verificando instalacion del modelo qwen2.5:3b...
ollama list 2>nul | findstr /I "qwen2.5:3b" >nul
if %errorlevel% neq 0 (
    echo [WARNING] El modelo qwen2.5:3b no esta instalado localmente.
    echo [INFO] Iniciando descarga del modelo - esto puede tardar unos minutos...
    ollama pull qwen2.5:3b
) else (
    echo [OK] El modelo qwen2.5:3b ya esta disponible localmente.
)

rem 3. Gestionar entorno virtual y dependencias de Python
if not exist venv\Scripts\activate.bat (
    echo [WARNING] No se detecto el entorno virtual venv.
    echo [INFO] Creando entorno virtual venv...
    python -m venv venv
)

echo [INFO] Activando entorno virtual venv...
call venv\Scripts\activate.bat

rem Verificar si streamlit esta instalado
pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Dependencias no detectadas en el entorno virtual.
    echo [INFO] Instalando dependencias desde requirements.txt...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo [OK] Las dependencias de Python ya estan instaladas.
)

rem 4. Iniciar el frontend de Streamlit
echo [INFO] Iniciando el frontend de Streamlit...
streamlit run src/app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al ejecutar la aplicacion.
    pause
)
