"""
LOKI AGENT — Server Intelligence & Operations Agent
Знает всё о сервере, имеет полный набор инструментов.
"""

import subprocess
import json
import os
import time
import sqlite3
import urllib.request
import urllib.error
from typing import Optional

# =========================================================
# CONFIG
# =========================================================

SERVER_IP = "149.154.65.75"
NEXUS_API = "http://localhost:8000"
MYSQL_USER = "root"
MYSQL_PASS = "uwuIxf1juS"
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "nexus"
PG_PASS = "nexuspass"
PG_DB = "nexusdb"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333


# =========================================================
# SHELL EXECUTOR
# =========================================================

def run(cmd: str, timeout: int = 30) -> dict:
    """Выполнить shell-команду, вернуть stdout/stderr/exit_code."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
            "exit_code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT", "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}


# =========================================================
# SYSTEM MONITORING
# =========================================================

def get_uptime() -> str:
    return run("uptime -p")["stdout"]

def get_load() -> str:
    return run("cat /proc/loadavg")["stdout"]

def get_ram() -> dict:
    r = run("free -h | grep -E 'Mem|Swap'")
    lines = r["stdout"].splitlines()
    result = {}
    for line in lines:
        parts = line.split()
        if parts[0].startswith("Mem"):
            result["mem_total"] = parts[1]
            result["mem_used"] = parts[2]
            result["mem_free"] = parts[3]
            result["mem_available"] = parts[6] if len(parts) > 6 else "?"
        elif parts[0].startswith("Swap"):
            result["swap_total"] = parts[1]
            result["swap_used"] = parts[2]
            result["swap_free"] = parts[3]
    return result

def get_disk() -> list:
    r = run("df -h --output=source,size,used,avail,pcent,target -x tmpfs -x devtmpfs | tail -n +2")
    disks = []
    for line in r["stdout"].splitlines():
        parts = line.split()
        if len(parts) >= 6:
            disks.append({
                "filesystem": parts[0],
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "use_percent": parts[4],
                "mount": parts[5],
            })
    return disks

def get_cpu_info() -> dict:
    r = run("nproc")
    cores = r["stdout"]
    r2 = run("cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2")
    model = r2["stdout"].strip()
    return {"cores": cores.strip(), "model": model}

def get_open_ports() -> list:
    r = run("ss -tlnp | grep LISTEN")
    ports = []
    for line in r["stdout"].splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local = parts[3]
            if ":" in local:
                port = local.rsplit(":", 1)[1]
                ports.append(port)
    return sorted(set(ports))


# =========================================================
# SERVICE MANAGEMENT
# =========================================================

def service_status(name: str) -> dict:
    r = run(f"systemctl is-active {name}")
    active = r["stdout"] == "active"
    r2 = run(f"systemctl is-enabled {name}")
    enabled = r2["stdout"] == "enabled"
    return {"name": name, "active": active, "enabled": enabled}

def service_restart(name: str) -> dict:
    r = run(f"systemctl restart {name}")
    if r["exit_code"] == 0:
        time.sleep(2)
        return service_status(name)
    return {"name": name, "error": r["stderr"]}

def service_logs(name: str, lines: int = 50) -> str:
    return run(f"journalctl -u {name} --no-pager -n {lines}")["stdout"]

def all_services_status() -> list:
    services = [
        "nexus-api", "nginx", "mysql", "ssh", "docker", "fail2ban",
        "named", "dovecot", "exim4", "proftpd", "uptime-kuma",
    ]
    return [service_status(s) for s in services]


# =========================================================
# DOCKER
# =========================================================

def docker_ps(all_containers: bool = True) -> list:
    flag = "-a" if all_containers else ""
    r = run(f"docker ps {flag} --format '{{{{.Names}}}}|{{{{.Status}}}}|{{{{.Ports}}}}'")
    containers = []
    for line in r["stdout"].splitlines():
        parts = line.split("|")
        if len(parts) >= 2:
            containers.append({
                "name": parts[0],
                "status": parts[1],
                "ports": parts[2] if len(parts) > 2 else "",
            })
    return containers

def docker_logs(container: str, lines: int = 50) -> str:
    return run(f"docker logs {container} --tail {lines}")["stdout"]

def docker_restart(container: str) -> dict:
    r = run(f"docker restart {container}")
    if r["exit_code"] == 0:
        time.sleep(2)
        return {"name": container, "status": "restarted"}
    return {"name": container, "error": r["stderr"]}

def docker_stop(container: str) -> dict:
    r = run(f"docker stop {container}")
    return {"name": container, "status": "stopped" if r["exit_code"] == 0 else "error"}

def docker_start(container: str) -> dict:
    r = run(f"docker start {container}")
    return {"name": container, "status": "started" if r["exit_code"] == 0 else "error"}

def docker_exec(container: str, cmd: str) -> dict:
    return run(f"docker exec {container} {cmd}")


# =========================================================
# NEXUS API
# =========================================================

def nexus_health() -> dict:
    try:
        req = urllib.request.urlopen(f"{NEXUS_API}/", timeout=5)
        return json.loads(req.read())
    except Exception as e:
        return {"error": str(e)}

def nexus_metrics() -> dict:
    try:
        req = urllib.request.urlopen(f"{NEXUS_API}/metrics", timeout=5)
        data = json.loads(req.read())
        # Нормализуем имена полей для совместимости
        return {
            **data,
            "queue": data.get("queue_size", data.get("queue", 0)),
            "active": data.get("active_generations", data.get("active", 0)),
        }
    except Exception as e:
        return {"error": str(e)}

def nexus_generate(prompt: str, max_tokens: int = 128, temperature: float = 0.7) -> dict:
    try:
        data = json.dumps({
            "text": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()
        req = urllib.request.Request(
            f"{NEXUS_API}/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def nexus_jobs_list() -> list:
    db_path = "/root/nexus-core/api/nexus_jobs.db"
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, status, created, updated FROM jobs ORDER BY created DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "status": r[1], "created": r[2], "updated": r[3]}
        for r in rows
    ]

def nexus_job_status(job_id: str) -> dict:
    db_path = "/root/nexus-core/api/nexus_jobs.db"
    if not os.path.exists(db_path):
        return {"error": "DB not found"}
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "status": row[1], "prompt": row[2],
            "response": row[3], "max_tokens": row[4],
            "temperature": row[5], "created": row[6], "updated": row[7],
        }
    return {"error": "job not found"}


# =========================================================
# DATABASES
# =========================================================

def mysql_query(query: str, db: str = "") -> dict:
    db_flag = f"-D {db}" if db else ""
    r = run(f'mysql -u {MYSQL_USER} -p{MYSQL_PASS} {db_flag} -e "{query}" -B')
    if r["exit_code"] == 0:
        lines = r["stdout"].splitlines()
        if lines:
            headers = lines[0].split("\t")
            rows = [line.split("\t") for line in lines[1:]]
            return {"headers": headers, "rows": rows, "count": len(rows)}
    return {"error": r["stderr"] or r["stdout"]}

def mysql_databases() -> list:
    r = mysql_query("SHOW DATABASES")
    return [row[0] for row in r.get("rows", [])]

def pg_query(query: str) -> dict:
    r = run(
        f'PGPASSWORD={PG_PASS} psql -h {PG_HOST} -p {PG_PORT} -U {PG_USER} -d {PG_DB} -c "{query}" -t -A -F "|"'
    )
    if r["exit_code"] == 0:
        lines = [l for l in r["stdout"].splitlines() if l.strip()]
        return {"rows": lines, "count": len(lines)}
    return {"error": r["stderr"] or r["stdout"]}

def redis_ping() -> str:
    return run(f"redis-cli -h {REDIS_HOST} -p {REDIS_PORT} PING")["stdout"]

def redis_info() -> dict:
    r = run(f"redis-cli -h {REDIS_HOST} -p {REDIS_PORT} INFO server")
    info = {}
    for line in r["stdout"].splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            info[k] = v
    return info

def qdrant_health() -> dict:
    try:
        req = urllib.request.urlopen(f"http://{QDRANT_HOST}:{QDRANT_PORT}/healthz", timeout=5)
        return {"status": "ok", "response": req.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def qdrant_collections() -> dict:
    try:
        req = urllib.request.urlopen(f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections", timeout=5)
        return json.loads(req.read())
    except Exception as e:
        return {"error": str(e)}


# =========================================================
# NETWORK
# =========================================================

def ping(host: str, count: int = 3) -> str:
    return run(f"ping -c {count} {host}")["stdout"]

def curl(url: str, timeout: int = 10) -> dict:
    r = run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time {timeout} {url}")
    return {"url": url, "http_code": r["stdout"]}

def check_port(host: str, port: int) -> bool:
    r = run(f"nc -z -w 2 {host} {port}")
    return r["exit_code"] == 0

def vpn_status() -> dict:
    # Пробуем сначала awg (AmneziaWG), потом wg (стандартный WireGuard)
    r = run("awg show awg0 2>/dev/null")
    if r["exit_code"] != 0 or not r["stdout"].strip():
        r = run("wg show awg0 2>/dev/null")
    if r["exit_code"] != 0 or not r["stdout"].strip():
        # Проверяем, существует ли интерфейс
        r2 = run("ip link show awg0 2>/dev/null")
        if r2["exit_code"] != 0:
            return {"status": "down", "error": "interface not found"}
        return {"status": "interface_exists", "detail": r2["stdout"]}
    lines = r["stdout"].splitlines()
    info = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    # Определяем реальный статус по latest handshake
    handshake = info.get("latest handshake", "")
    if handshake and "minute" in handshake.lower():
        mins = 0
        parts = handshake.lower().split()
        for i, p in enumerate(parts):
            if p.isdigit():
                if "minute" in parts[i+1:i+2][0] if i+1 < len(parts) else "":
                    mins = int(p)
                elif "second" in parts[i+1:i+2][0] if i+1 < len(parts) else "":
                    mins = 0
        if mins < 5:
            info["status"] = "up"
        else:
            info["status"] = "stale"
    elif handshake and "second" in handshake.lower():
        info["status"] = "up"
    elif handshake and "day" in handshake.lower():
        info["status"] = "stale"
    else:
        info["status"] = "up" if "peer" in r["stdout"].lower() else "down"
    return info

def dns_resolve(host: str) -> str:
    return run(f"dig +short {host}")["stdout"]


# =========================================================
# SECURITY
# =========================================================

def fail2ban_status() -> str:
    return run("fail2ban-client status")["stdout"]

def fail2ban_jails() -> list:
    r = run("fail2ban-client status | grep 'Jail list'")
    if r["stdout"]:
        jails = r["stdout"].split(":")[1].strip().split(",")
        return [j.strip() for j in jails if j.strip()]
    return []

def ssh_keys() -> list:
    path = "/root/.ssh/authorized_keys"
    if os.path.exists(path):
        with open(path) as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def firewall_status() -> str:
    return run("ufw status 2>/dev/null || iptables -L -n 2>/dev/null || echo 'no firewall info'")["stdout"]

def last_logins(count: int = 10) -> str:
    return run(f"last -{count}")["stdout"]

def who_is_online() -> str:
    return run("who")["stdout"]


# =========================================================
# FILESYSTEM
# =========================================================

def disk_usage(path: str = "/") -> str:
    return run(f"df -h {path}")["stdout"]

def dir_size(path: str) -> str:
    return run(f"du -sh {path} 2>/dev/null")["stdout"]

def find_large_files(path: str = "/", min_size: str = "100M") -> str:
    return run(f"find {path} -type f -size +{min_size} -exec ls -lh {{}} \\; 2>/dev/null | head -20")["stdout"]

def find_old_files(path: str = "/tmp", days: int = 7) -> str:
    return run(f"find {path} -type f -mtime +{days} 2>/dev/null | head -20")["stdout"]

def read_file_head(path: str, lines: int = 50) -> str:
    return run(f"head -{lines} {path}")["stdout"]

def read_file_tail(path: str, lines: int = 50) -> str:
    return run(f"tail -{lines} {path}")["stdout"]


# =========================================================
# FULL SERVER REPORT
# =========================================================

def full_report() -> dict:
    """Полный отчёт о состоянии сервера."""
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": get_uptime(),
        "load": get_load(),
        "cpu": get_cpu_info(),
        "ram": get_ram(),
        "disk": get_disk(),
        "nexus": nexus_metrics(),
        "docker": docker_ps(),
        "vpn": vpn_status(),
        "open_ports": get_open_ports(),
    }


# =========================================================
# LOKI AGENT — MAIN INTERFACE
# =========================================================

class LokiAgent:
    """
    Loki — агент-оператор сервера.
    Знает всё, может всё.
    """

    def __init__(self):
        self.name = "Loki"
        self.version = "1.0.0"

    def status(self) -> str:
        """Краткий статус сервера."""
        report = full_report()
        ram = report["ram"]
        disk_info = report["disk"][0] if report["disk"] else {}
        nexus = report["nexus"]
        vpn = report["vpn"]

        lines = [
            f"=== LOKI SERVER STATUS ===",
            f"Time: {report['timestamp']}",
            f"Uptime: {report['uptime']}",
            f"Load: {report['load']}",
            f"CPU: {report['cpu']['cores']} cores — {report['cpu']['model']}",
            f"RAM: {ram.get('mem_used','?')}/{ram.get('mem_total','?')} (avail: {ram.get('mem_available','?')})",
            f"Disk: {disk_info.get('used','?')}/{disk_info.get('size','?')} ({disk_info.get('use_percent','?')})",
            f"Nexus API: queue={nexus.get('queue','?')}, active={nexus.get('active','?')}, completed={nexus.get('completed_requests','?')}",
            f"VPN: {vpn.get('status','?')}",
            f"Docker containers: {len(report['docker'])}",
        ]
        return "\n".join(lines)

    def diagnose(self) -> str:
        """Диагностика проблем."""
        issues = []

        # Check services
        for svc in ["nexus-api", "nginx", "mysql", "docker", "fail2ban"]:
            s = service_status(svc)
            if not s["active"]:
                issues.append(f"[DOWN] {svc} is not active")

        # Check disk
        for d in get_disk():
            pct = int(d["use_percent"].replace("%", ""))
            if pct > 85:
                issues.append(f"[DISK] {d['mount']} is {d['use_percent']} full")

        # Check RAM
        ram = get_ram()
        if ram:
            avail = ram.get("mem_available", "")
            if avail.endswith("Mi"):
                avail_mb = int(avail.replace("Mi", ""))
                if avail_mb < 500:
                    issues.append(f"[RAM] Low available memory: {avail}")

        # Check Nexus
        nexus = nexus_health()
        if "error" in nexus:
            issues.append(f"[NEXUS] API not responding: {nexus['error']}")

        # Check Docker containers
        for c in docker_ps():
            name = c["name"]
            status = c["status"].lower()
            # Игнорируем тестовые/одноразовые контейнеры
            if name in ["watchtower"]:
                continue  # watchtower мониторится отдельно
            if "exited (0)" in status and name in ["distracted_meninsky", "musing_williamson"]:
                continue  # старые hello-world контейнеры, не ошибка
            if "unhealthy" in status:
                issues.append(f"[DOCKER] {name} is unhealthy")
            elif "exited" in status and "exited (0)" not in status:
                issues.append(f"[DOCKER] {name} exited with error: {c['status']}")
            elif "exited" in status and name not in ["distracted_meninsky", "musing_williamson"]:
                issues.append(f"[DOCKER] {name} exited: {c['status']}")

        # Check VPN
        vpn = vpn_status()
        if vpn["status"] == "down":
            issues.append("[VPN] AmneziaWG tunnel is down")

        if not issues:
            return "=== LOKI DIAGNOSIS ===\nAll systems nominal. No issues detected."

        return "=== LOKI DIAGNOSIS ===\n" + "\n".join(issues)

    def auto_heal(self, dry_run: bool = False) -> dict:
        """
        Автоматическое исправление проблем.
        dry_run=True — только показать что будет исправлено, не трогать.
        """
        actions = []
        errors = []

        # 1. Проверяем и перезапускаем упавшие сервисы
        critical_services = ["nexus-api", "nginx", "mysql", "docker", "fail2ban", "ssh"]
        for svc in critical_services:
            s = service_status(svc)
            if not s["active"]:
                actions.append(f"[HEAL] Restarting {svc} (was down)")
                if not dry_run:
                    result = service_restart(svc)
                    if "error" in result:
                        errors.append(f"[ERROR] Failed to restart {svc}: {result['error']}")

        # 2. Проверяем Docker контейнеры
        important_containers = ["nexus_postgres", "nexus_redis", "nexus_qdrant", "uptime-kuma", "portainer"]
        for c in docker_ps():
            name = c["name"]
            status = c["status"].lower()
            if name in important_containers and ("exited" in status and "exited (0)" not in status):
                actions.append(f"[HEAL] Restarting container {name} (was {c['status']})")
                if not dry_run:
                    result = docker_restart(name)
                    if "error" in result:
                        errors.append(f"[ERROR] Failed to restart {name}: {result['error']}")

        # 3. Watchtower — если упал, пересоздать
        watchtower_found = False
        for c in docker_ps():
            if c["name"] == "watchtower":
                watchtower_found = True
                if "exited" in c["status"].lower() and "exited (0)" not in c["status"].lower():
                    actions.append("[HEAL] Recreating watchtower (was down)")
                    if not dry_run:
                        run("docker rm watchtower 2>/dev/null")
                        run("docker run -d --name watchtower --restart unless-stopped "
                            "-v /var/run/docker.sock:/var/run/docker.sock "
                            "containrrr/watchtower --cleanup --interval 3600")
                break
        if not watchtower_found:
            actions.append("[HEAL] Creating watchtower (was missing)")
            if not dry_run:
                run("docker run -d --name watchtower --restart unless-stopped "
                    "-v /var/run/docker.sock:/var/run/docker.sock "
                    "containrrr/watchtower --cleanup --interval 3600")

        # 4. VPN — если down, поднять
        vpn = vpn_status()
        if vpn["status"] in ("down", "interface_not_found"):
            actions.append("[HEAL] Bringing up AmneziaWG tunnel")
            if not dry_run:
                r = run("awg-quick up awg0 2>&1")
                if r["exit_code"] != 0:
                    errors.append(f"[ERROR] Failed to start VPN: {r['stderr']}")

        # 5. Очистка старых hello-world контейнеров
        for c in docker_ps():
            if c["name"] in ["distracted_meninsky", "musing_williamson"]:
                actions.append(f"[HEAL] Removing old test container {c['name']}")
                if not dry_run:
                    run(f"docker rm {c['name']} 2>/dev/null")

        # 6. Очистка старых Nexus задач
        old_jobs = nexus_jobs_list()
        if len(old_jobs) > 100:
            actions.append(f"[HEAL] Cleaning up {len(old_jobs)} old Nexus jobs")
            if not dry_run:
                db_path = "/root/nexus-core/api/nexus_jobs.db"
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    conn.execute("DELETE FROM jobs WHERE status IN ('done','error')")
                    conn.commit()
                    conn.close()

        return {
            "dry_run": dry_run,
            "actions": actions,
            "errors": errors,
            "total_actions": len(actions),
            "total_errors": len(errors),
        }

    def analyze_logs(self, service: str = "nexus-api", lines: int = 100) -> str:
        """
        Анализ логов сервиса через локальную LLM.
        Читает логи и отправляет их в Nexus LLM для анализа.
        """
        # Получаем логи
        if service == "docker":
            log_text = docker_logs("nexus_postgres", lines)
        else:
            log_text = service_logs(service, lines)

        if not log_text.strip():
            return f"No logs found for {service}"

        # Обрезаем до разумного размера для LLM
        log_lines = log_text.splitlines()
        if len(log_lines) > 200:
            log_lines = log_lines[-200:]
        log_text = "\n".join(log_lines)

        # Формируем промпт для анализа
        prompt = f"""Analyze the following server logs and provide:
