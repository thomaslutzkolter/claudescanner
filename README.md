# ClaudeScanner

Browser-basierter Viewer und Editor für Claude Code MD-Dateien und Git-Repos.

## Features

- Alle `.claude/` MD-Dateien (Plans, Memory, Session-Summaries) anzeigen
- CLAUDE.md, GOVERNANCE.md sichtbar
- Dateien direkt im Browser editieren (Ctrl+S)
- Git-Repos mit Branch, letztem Commit, Dirty-Status
- Keine externen Dependencies (Python3 stdlib only)
- Systemd-Service

## Setup

```bash
# Kopieren
cp claude-files-server.py /root/

# Starten
python3 /root/claude-files-server.py

# Oder als systemd Service
cp claude-files.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now claude-files
```

Läuft auf Port 8090.

## Warum

Claude Code speichert Pläne, Memory und Konfiguration in lokalen MD-Dateien.
Ohne dieses Tool hat der User keine Sicht auf diese Dateien.
