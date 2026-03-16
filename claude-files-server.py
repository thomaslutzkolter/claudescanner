#!/usr/bin/env python3
"""
Claude Files Browser — Standalone auf wireguard (10.0.0.6)
Zeigt .claude/ MD-Dateien, CLAUDE.md, GOVERNANCE.md und Git-Repos.
Editierbar im Browser. Keine externen Dependencies.
Port: 8090
"""

import os
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

REPO_ROOT = "/root"
PORT = 8090

def get_md_files():
    files = []
    for f in ["/root/CLAUDE.md", "/root/myzel-infra/CLAUDE.md", "/root/myzel-infra/GOVERNANCE.md"]:
        if os.path.isfile(f):
            files.append(f)
    claude_dir = Path("/root/.claude")
    if claude_dir.exists():
        for md in sorted(claude_dir.rglob("*.md")):
            s = str(md)
            if "/plugins/" in s or "/cache/" in s:
                continue
            if s not in files:
                files.append(s)
    return files

def is_allowed(path):
    real = os.path.realpath(path)
    if not real.startswith(REPO_ROOT):
        return False
    if "/plugins/" in real or "/cache/" in real:
        return False
    if ".git/" in real:
        return False
    if real.endswith(".md"):
        return True
    # Erlaubt: CLAUDE.md, GOVERNANCE.md, settings.json etc im .claude
    if real.startswith(os.path.realpath("/root/.claude")):
        return True
    return False