1. Summary of what happened
2. Any errors or warnings detected
3. Root cause analysis if there are issues
4. Recommended actions

Logs from {service}:
---
{log_text}
---

Analysis (in Russian):"""

        # Отправляем в Nexus API
        result = nexus_generate(prompt, max_tokens=500, temperature=0.3)
        if "error" in result:
            return f"LLM analysis failed: {result['error']}"

        job_id = result.get("job_id", "")
        if job_id:
            # Ждём результат (опрос статуса)
            for _ in range(30):
                time.sleep(2)
                job = nexus_job_status(job_id)
                if job.get("status") == "done":
                    return job.get("response", "No response")
                if job.get("status") == "error":
                    return f"LLM error: {job.get('response', 'unknown')}"
            return "LLM analysis timed out"

        return "No job_id returned"

    def ask_llm(self, question: str) -> str:
        """
        Задать вопрос локальной LLM о сервере.
        Loki собирает контекст и отправляет в Nexus.
        """
        # Собираем контекст о сервере
        context = self.status()
        diagnose = self.diagnose()

        prompt = f"""Ты — Loki, агент-оператор сервера. Вот текущее состояние:

{context}

Диагностика:
{diagnose}

Вопрос пользователя: {question}

Ответь кратко и по делу на русском языке:"""

        result = nexus_generate(prompt, max_tokens=300, temperature=0.5)
        if "error" in result:
            return f"LLM error: {result['error']}"

        job_id = result.get("job_id", "")
        if job_id:
            for _ in range(30):
                time.sleep(2)
                job = nexus_job_status(job_id)
                if job.get("status") == "done":
                    return job.get("response", "No response")
                if job.get("status") == "error":
                    return f"LLM error: {job.get('response', 'unknown')}"
            return "LLM timed out"

        return "No job_id returned"

    def run(self, task: str) -> str:
        """Обработка задачи — маршрутизация к нужному инструменту."""
        task_lower = task.lower()

        # Status
        if any(w in task_lower for w in ["статус", "status", "состояние", "health"]):
            return self.status()

        # Diagnosis
        if any(w in task_lower for w in ["диагностик", "diagnose", "проблем", "issue", "check"]):
            return self.diagnose()

        # Auto-heal
        if any(w in task_lower for w in ["почини", "heal", "исправ", "autofix", "починить"]):
            dry = "сухой" in task_lower or "dry" in task_lower or "preview" in task_lower
            result = self.auto_heal(dry_run=dry)
            if dry:
                lines = ["=== LOKI AUTO-HEAL (DRY RUN) ==="]
            else:
                lines = ["=== LOKI AUTO-HEAL ==="]
            for a in result["actions"]:
                lines.append(f"  {a}")
            for e in result["errors"]:
                lines.append(f"  {e}")
            lines.append(f"\nTotal: {result['total_actions']} actions, {result['total_errors']} errors")
            return "\n".join(lines)

        # LLM analysis
        if any(w in task_lower for w in ["анализ логов", "analyze logs", "анализ журнала"]):
            svc = "nexus-api"
            if "nginx" in task_lower:
                svc = "nginx"
            elif "mysql" in task_lower:
                svc = "mysql"
            elif "docker" in task_lower:
                svc = "docker"
            return self.analyze_logs(service=svc)

        # Ask LLM
        if any(w in task_lower for w in ["спроси llm", "ask llm", "вопрос llm", "llm вопрос"]):
            # Извлекаем вопрос после ключевого слова
            for prefix in ["спроси llm", "ask llm", "вопрос llm", "llm вопрос"]:
                if prefix in task_lower:
                    question = task[task_lower.index(prefix) + len(prefix):].strip()
                    if question:
                        return self.ask_llm(question)
            return "Usage: спроси llm <вопрос>"

        # Docker
        if any(w in task_lower for w in ["docker", "контейнер"]):
            containers = docker_ps()
            return json.dumps(containers, ensure_ascii=False, indent=2)

        # Nexus
        if any(w in task_lower for w in ["nexus", "llm", "api", "модель"]):
            return json.dumps(nexus_metrics(), ensure_ascii=False, indent=2)

        # VPN
        if any(w in task_lower for w in ["vpn", "wg", "amnezia", "туннел"]):
            return json.dumps(vpn_status(), ensure_ascii=False, indent=2)

        # Database
        if any(w in task_lower for w in ["mysql", "база данных", "database"]):
            return json.dumps(mysql_databases(), ensure_ascii=False, indent=2)

        # Redis
        if "redis" in task_lower:
            return json.dumps({"ping": redis_ping(), "info": redis_info()}, ensure_ascii=False, indent=2)

        # Qdrant
        if "qdrant" in task_lower:
            return json.dumps({"health": qdrant_health(), "collections": qdrant_collections()}, ensure_ascii=False, indent=2)

        # Services
        if any(w in task_lower for w in ["сервис", "service", "systemd"]):
            return json.dumps(all_services_status(), ensure_ascii=False, indent=2)

        # Disk
        if any(w in task_lower for w in ["диск", "disk", "место", "space"]):
            return json.dumps(get_disk(), ensure_ascii=False, indent=2)

        # RAM
        if any(w in task_lower for w in ["ram", "память", "memory"]):
            return json.dumps(get_ram(), ensure_ascii=False, indent=2)

        # Network
        if any(w in task_lower for w in ["порт", "port", "сеть", "network"]):
            return json.dumps(get_open_ports(), ensure_ascii=False, indent=2)

        # Security
        if any(w in task_lower for w in ["безопасн", "security", "fail2ban", "firewall"]):
            return json.dumps({
                "fail2ban": fail2ban_status(),
                "firewall": firewall_status(),
                "ssh_keys": ssh_keys(),
            }, ensure_ascii=False, indent=2)

        # Full report
        if any(w in task_lower for w in ["полный", "full", "всё", "everything", "отчёт", "report"]):
            return json.dumps(full_report(), ensure_ascii=False, indent=2)

        # Default — краткий статус
        return self.status()


# =========================================================
# CLI ENTRY POINT
# =========================================================

if __name__ == "__main__":
    import sys

    agent = LokiAgent()

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(agent.run(task))
    else:
        print(agent.status())
        print()
        print("Usage: python loki_agent.py <command>")
        print("Commands: status, diagnose, docker, nexus, vpn, mysql, redis, qdrant,")
        print("          services, disk, ram, network, security, report")
