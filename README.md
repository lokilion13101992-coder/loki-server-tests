# Loki Server

Infrastructure and AI agent server running on Ubuntu 24.04.

## Services

| Service | Port | Description |
|---------|------|-------------|
| Nexus Core | 8000 | FastAPI LLM inference server |
| Loki Dashboard | 8080 | Agent dashboard |
| Nginx | 80 | Web server |
| MySQL | 3306 | Database |
| PostgreSQL | 5432 | Database (Docker) |
| Redis | 6379 | Cache (Docker) |
| Qdrant | 6333 | Vector DB (Docker) |
| Uptime Kuma | 3001 | Monitoring (Docker) |
| Netdata | 19999 | System monitoring (Docker) |
| Portainer | 9000/9443 | Container management (Docker) |
| ISPmanager | 1500 | Control panel |
| AmneziaWG | 58018 | VPN |

## Tests

```bash
cd /root/nexus-core
python -m pytest tests/ -v
```

See [tests/README.md](tests/README.md) for details.
