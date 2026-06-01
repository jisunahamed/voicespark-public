$env:USE_SQLITE='true'
$env:DEBUG='true'
$env:ALLOWED_HOSTS='localhost,127.0.0.1,testserver'
$env:GEMINI_API_KEY='AIzaSyAkU6UOxkQx8kLg9akENqXL5_wo9h6OGTw'
Set-Location 'D:\\voice-spark\\Voice-Spark-AI-combined\backend'
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --noreload
