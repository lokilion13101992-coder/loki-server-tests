# AGENTS.md — Знания о сервере Loki

## Инфраструктура

- ОС: Ubuntu 24.04.4 LTS, ядро 6.8.0-117-generic (обновлено 2026-05-16, требуется reboot)
- CPU: 4 ядра AMD EPYC 7763, RAM: 7.7 GiB, Диск: 79G (41%)
- IP: 149.154.65.75, VPN: AmneziaWG (awg0, 10.66.66.1, port 58018)
- Хостнейм: loki.lion.13.10.1992.fvds.ru
- tuned: throughput-performance
- swappiness: 10

## Сервисы

| Сервис | Порт | Доступ | Примечание |
|--------|------|--------|------------|
| Nexus Core API | 8000 | localhost only | FastAPI, MemoryMax=5G, CPUQuota=80% |
| Loki Dashboard | 8080 | localhost | FastAPI, MemoryMax=256M |
| Loki Bot | — | systemd | Telegram bot, MemoryMax=512M |
| PostgreSQL 16 | 5432 | localhost only | nexus:nexuspass@/nexusdb |
| Redis 7 | 6379 | localhost only | |
| Qdrant | 6333 | localhost only | Vector DB |
| MySQL 8.0.45 | 3306 | localhost | credentials in /root/.my.cnf |
| Nginx | 80/443 | 0.0.0.0 | Reverse proxy, gzip, worker_connections=4096 |
| ISPmanager | 1500 | 0.0.0.0 | Панель управления |
| UFW | — | active | deny incoming, закрыты 8000,3001,21 |
| Fail2ban | — | active | jails: sshd, exim-isp, nginx-http-auth, nginx-botsearch, nginx-limit-req |
| Watchtower | — | healthy | Docker auto-update |
| Portainer | 9000, 9443 | 0.0.0.0 | Container management |
| Uptime Kuma | 3001 | 0.0.0.0 | Monitoring (через Nginx) |
| Netdata | 19999 | localhost | System monitoring |

## Nginx маршрутизация (3 стратегии)

### nip.io (рекомендуемый)
- `http://api.149.154.65.75.nip.io/` → Nexus Core
- `http://dash.149.154.65.75.nip.io/` → Loki Dashboard
- `http://status.149.154.65.75.nip.io/` → Uptime Kuma
- `http://portainer.149.154.65.75.nip.io/` → Portainer
- `http://monitor.149.154.65.75.nip.io/` → Netdata

### Path-based
- `http://149.154.65.75/nexus/` → Nexus Core
- `http://149.154.65.75/dashboard/` → Loki Dashboard
- `http://149.154.65.75/status/` → Uptime Kuma

### Local DNS (только с сервера)
- `http://api.loki.local/` → Nexus Core
- `http://dash.loki.local/` → Loki Dashboard
- `http://status.loki.local/` → Uptime Kuma

## Архитектура — Nexus Tree

Всё есть событие. Состояние — производное от лога событий.

```
NEXUS =
  Event Stream          ← единственная правда
+ Identity Kernel       ← кто ты, закодировано
+ Attention Engine      ← что важно сейчас
+ Memory (episodic + semantic graph)
+ Reflection Layer      ← система наблюдает за собой
+ Intent Layer          ← живые цели, не мёртвые задачи
+ Scheduler             ← реальность меняется по триггерам
+ Shield                ← защита перед исполнением
+ Learning Loop         ← система растёт
```

## Инварианты лога событий

1. ВСЁ = СОБЫТИЕ
2. СОСТОЯНИЕ = ПРОИЗВОДНАЯ(ЛОГ СОБЫТИЙ)
3. LLM = ФУНКЦИЯ РЕШЕНИЙ, НЕ ПРАВДА
4. ПАМЯТЬ = ИНДЕКС ПО СОБЫТИЯМ

## Пути

- Nexus core: /root/nexus-core/
- Nexus API: /root/nexus-core/api/local_llm_server.py
- Модель: /root/nexus-core/models/mistral/openhermes-2.5-mistral-7b.Q4_K_M.gguf
- Бэкапы: /backup/
- MySQL credentials: /root/.my.cnf
- Hermes home: ~/.hermes/
- SOUL.md: ~/.hermes/SOUL.md
- Тесты: /root/nexus-core/tests/
- Логи: /var/log/loki/
- Nginx конфиги: /etc/nginx/conf.d/

## Безопасность

- SSH: только ключи, без root login, без паролей
- UFW: deny incoming, открыты только нужные порты (80, 443, 22, 1500, почтовые, 53, 9000, 9443)
- PostgreSQL/Redis/Qdrant: только localhost (127.0.0.1)
- Бэкапы: ежедневно в 3:00, хранятся 7 дней
- tirith: мониторинг опасных команд в реальном времени
- fail2ban: 5 jails активных

## GitHub

- Репозиторий: lokilion13101992-coder/loki-server-tests
- URL: https://github.com/lokilion13101992-coder/loki-server-tests
- Тесты: pytest suite

## История изменений

- 2026-05-16: Полная ревизия и оптимизация сервера
  - Обновлено ядро 6.8.0-111 → 6.8.0-117
  - Nginx: gzip, worker_connections 4096, proxy_timeout 300s
  - UFW: закрыты порты 8000, 3001, 21
  - MySQL пароль перенесён в .my.cnf
  - Systemd: MemoryMax/CPUQuota для Nexus, Bot, Dashboard
  - Docker: очистка dangling volumes и лишних образов
  - Fail2ban: +3 nginx jails
  - tuned: throughput-performance
  - swappiness: 10
