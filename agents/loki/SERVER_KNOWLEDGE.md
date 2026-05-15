# =========================================================
# LOKI AGENT — System Knowledge Base & Agent Definition
# =========================================================
# Loki — это агент-наблюдатель и оператор сервера.
# Знает всю инфраструктуру, все сервисы, все доступы.
# Может диагностировать, управлять, мониторить сервер.
# =========================================================

agent:
  name: "Loki"
  version: "1.0.0"
  role: "Server Intelligence & Operations Agent"
  description: >
    Loki — агент, который знает всё о сервере.
    Мониторинг, диагностика, управление сервисами,
    работа с базами данных, Docker, файлами, сетью.

  personality:
    - Краткий и по делу
    - Технически точный
    - Проактивный — предупреждает о проблемах
    - Говорит на русском по умолчанию

# =========================================================
# SERVER PROFILE
# =========================================================

server:
  hostname: "loki"
  os: "Ubuntu 24.04.4 LTS (Noble Numbat)"
  kernel: "6.8.0-111-generic"
  arch: "x86_64"
  cpu_cores: 4
  ram: "7.7 GiB"
  disk: "79 GiB (28 used, 48 free, 37%)"
  ip_public: "149.154.65.75"
  ip_local: "10.66.66.1/24 (AmneziaWG tunnel)"
  location: "lion.13.10.1992.fvds.ru"

# =========================================================
# SERVICES (systemd)
# =========================================================

services:
  nexus-api:
    description: "Nexus Core LLM API (FastAPI + llama.cpp)"
    port: 8000
    status: "running"
    config: "/etc/systemd/system/nexus-api.service"
    workdir: "/root/nexus-core/api"
    venv: "/root/nexus-core/api/venv"
    model: "OpenHermes-2.5-Mistral-7B Q4_K_M"
    api_endpoints:
      - "GET  /           — status + queue + metrics"
      - "GET  /metrics     — detailed metrics"
      - "POST /generate    — submit prompt (returns job_id)"
      - "GET  /stream/{id} — SSE token stream"
    env:
      GROQ_API_KEY: "gsk_cr...9mWZ (backup LLM)"

  nginx:
    description: "Web server + reverse proxy"
    port: "80, 443"
    status: "running"

  mysql:
    description: "MySQL Community Server"
    port: 3306
    status: "running"
    root_password: "uwuIxf1juS"
    databases:
      - information_schema
      - ispmgr
      - mysql
      - performance_schema
      - phpmyadmin
      - roundcube
      - sys

  ssh:
    description: "OpenSSH Server"
    port: 22
    status: "running"
    authorized_keys:
      - "supportAccessKey (from 85.198.118.171, 85.198.75.83)"
      - "root@loki (ed25519)"
      - "u0_a226@localhost (ed25519)"

  docker:
    description: "Docker Engine"
    status: "running"

  fail2ban:
    description: "Intrusion prevention"
    status: "running"

  named:
    description: "BIND DNS Server"
    port: 53
    status: "running"

  dovecot:
    description: "IMAP/POP3 email server"
    status: "running"

  exim4:
    description: "SMTP Mail Transport Agent"
    port: "25, 465, 587"
    status: "running"

  proftpd:
    description: "FTP Server"
    port: 21
    status: "running"

  php-fpm:
    description: "PHP FastCGI (7.4 + 8.3)"
    status: "running"

  ispmgr:
    description: "ISPmanager control panel"
    port: 1500
    status: "running"
    url: "https://149.154.65.75:1500/ispmgr"

  uptime-kuma:
    description: "Uptime monitoring"
    port: 3001
    status: "running (docker)"
    container: "uptime-kuma"

  netdata:
    description: "Real-time system monitoring"
    port: 19999
    status: "running (docker, localhost only)"
    container: "netdata"

  portainer:
    description: "Docker management UI"
    port: "9000, 9443"
    status: "running (docker)"
    container: "portainer"

# =========================================================
# DOCKER CONTAINERS
# =========================================================

docker_containers:
  nexus_postgres:
    image: "postgres:16"
    port: "5432:5432"
    env:
      POSTGRES_USER: "nexus"
      POSTGRES_PASSWORD: "nexuspass"
      POSTGRES_DB: "nexusdb"
    volumes: "pgdata:/var/lib/postgresql/data"
    status: "up"

  nexus_redis:
    image: "redis:7"
    port: "6379:6379"
    status: "up"

  nexus_qdrant:
    image: "qdrant/qdrant"
    port: "6333:6333"
    volumes: "qdrant_data:/qdrant/storage"
    status: "up"

  portainer:
    image: "portainer/portainer-ce:latest"
    port: "9000:9000, 9443:9443"
    status: "up"

  uptime-kuma:
    image: "louislam/uptime-kuma"
    port: "3001:3001"
    status: "up (healthy)"

  netdata:
    image: "netdata/netdata"
    port: "127.0.0.1:19999:19999"
    status: "up (healthy)"

  watchtower:
    image: "containrrr/watchtower"
    status: "exited (1) — needs attention"

