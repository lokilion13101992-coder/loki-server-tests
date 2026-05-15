# Loki Server — План улучшений

## Критичные проблемы (исправить сразу)

### 1. Watchtower — restart loop
**Проблема:** Docker API version mismatch (client 1.25, min 1.44)
**Решение:**
```bash
docker stop watchtower && docker rm watchtower
docker run -d --name watchtower --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower --cleanup --interval 86400
```
**Приоритет:** Высокий (тратит ресурсы на перезапуски)

### 2. Apache2 — failed service
**Проблема:** Не используется, но пытается стартовать
**Решение:**
```bash
systemctl stop apache2
systemctl disable apache2
systemctl mask apache2
```
**Приоритет:** Средний (засоряет логи)

### 3. MySQL — нет автозапуска
**Проблема:** `systemctl is-enabled mysql` → disabled
**Решение:**
```bash
systemctl enable mysql
```
**Приоритет:** Высокий (после рестарта сервера MySQL не запустится)

## Важные улучшения

### 4. Loki Bot — не работает
**Проблема:** systemd service не найден, процесс inactive
**Решение:**
- Проверить loki-bot.service unit файл
- Настроить автозапуск через systemd
- Добавить логирование

### 5. Loki Dashboard — нет systemd service
**Проблема:** Запускается вручную, не переживает рестарт
**Решение:** Создать systemd unit файл

### 6. Loki Cron — логи не пишутся
**Проблема:** /var/log/loki/health.log и backup.log пустые
**Решение:**
- Проверить права на /var/log/loki/
- Проверить что cron скрипты работают
- Добавить логирование в stdout

### 7. SSL сертификат для Nginx
**Проблема:** Порт 443 не слушается
**Решение:**
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```
**Приоритет:** Высокий (HTTPS обязателен)

## Оптимизация

### 8. Nexus Core — 33.8% RAM
**Проблема:** Nexus Core потребляет 2.7G RAM (33.8% от 7.7G)
**Решение:**
- Рассмотреть уменьшение контекстного окна
- Добавить swap на диск (zram уже есть, но 1G используется)
- Мониторить при OOM

### 9. /tmp — 683M
**Проблема:** Много временных файлов
**Решение:**
```bash
# Добавить в cron ежедневную очистку
find /tmp -type f -mtime +3 -delete
```

### 10. Nginx — пустой конфиг
**Проблема:** sites-enabled и conf.d пустые, отдаёт дефолтную страницу
**Решение:** Настроить reverse proxy для:
- Nexus Core (8000 → api.domain.com)
- Loki Dashboard (8080 → dashboard.domain.com)
- Uptime Kuma (3001 → status.domain.com)

## Безопасность

### 11. Fail2ban — расширить jails
**Текущее:** только exim-isp, sshd
**Добавить:**
- nginx-http-auth
- nginx-botsearch
- nginx-limit-req

### 12. UFW — закрыть лишние порты
**Текущее:** открыто 8000 (Nexus) для всех
**Решение:** Ограничить доступ к 8000 только с VPN (10.66.66.0/24)

### 13. Автоматические обновления безопасности
```bash
apt install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

## Мониторинг

### 14. Настроить алерты Uptime Kuma
- Добавить все критичные сервисы в мониторинг
- Настроить Telegram/Discord уведомления

### 15. Расширить тесты
- Добавить тесты производительности (latency, throughput)
- Добавить тесты нагрузки
- Интегрировать с Uptime Kuma API

## Масштабирование (будущее)

### 16. Разделение сервисов
- Вынести БД на отдельный сервер
- Добавить Redis Sentinel для HA
- Настроить репликацию PostgreSQL

### 17. CI/CD pipeline
- Автоматический деплой при push в main
- Автоматический запуск тестов перед деплоем
- Blue-green deployment

### 18. Логирование
- Настроить ELK stack или Loki+Promtail
- Централизованное логирование всех сервисов
- Алерты на ошибки в логах
