@echo off
REM Задаём кодировку UTF-8 для корректной работы с русскими символами
chcp 65001 >nul

REM Переход в директорию скрипта
cd /d "%~dp0"

REM Логируем текущую директория для диагностики
echo Текущая директория: %CD% >> log.txt

REM Проверка наличия Python
where python >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не найден в PATH >> log.txt
    exit /b 1
)

REM Проверка наличия .venv
if not exist .venv (
    echo Ошибка: Виртуальное окружение .venv не найдено >> log.txt
    echo Создаём новое виртуальное окружение... >> log.txt
    python -m venv .venv
    if errorlevel 1 (
        echo Ошибка: Не удалось создать виртуальное окружение >> log.txt
        exit /b 1
    )
    echo Устанавливаем зависимости... >> log.txt
    call .venv\Scripts\activate
    pip install aiogram python-dotenv requests >> log.txt 2>&1
    if errorlevel 1 (
        echo Ошибка: Не удалось установить зависимости >> log.txt
        exit /b 1
    )
) else (
    echo Папка .venv найдена >> log.txt
    REM Пропускаем активацию, если уже активировано
    if not defined VIRTUAL_ENV (
        call .venv\Scripts\activate
        if errorlevel 1 (
            echo Ошибка: Не удалось активировать виртуальное окружение >> log.txt
            exit /b 1
        )
    ) else (
        echo Виртуальное окружение уже активировано: %VIRTUAL_ENV% >> log.txt
    )
)

REM Проверка, активировано ли окружение
echo Текущая среда: %VIRTUAL_ENV% >> log.txt

REM Выводим индикаторную надпись в консоль
echo Кот запущен, но его в темноте не видно

REM Запуск Python-скрипта
echo Запуск generateYART.py... >> log.txt
python generateYART.py >> log.txt 2>&1
if errorlevel 1 (
    echo Ошибка: Не удалось выполнить generateYART.py >> log.txt
    exit /b 1
)