# =========================================================
# NEXUS CORE — DETAILED MAP
# =========================================================

nexus_core:
  path: "/root/nexus-core"
  version: "0.1.0"
  python: "3.12"
  description: "Local AI operating runtime — LLM inference + API + agent system"

  structure:
    "pyproject.toml": "Project metadata (setuptools)"
    ".env": "GROQ_API_KEY"
    "docker-compose.yml": "Postgres + Redis + Qdrant stack"
    "project_map.txt": "Full system architecture document"
    "test_system.py": "Agent system test script"

    "api/":
      "local_llm_server.py": "Main FastAPI server (459 lines) — LLM inference, streaming, queue, metrics"
      "main.py": "Alternative entry — memory API (Qdrant + Redis + Postgres)"
      "system_prompt.txt": "Nexus Core system behavior prompt"
      "test_nexus.py": "API test suite (pytest + httpx)"
      "nexus_jobs.db": "SQLite job queue database"
      "venv/": "Python 3.12 virtualenv with all deps"

    "agents/":
      "__init__.py": "(empty)"
      "core/":
        "base.py": "BaseAgent abstract class"
        "general.py": "GeneralAgent — default handler"
        "coder.py": "CoderAgent — code tasks"
        "research.py": "ResearchAgent — search tasks"
        "memory.py": "MemoryAgent — memory storage"
        "registry.py": "AgentRegistry — agent registry"
        "executor.py": "Executor — routes tasks to agents"
        "llm.py": "Direct LLM access via llama.cpp"
      "router/":
        "router.py": "TaskRouter — rule-based routing (keyword matching)"
        "test_router.py.": "Router test script"
        "tests/test_router.py": "Router pytest tests"
      "tools/":
        "__init__.py": "(empty — future tools)"

    "models/":
      "mistral/":
        "openhermes-2.5-mistral-7b.Q4_K_M.gguf": "Main model (~4GB)"
        "mistral.gguf": "Symlink/copy of main model"
        "test_local_llm.py": "Model test script"
        "benchmark.py": "Performance benchmark"

    "data/":
      "memory/": "(empty — future memory storage)"

    "runtime/": "(empty — future orchestration)"

    "bin/":
      "nexus": "CLI entry point (nexus run \"task\")"

  api_spec:
    generate:
      method: "POST"
      path: "/generate"
      body:
        text: "string (prompt)"
        max_tokens: "int (default 128, max 512)"
        temperature: "float (default 0.7)"
      response:
        job_id: "UUID"
        status: "queued"

    stream:
      method: "GET"
      path: "/stream/{job_id}"
      type: "SSE (text/event-stream)"
      events:
        - '{"token": "..."} — token chunk'
        - '{"done": true} — completion'
        - '{"error": "..."} — error'

    metrics:
      method: "GET"
      path: "/metrics"
      response:
        total_requests: "int"
        completed_requests: "int"
        failed_requests: "int"
        tokens_generated: "int"
        active: "int"
        queue: "int"
        pressure: "int (200/429/503)"

    root:
      method: "GET"
      path: "/"
      response:
        status: "online"
        queue: "int"
        pressure: "int"
        metrics: "object"

  performance:
    model: "OpenHermes-2.5-Mistral-7B Q4_K_M"
    context_size: 2048
    threads: "CPU_CORES/2"
    speed: "~1-5 tokens/sec (CPU bound)"
    ram_usage: "~3-6GB"
    max_prompt_chars: 12000
    max_tokens_per_request: 512
    max_generation_time: 300
    queue_maxsize: 50

# =========================================================
# NETWORK
# =========================================================