def get_repos():
    repos = []
    for d in sorted(Path(REPO_ROOT).iterdir()):
        git_dir = d / ".git"
        if d.is_dir() and git_dir.exists():
            try:
                branch = subprocess.check_output(["git", "-C", str(d), "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
                last_commit = subprocess.check_output(["git", "-C", str(d), "log", "-1", "--format=%h %s (%cr)"], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
                status = subprocess.check_output(["git", "-C", str(d), "status", "--porcelain"], stderr=subprocess.DEVNULL, timeout=5).decode().strip()
                dirty = len(status.splitlines()) if status else 0
            except Exception:
                branch, last_commit, dirty = "?", "?", -1
            repos.append({"name": d.name, "path": str(d), "branch": branch, "last_commit": last_commit, "dirty_files": dirty})
    return repos

def get_repo_files(path):
    real = os.path.realpath(path)
    if not real.startswith(REPO_ROOT) or not os.path.isdir(real):
        return []
    mds = []
    for md in sorted(Path(real).rglob("*.md")):
        rel = str(md.relative_to(real))
        if "node_modules" in rel or ".git/" in rel:
            continue
        mds.append({"path": str(md), "relative": rel, "size": md.stat().st_size})
    return mds

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Kein Spam

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/":
            self._html(HTML)
        elif parsed.path == "/api/files":
            self._json({"files": get_md_files()})
        elif parsed.path == "/api/file":
            path = params.get("path", [""])[0]
            if not path or not is_allowed(path) or not os.path.isfile(path):
                self._json({"error": "Nicht erlaubt oder nicht gefunden"}, 403)
                return
            self._json({"path": path, "content": Path(path).read_text(errors="replace"), "size": os.path.getsize(path)})
        elif parsed.path == "/api/repos":
            self._json({"repos": get_repos()})
        elif parsed.path == "/api/repo/files":
            path = params.get("path", [""])[0]
            self._json({"repo": os.path.basename(path), "files": get_repo_files(path)})
        else:
            self._json({"error": "Not found"}, 404)

    def do_PUT(self):
        if self.path == "/api/file":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            path = body.get("path", "")
            content = body.get("content", "")
            if not path or not is_allowed(path) or not os.path.isfile(path):
                self._json({"error": "Nicht erlaubt"}, 403)
                return
            Path(path).write_text(content)
            self._json({"ok": True, "path": path, "size": len(content)})
        else:
            self._json({"error": "Not found"}, 404)

HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Files — Wireguard</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f1117; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; }
.topbar { background: #1a1d27; border-bottom: 1px solid #2a2d3a; padding: 10px 20px; display: flex; align-items: center; gap: 16px; }
.topbar h1 { font-size: 16px; font-weight: 600; color: #fff; }
.topbar a { color: #f97316; text-decoration: none; font-size: 13px; }
.tabs { display: flex; gap: 0; background: #1a1d27; border-bottom: 1px solid #2a2d3a; padding: 0 20px; }
.tab { padding: 10px 20px; font-size: 13px; font-weight: 600; color: #666; cursor: pointer; border-bottom: 2px solid transparent; }
.tab:hover { color: #aaa; }
.tab.active { color: #f97316; border-bottom-color: #f97316; }
.container { display: flex; height: calc(100vh - 85px); }
.sidebar { width: 320px; background: #1a1d27; border-right: 1px solid #2a2d3a; overflow-y: auto; flex-shrink: 0; }
.file-item { padding: 8px 16px; font-size: 13px; cursor: pointer; border-bottom: 1px solid #1f222d; display: flex; justify-content: space-between; align-items: center; }
.file-item:hover { background: #22252f; }
.file-item.active { background: #2a2d3a; color: #f97316; }
.file-item .path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-item .size { color: #666; font-size: 11px; flex-shrink: 0; margin-left: 8px; }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.editor-bar { padding: 8px 16px; background: #1a1d27; border-bottom: 1px solid #2a2d3a; display: flex; align-items: center; gap: 8px; }
.editor-bar .filepath { font-size: 12px; color: #888; font-family: monospace; flex: 1; overflow: hidden; text-overflow: ellipsis; }
.btn { padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid #3a3d4a; background: #1a1d27; color: #aaa; }
.btn:hover { border-color: #666; color: #fff; }
.btn-save { background: #22c55e; border-color: #22c55e; color: #fff; }
.btn-save:hover { background: #16a34a; }
.btn-save:disabled { opacity: 0.4; cursor: default; }
textarea#editor { flex: 1; background: #0f1117; color: #e0e0e0; border: none; padding: 16px; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; resize: none; outline: none; tab-size: 4; }
.toast { position: fixed; bottom: 20px; right: 20px; padding: 10px 20px; border-radius: 8px; font-size: 13px; background: #22c55e; color: #fff; opacity: 0; transition: opacity 0.3s; z-index: 999; }
.toast.show { opacity: 1; }
.toast.error { background: #ef4444; }
.repo-card { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 14px; margin: 8px 16px; cursor: pointer; }
.repo-card:hover { border-color: #f97316; }
.repo-card h3 { font-size: 14px; color: #fff; margin-bottom: 6px; }
.repo-meta { font-size: 12px; color: #888; }
.repo-meta .branch { color: #22d3ee; }
.repo-meta .dirty { color: #f97316; }
.repo-meta .clean { color: #22c55e; }
.repo-grid { padding: 8px; overflow-y: auto; }
.empty { padding: 40px; text-align: center; color: #666; }
.search { margin: 8px 12px; padding: 8px 12px; background: #0f1117; border: 1px solid #2a2d3a; border-radius: 6px; color: #e0e0e0; font-size: 13px; width: calc(100% - 24px); }
</style>
</head>
<body>
<div class="topbar">
    <h1>Claude Files</h1>
    <a href="http://10.0.0.4:3002" target="_blank">MYRA</a>
    <a href="http://10.0.0.4:3002/static/gateway.html" target="_blank">Gateway</a>
</div>
<div class="tabs">
    <div class="tab active" onclick="switchTab('files')">MD-Dateien</div>
    <div class="tab" onclick="switchTab('repos')">Git Repos</div>
</div>
<div class="container" id="files-view">
    <div class="sidebar">
        <input class="search" type="text" placeholder="Filter..." oninput="filterFiles(this.value)">
        <div id="file-list"></div>
    </div>
    <div class="main">
        <div class="editor-bar">
            <span class="filepath" id="current-path">Datei auswaehlen...</span>
            <button class="btn btn-save" id="btn-save" onclick="saveFile()" disabled>Speichern</button>
        </div>
        <textarea id="editor" placeholder="Datei auswaehlen um Inhalt zu sehen..." readonly></textarea>
    </div>
</div>
<div class="container" id="repos-view" style="display:none;flex-direction:column;">
    <div class="repo-grid" id="repo-list"></div>
</div>
<div class="toast" id="toast"></div>
<script>
let allFiles=[], currentFile=null;

async function loadFiles() {
    const r = await fetch('/api/files');
    allFiles = (await r.json()).files;
    renderFiles(allFiles);
}

function renderFiles(files) {
    const el = document.getElementById('file-list');
    const groups = {};
    files.forEach(f => {
        const parts = f.split('/');
        let g = parts.length > 4 ? parts.slice(0,4).join('/') : parts.slice(0,-1).join('/');
        if (!groups[g]) groups[g] = [];
        groups[g].push(f);
    });
    let h = '';
    for (const [g, gf] of Object.entries(groups)) {
        h += '<div style="padding:6px 12px;font-size:11px;color:#f97316;font-weight:600;border-bottom:1px solid #1f222d;background:#13151d">' + g.replace('/root/','~/') + '</div>';
        gf.forEach(f => {
            const n = f.split('/').pop();
            h += '<div class="file-item" data-path="'+f+'" onclick="openFile(\''+f.replace(/'/g,"\\'")+'\')">';
            h += '<span class="path">'+n+'</span></div>';
        });
    }
    el.innerHTML = h || '<div class="empty">Keine Dateien</div>';
}

function filterFiles(q) {
    q = q.toLowerCase();
    renderFiles(allFiles.filter(f => f.toLowerCase().includes(q)));
}

async function openFile(path) {
    const r = await fetch('/api/file?path='+encodeURIComponent(path));
    if (!r.ok) { toast('Fehler: '+r.status, true); return; }
    const d = await r.json();
    if (d.error) { toast(d.error, true); return; }
    currentFile = path;
    document.getElementById('editor').value = d.content;
    document.getElementById('editor').readOnly = false;
    document.getElementById('current-path').textContent = path.replace('/root/','~/');
    document.getElementById('btn-save').disabled = false;
    document.querySelectorAll('.file-item').forEach(el => el.classList.toggle('active', el.dataset.path===path));
}

async function saveFile() {
    if (!currentFile) return;
    const r = await fetch('/api/file', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:currentFile, content:document.getElementById('editor').value})});
    toast(r.ok ? 'Gespeichert' : 'Fehler', !r.ok);
}

async function loadRepos() {
    const r = await fetch('/api/repos');
    const d = await r.json();
    const el = document.getElementById('repo-list');
    if (!d.repos.length) { el.innerHTML='<div class="empty">Keine Repos</div>'; return; }
    el.innerHTML = d.repos.map(r => `
        <div class="repo-card" onclick="openRepo('${r.path}')">
            <h3>${r.name}</h3>
            <div class="repo-meta"><span class="branch">${r.branch}</span> · <span class="${r.dirty_files>0?'dirty':'clean'}">${r.dirty_files>0?r.dirty_files+' uncommitted':'clean'}</span></div>
            <div class="repo-meta" style="margin-top:4px">${r.last_commit}</div>
        </div>`).join('');
}

async function openRepo(path) {
    const r = await fetch('/api/repo/files?path='+encodeURIComponent(path));
    const d = await r.json();
    const el = document.getElementById('repo-list');
    let h = '<div style="padding:12px 16px"><button class="btn" onclick="loadRepos()">Zurueck</button> <span style="color:#f97316;font-weight:600;margin-left:8px">'+d.repo+'</span> — '+d.files.length+' MD-Dateien</div>';
    d.files.forEach(f => {
        h += '<div class="file-item" style="margin:0 16px;border-radius:6px" onclick="openRepoFile(\''+f.path.replace(/'/g,"\\'")+'\')">';
        h += '<span class="path">'+f.relative+'</span><span class="size">'+(f.size/1024).toFixed(1)+'k</span></div>';
    });
    el.innerHTML = h;
}

function openRepoFile(p) { switchTab('files'); openFile(p); }

function switchTab(t) {
    document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
    if (t==='files') {
        document.getElementById('files-view').style.display='flex';
        document.getElementById('repos-view').style.display='none';
        document.querySelectorAll('.tab')[0].classList.add('active');
    } else {
        document.getElementById('files-view').style.display='none';
        document.getElementById('repos-view').style.display='flex';
        document.querySelectorAll('.tab')[1].classList.add('active');
        loadRepos();
    }
}

function toast(m,e) {
    const t=document.getElementById('toast');
    t.textContent=m; t.className='toast show'+(e?' error':'');
    setTimeout(()=>t.className='toast',2500);
}

document.addEventListener('keydown', e => {
    if ((e.ctrlKey||e.metaKey) && e.key==='s') { e.preventDefault(); saveFile(); }
});

loadFiles();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print(f"Claude Files Browser auf http://10.0.0.6:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
