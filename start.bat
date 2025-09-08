@echo off
REM 🚀 БЫСТРЫЙ ЗАПУСК СИСТЕМЫ AGATHA для Windows
REM =============================================

echo 🚀 ЗАПУСК СИСТЕМЫ AGATHA
echo ========================

REM Переходим в директорию скрипта
cd /d "%~dp0"

REM Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

REM Проверяем виртуальное окружение
if not exist "venv\" (
    echo ⚠️ Виртуальное окружение не найдено
    echo 💡 Создайте его: python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Проверяем config.env
if not exist "config.env" (
    echo ❌ Файл config.env не найден!
    echo 💡 Создайте config.env с необходимыми переменными
    pause
    exit /b 1
)

echo 🔧 Настраиваем окружение...

REM Активируем виртуальное окружение
call venv\Scripts\activate.bat

REM Загружаем переменные из config.env (упрощенная версия)
for /f "usebackq tokens=1,2 delims==" %%a in ("config.env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

echo ✅ Окружение настроено

REM Запускаем полную систему
echo 🚀 Запускаем полную систему...
python start_agatha.py

pause