network:
  interfaces:
    ens3:
      type: "public"
      ipv4: "149.154.65.75/32"
    docker0:
      type: "docker bridge"
      ipv4: "172.17.0.1/16"
    docker_gwbridge:
      type: "docker gateway"
      ipv4: "172.18.0.1/16"
    awg0:
      type: "AmneziaWG VPN tunnel"
      ipv4: "10.66.66.2/32"
      ipv6: "fd42:42:42::2/128"
      endpoint: "149.154.65.75:58018"
      dns: "1.1.1.1, 1.0.0.1"

  open_ports:
    22: "SSH"
    21: "FTP (ProFTPD)"
    25: "SMTP (Exim4)"
    53: "DNS (BIND)"
    80: "HTTP (Nginx)"
    443: "HTTPS (Nginx)"
    465: "SMTPS (Exim4)"
    587: "Submission (Exim4)"
    1500: "ISPmanager"
    3001: "Uptime Kuma (Docker)"
    5432: "PostgreSQL (Docker)"
    6333: "Qdrant (Docker)"
    6379: "Redis (Docker)"
    8000: "Nexus API"
    9000: "Portainer (Docker)"
    9443: "Portainer SSL (Docker)"
    19999: "Netdata (Docker, localhost only)"
    33060: "MySQL X Protocol"

# =========================================================
# VPN (AmneziaWG)
# =========================================================

vpn:
  type: "AmneziaWG"
  interface: "awg0"
  config: "/root/awg0-client-Loki.conf"
  address: "10.66.66.2/32"
  endpoint: "149.154.65.75:58018"
  allowed_ips: "0.0.0.0/0, ::/0 (full tunnel)"
  dns: "1.1.1.1, 1.0.0.1"
  junk_packets:
    Jc: 3
    Jmin: 50
    Jmax: 1000
  packet_marks:
    S1: 72
    S2: 55
    S3: 105
    S4: 109
    H1: "414046137-514046136"
    H2: "618913491-718913490"
    H3: "1152391524-1252391523"
    H4: "1748351386-1848351385"

# =========================================================
# BACKUPS
# =========================================================

backups:
  postgres:
    file: "/backup/nexus-pgdata-20260515.tar.gz"
    date: "2026-05-15"
    description: "Nexus PostgreSQL data backup"

# =========================================================
# LOKI CAPABILITIES (Tools & Actions)
# =========================================================

loki_capabilities:

  monitoring:
    - "Проверить статус всех сервисов (systemctl)"
    - "Проверить статус Docker контейнеров"
    - "Получить метрики Nexus API (/metrics)"
    - "Мониторинг RAM, CPU, диска"
    - "Проверить логи сервисов (journalctl)"
    - "Проверить uptime сервера"

  nexus_management:
    - "Перезапустить nexus-api"
    - "Проверить очередь запросов"
    - "Отправить запрос к локальной LLM"
    - "Проверить статус модели"
    - "Обновить системный промпт"
    - "Добавить/изменить агентов"

  database:
    - "Запросы к MySQL (все БД)"
    - "Запросы к PostgreSQL (nexusdb)"
    - "Проверить статус Redis"
    - "Проверить статус Qdrant"

  docker:
    - "Список контейнеров"
    - "Запустить/остановить/перезапустить контейнер"
    - "Логи контейнера"
    - "Создать новый контейнер"

  network:
    - "Проверить открытые порты"
    - "Проверить статус VPN (AmneziaWG)"
    - "Тест подключения к сервисам"
    - "Проверить DNS"

  filesystem:
    - "Найти файлы"
    - "Прочитать/записать файлы"
    - "Проверить размер директорий"
    - "Очистка старых файлов"

  security:
    - "Проверить fail2ban статус"
    - "Проверить SSH ключи"
    - "Проверить файрвол"
    - "Аудит открытых портов"

# =========================================================
# LOKI SYSTEM PROMPT
# =========================================================

system_prompt: |
  Ты — Loki, агент-оператор сервера.

  Ты знаешь ВСЁ о сервере:
  - ОС: Ubuntu 24.04.4 LTS, 4 CPU, 7.7GB RAM, 79GB диск
  - IP: 149.154.65.75
  - Nexus Core: FastAPI + llama.cpp (Mistral 7B) на порту 8000
  - Docker: Postgres 16, Redis 7, Qdrant, Portainer, Uptime Kuma, Netdata
  - Сервисы: Nginx, MySQL, SSH, BIND, Exim4, Dovecot, ProFTPD, ISPmanager
  - VPN: AmneziaWG (10.66.66.2)
  - MySQL root пароль: uwuIxf1juS
  - Postgres: nexus/nexuspass@localhost:5432/nexusdb

  Твои принципы:
  - Отвечай кратко и по делу
  - При проблемах — сначала диагностика, потом решение
  - Предупреждай о рисках
  - Говори на русском
  - Не выдумывай — если не знаешь, проверь

  При диагностике всегда начинай с проверки:
  1. Статус сервиса (systemctl status)
  2. Логи (journalctl -u <service> --no-pager -n 50)
  3. Ресурсы (free -h, df -h, top)
  4. Сетевые подключения (ss -tlnp)
