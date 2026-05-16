# Loki Server — План улучшений

## ✅ Исправлено (2026-05-16)

### 1. Watchtower — restart loop ✅
Больше не наблюдается. Watchtower healthy.

### 2. Apache2 — failed service ✅
Masked, больше не засоряет логи.

### 3. MySQL — нет автозапуска ✅
Enabled и active.

### 4. Loki Bot — работает ✅
systemd service active.

### 5. Loki Dashboard — systemd service ✅
Создан и работает.

### 6. Loki Cron — логи пишутся ✅
/var/log/loki/cron-YYYYMMDD.log обновляется.

### 7. Nginx — reverse proxy ✅
3 стратегии маршрутизации настроены.

### 8. Nginx — оптимизация ✅
- worker_connections: 768 → 4096
- gzip: включён
- proxy_timeout: 300s для LLM
- default site удалён
- multi_accept + epoll

### 9. UFW — закрыты лишние порты ✅
- 8000 (Nexus) — удалён
- 3001 (Uptime Kuma) — удалён
- 21 (FTP) — удалён

### 10. MySQL пароль ✅
Перенесён в /root/.my.cnf, убран из loki-cron.

### 11. Systemd — лимиты ресурсов ✅
- Nexus API: MemoryMax=5G, CPUQuota=80%
- Loki Bot: MemoryMax=512M, CPUQuota=30%
- Loki Dashboard: MemoryMax=256M, CPUQuota=20%

### 12. Ядро обновлено ✅
6.8.0-111 → 6.8.0-117 (потребуется reboot).

### 13. Оптимизация ядра ✅
- swappiness: 30 → 10
- tuned: throughput-performance
- journald: SystemMaxUse=500M

### 14. Docker очистка ✅
- Dangling volumes удалены
- hello-world, dockviz образы удалены
- nexus-core_default сеть пересоздана

### 15. Fail2ban расширен ✅
Добавлены jails: nginx-http-auth, nginx-botsearch, nginx-limit-req.

## Осталось сделать

### SSL — Let's Encrypt
Нужен домен. certbot --nginx -d yourdomain.com

### VPN — мониторинг
Добавить алерт если peer не подключён > 24h.

### Backup — offsite
Добавить rsync на удалённый сервер или S3.

### Log rotation для /var/log/loki/
Настроить logrotate для логов Loki.
