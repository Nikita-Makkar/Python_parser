# Tender Parser

Этот проект в рамках тестового задания для асинхронного сбора и парсинга тендерных данных с сайта https://zakupki.gov.ru

## Установка

1. Клонируйте репозиторий:
``` bash
  git clone https://github.com/Nikita-Makkar/Python_parser.git
  ```
2. Установите зависимости:
``` bash
  python -m venv venv
  source venv/bin/activate  # Для Linux/macOS
  venv\Scripts\activate  # Для Windows
  pip install -r requirements.txt
```
3. Настройте переменные окружения в файле .env 
(пример файл .env.example)

## Запуск

1. Запуск Celery Worker:
``` bush
   celery -A async_parser worker --loglevel=info
```
2. Запуск основного скрипта.
``` python
   python async_parser.py
   ```