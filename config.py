import os

TOKEN = os.environ.get("BOT_TOKEN")
# Сюда мы вставим ссылку из n8n (Webhook URL) на следующем этапе
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://example.com")
