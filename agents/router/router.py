class TaskRouter:
    """
    Rule-based router (MVP ядро)
    Маршрутизирует задачи к соответствующим агентам.
    """

    def route(self, task: str) -> str:
        task_lower = task.lower()

        # 🛡️ Loki — server operations & monitoring
        if any(word in task_lower for word in [
            "сервер", "server", "статус", "status", "диагностик", "diagnose",
            "docker", "контейнер", "nexus", "llm", "api", "модель",
            "vpn", "wg", "amnezia", "туннел",
            "mysql", "база данных", "database", "redis", "qdrant",
            "сервис", "service", "systemd",
            "диск", "disk", "место", "space", "ram", "память", "memory",
            "порт", "port", "сеть", "network",
            "безопасн", "security", "fail2ban", "firewall",
            "мониторинг", "monitoring", "отчёт", "report",
            "логи", "log", "логи сервиса",
        ]):
            return "loki_agent"

        # 🧠 coder
        if any(word in task_lower for word in ["код", "python", "bug", "парс", "script"]):
            return "coder_agent"

        # 🔎 research
        if any(word in task_lower for word in ["найди", "поиск", "информац", "qdrant"]):
            return "research_agent"

        # 🧠 memory
        if any(word in task_lower for word in ["запомни", "сохрани", "remember", "note"]):
            return "memory_agent"

        # 🤖 default
        return "general_agent"
