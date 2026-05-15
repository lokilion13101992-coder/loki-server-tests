# =========================================================
# LOKI TELEGRAM BOT — ИНСТРУКЦИЯ ПО НАСТРОЙКЕ
# =========================================================

## ПРОБЛЕМА
api.telegram.org заблокирован на уровне сети провайдера.
Бот не может подключиться к Telegram API напрямую.

## РЕШЕНИЕ — Cloudflare Worker (бесплатно)

### Шаг 1: Создай воркер
1. Перейди на https://workers.cloudflare.com
2. Создай новый воркер (Sign Up / Log In)
3. Вставь этот код:

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = 'api.telegram.org';
    return fetch(url, request);
  }
};
```

4. Нажми "Save and Deploy"
5. Скопируй URL воркера (вида: https://loki-telegram-proxy.твой-логин.workers.dev)

### Шаг 2: Проверь прокси
На сервере выполни:

curl -s "https://loki-telegram-proxy.твой-логин.workers.dev/bot8680097904:AAGVyCHOMCTu6gvCbeWj5dMZCSMmjGaihag/getMe"

Если получишь JSON с информацией о боте — прокси работает.

### Шаг 3: Запусти бота
/root/nexus-core/bin/loki-bot "https://loki-telegram-proxy.твой-логин.workers.dev"

Или с переменной окружения:
TELEGRAM_API_FALLBACK=https://loki-telegram-proxy.твой-логин.workers.dev /root/nexus-core/bin/loki-bot

### Шаг 4: Добавь systemd сервис
sudo cp /root/nexus-core/agents/loki/loki-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable loki-bot
sudo systemctl start loki-bot

## АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ

### SOCKS5 прокси
Если есть SOCKS5 прокси:
TELEGRAM_PROXY=socks5://user:pass@host:1080 /root/nexus-core/bin/loki-bot

### Веб-дашборд (работает без прокси)
http://149.154.65.75:8080

## ФАЙЛЫ
- Бот: /root/nexus-core/agents/loki/loki_bot.py
- CLI: /root/nexus-core/bin/loki-bot
- Токен: /root/nexus-core/agents/loki/.bot_token
- Сервис: /root/nexus-core/agents/loki/loki-bot.service
