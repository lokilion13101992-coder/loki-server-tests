# Loki Server Auto-Tests

Comprehensive test suite for the Loki server infrastructure.

## Quick Start

```bash
cd /root/nexus-core
pip install pytest
python -m pytest tests/ -v
```

## Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| `TestOperatingSystem` | 9 | OS, kernel, RAM, disk, load |
| `TestNetwork` | 6 | IP, VPN, DNS, routing |
| `TestServices` | 11 | systemd services (nginx, ssh, docker, etc.) |
| `TestDockerContainers` | 9 | Docker containers health |
| `TestNexusCore` | 6 | Nexus Core API endpoints |
| `TestLokiDashboard` | 2 | Loki Dashboard |
| `TestNginx` | 4 | Nginx web server |
| `TestDatabases` | 7 | MySQL, PostgreSQL, Redis, Qdrant |
| `TestSecurity` | 9 | UFW, fail2ban, SSH, file permissions |
| `TestBackupsAndCron` | 7 | Backup files, cron jobs |
| `TestLokiAgent` | 4 | Loki agent files |
| `TestISPmanager` | 2 | ISPmanager control panel |
| `TestMailServices` | 7 | SMTP, IMAP, POP3 |
| `TestDNSServer` | 3 | BIND/named |
| `TestFTPServer` | 2 | ProFTPD |
| `TestUptimeKuma` | 2 | Uptime Kuma monitoring |
| `TestNetdata` | 2 | Netdata monitoring |
| `TestPortainer` | 2 | Portainer container management |

**Total: 94 tests**

## Running Specific Tests

```bash
# Only security tests
python -m pytest tests/ -v -k "Security"

# Only Docker tests
python -m pytest tests/ -v -k "Docker"

# Only API tests
python -m pytest tests/ -v -k "NexusCore or LokiDashboard"

# Exclude slow tests
python -m pytest tests/ -v -m "not slow"
```

## Known Issues

- **Watchtower**: Restart loop due to Docker API version mismatch (client 1.25, min 1.44)
- **Port 443**: No SSL certificate configured yet
- **Loki Dashboard**: Not set up as systemd service (started manually)
- **ISPmanager**: Port 1500 binding may be interface-specific

## CI/CD

Tests run automatically via GitHub Actions on:
- Push to main/master
- Pull requests
- Daily schedule (3:00 AM UTC)
