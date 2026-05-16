# AGENTS.md — Знания о сервере Loki

## Инфраструктура

- ОС: Ubuntu 24.04.4 LTS, ядро 6.8.0-111-generic
- CPU: 4 ядра AMD EPYC 7763, RAM: 7.7 GiB, Диск: 79G
- IP: 149.154.65.75, VPN: AmneziaWG (awg0, 10.66.66.1)
- Хостнейм: loki.lion.13.10.1992.fvds.ru

## Сервисы

| Сервис | Порт | Статус | Примечание |
|--------|------|--------|------------|
| Nexus Core API | 8000 | Работает | FastAPI, pid 135089 |
| Loki Dashboard | 8080 | Работает | FastAPI, systemd: loki-dashboard |
| Loki Bot | — | Работает | Telegram bot, systemd: loki-bot |
| PostgreSQL 16 | 5432 | Up (docker) | nexus:nexuspass@/nexusdb |
| Redis 7 | 6379 | Up (docker) | localhost |
| Qdrant | 6333 | Up (docker) | Vector DB |
| MySQL 8.0.45 | 3306 | Работает | root:uwuIxf1juS, enabled |
| Nginx | 80, 443 | Работает | self-signed SSL |
| ISPmanager | 1500 | Работает | Панель управления |
| UFW | — | Active | deny incoming |
| Fail2ban | — | Active | jails: sshd, exim-isp |
| Watchtower | — | Работает | Docker auto-update, исправлен |
| Apache2 | — | Masked | Отключён, не используется |

## Архитектура — Nexus Tree

Всё есть событие. Состояние — производное от лога событий.
Файлы — листья. Логика живёт в узлах.

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

Стадии 1-2 завершены (ствол + корни). Kernel построен. Все 9 тестов зелёные.

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
- Hermes home: ~/.hermes/
- SOUL.md: ~/.hermes/SOUL.md
- Тесты: /root/nexus-core/tests/
- Логи: /var/log/loki/

## Лог решений

- v7: монолит — работал но слишком сложный
- v8: упрощение — потеряли слой контроля
- v9: архитектура — нестабильная
- v0.1 kernel: event-sourced, все тесты зелёные ✓
- 2026-05-16: исправлены все проблемы сервера (watchtower, apache2, mysql, loki bot, loki cron, ssl)

## Текущие приоритеты

1. Настроить Nginx reverse proxy для сервисов
2. Подключить лог событий Nexus к памяти Hermes
3. Настроить SSL Let's Encrypt (нужен домен)
4. Расширить fail2ban jails
5. Настроить алерты Uptime Kuma

## Безопасность

- SSH: только ключи, без root login, без паролей
- UFW: deny incoming, открыты только нужные порты
- PostgreSQL/Redis/Qdrant: закрыты извне (только localhost/docker)
- Бэкапы: ежедневно в 3:00, хранятся 7 дней

## GitHub

- Репозиторий: lokilion13101992-coder/loki-server-tests
- URL: https://github.com/lokilion13101992-coder/loki-server-tests
- Тесты: 97 pytest, все проходят
