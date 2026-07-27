"""portcheck-gui — GTK4 + libadwaita live port monitor.

Pure live-scan mode. No registry, no persistence of "what *should* be there".
Each tick re-reads `ss -tlnpH` and shows only the ports actually being
listened on right now. Names are derived from the holder process's name and
cmdline (project directory, script path, `-m` module, etc.) so they update
themselves as services come and go.

Closing the window quits the app.
"""
from __future__ import annotations

import gettext
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import field
from dataclasses import dataclass
from pathlib import Path

# 配置多语言 (i18n / gettext) 机制
LOCALE_DIR = Path(__file__).parent / "po"
gettext.bindtextdomain("portcheck-gui", str(LOCALE_DIR))
gettext.textdomain("portcheck-gui")

# 翻译字典定义（支持 英语 en、简体中文 zh_CN、西班牙语 es）
TRANSLATIONS = {
    "en": {
        "APP_NAME": "Port Checker",
        "REFRESH_TOOLTIP": "Refresh (F5)",
        "SEARCH_PLACEHOLDER": "Search by port, process name or PID...",
        "STATUS_REFRESHED": "Refreshed ({count} listening ports)",
        "TITLE_TEST_HTTP": "Test HTTP Connectivity (Ping)",
        "TITLE_OPEN_BROWSER": "Open in Browser",
        "TITLE_WITR_CAUSALITY": "Trace Process Causality (witr)",
        "TITLE_OPEN_PROC": "Open Process Folder /proc/<pid>",
        "TITLE_KILL_PROC": "Terminate Process (Kill)",
        "SUBTITLE_KILL_PROC": "Send SIGTERM / SIGKILL to release port",
        "MENU_ABOUT": "About Port Checker",
        "ABOUT_COMMENTS": "Real-time local listening port monitor.\nPowered by ss + /proc + witr causality analysis.",
        "KILL_CONFIRM_TITLE": "Terminate Process {name} (PID {pid})?",
        "KILL_CONFIRM_BODY": "This will stop the process occupying port {port}. Are you sure?",
        "BTN_CANCEL": "Cancel",
        "BTN_TERMINATE": "Terminate",
        "TOAST_KILL_SUCCESS": "Process {pid} terminated",
        "TOAST_KILL_FAIL": "Failed to terminate process {pid}: {error}",
        "WITR_DIALOG_TITLE": "Process Causality Analysis (witr)",
        "WITR_NOT_FOUND": "witr tool is not installed in system.",
    },
    "es": {
        "APP_NAME": "Comprobador de Puertos",
        "REFRESH_TOOLTIP": "Actualizar (F5)",
        "SEARCH_PLACEHOLDER": "Buscar por puerto, proceso o PID...",
        "STATUS_REFRESHED": "Actualizado ({count} puertos escuchando)",
        "TITLE_TEST_HTTP": "Probar conectividad HTTP (Ping)",
        "TITLE_OPEN_BROWSER": "Abrir en el navegador",
        "TITLE_WITR_CAUSALITY": "Rastrear causalidad del proceso (witr)",
        "TITLE_OPEN_PROC": "Abrir carpeta del proceso /proc/<pid>",
        "TITLE_KILL_PROC": "Terminar proceso (Kill)",
        "SUBTITLE_KILL_PROC": "Enviar SIGTERM / SIGKILL para liberar el puerto",
        "MENU_ABOUT": "Acerca del Comprobador de Puertos",
        "ABOUT_COMMENTS": "Monitor de puertos de escucha en tiempo real.\nBasado en análisis de ss + /proc + witr.",
        "KILL_CONFIRM_TITLE": "¿Terminar el proceso {name} (PID {pid})?",
        "KILL_CONFIRM_BODY": "Esto detendrá el proceso que ocupa el puerto {port}. ¿Estás seguro?",
        "BTN_CANCEL": "Cancelar",
        "BTN_TERMINATE": "Terminar",
        "TOAST_KILL_SUCCESS": "Proceso {pid} terminado",
        "TOAST_KILL_FAIL": "Error al terminar el proceso {pid}: {error}",
        "WITR_DIALOG_TITLE": "Análisis de causalidad del proceso (witr)",
        "WITR_NOT_FOUND": "La herramienta witr no está instalada en el sistema.",
    },
    "zh_CN": {
        "APP_NAME": "端口检查器",
        "REFRESH_TOOLTIP": "刷新 (F5)",
        "SEARCH_PLACEHOLDER": "按端口、进程名或 PID 搜索...",
        "STATUS_REFRESHED": "已刷新 ({count} 个监听端口)",
        "TITLE_TEST_HTTP": "测试 HTTP 连通性 (Ping)",
        "TITLE_OPEN_BROWSER": "在浏览器中打开",
        "TITLE_WITR_CAUSALITY": "追溯进程因果链 (witr)",
        "TITLE_OPEN_PROC": "打开进程目录 /proc/<pid>",
        "TITLE_KILL_PROC": "结束进程 (Kill)",
        "SUBTITLE_KILL_PROC": "发送 SIGTERM / SIGKILL 释放端口",
        "MENU_ABOUT": "关于 端口检查器",
        "ABOUT_COMMENTS": "本机监听端口实时监控器。\n基于 ss + /proc + witr 因果链分析。",
        "KILL_CONFIRM_TITLE": "确定要结束进程 {name} (PID {pid}) 吗？",
        "KILL_CONFIRM_BODY": "这将终结正在占用端口 {port} 的进程，确定要继续吗？",
        "BTN_CANCEL": "取消",
        "BTN_TERMINATE": "确定结束",
        "TOAST_KILL_SUCCESS": "进程 {pid} 已结束",
        "TOAST_KILL_FAIL": "结束进程 {pid} 失败: {error}",
        "WITR_DIALOG_TITLE": "进程因果链分析 (witr)",
        "WITR_NOT_FOUND": "未在系统中找到 witr 工具。",
    }
}

def get_sys_lang() -> str:
    lang = os.environ.get("LANG", "en").split(".")[0]
    if lang.startswith("zh"):
        return "zh_CN"
    elif lang.startswith("es"):
        return "es"
    return "en"

CURRENT_LANG = get_sys_lang()

def _(key: str) -> str:
    """自动获取系统语言对应的国际化文本"""
    return TRANSLATIONS.get(CURRENT_LANG, TRANSLATIONS["en"]).get(key, key)
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

APP_ID = "com.local.portcheck"
APP_NAME = _("APP_NAME")
POLL_SECONDS = 3
STATE_PATH = Path(
    os.environ.get("PORTCHECK_GUI_STATE")
    or (Path.home() / ".config" / "portcheck-gui" / "state.json")
)


# ---------- Window state persistence (geometry + show-system toggle) ----------

def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


# ---------- Live socket scanner ----------

@dataclass
class Listener:
    pid: int          # 0 if owner is not visible (other user / kernel)
    proc: str         # /proc/<pid>/comm — short name like "ollama", "python3"
    cmdline: str      # full argv joined by spaces
    user: str = ""    # owner username (best-effort)
    host: str = ""    # bind address
    port: int = 0
    proto: str = "tcp"

    @property
    def is_ipv6(self) -> bool:
        return ":" in self.host and not self.host.startswith("127.") and self.host != "localhost"


@dataclass
class Row:
    """One displayed entry — uniquely keyed by (proto, port, host)."""
    name: str         # auto-derived display name
    port: int
    host: str
    proto: str
    holder: Listener
    aliases: list[Listener] = field(default_factory=list)  # other listeners (e.g. v6 dup)

    @property
    def key(self) -> str:
        return f"{self.proto}:{self.host}:{self.port}"


# Linux process names that are generic interpreters / launchers; we have to
# look at the cmdline to figure out what they actually are.
GENERIC_PROCS = {
    "python", "python2", "python3",
    "node", "nodejs", "deno", "bun",
    "java", "ruby", "perl", "php",
    "bash", "sh", "zsh", "fish",
    "uvicorn", "gunicorn", "hypercorn", "daphne",
    "electron", "chrome", "chromium",
    "docker-proxy", "containerd-shim",
}

# Path segments that should never be picked as a project name.
PATH_NOISE = {
    "local", "cache", "config", "ssh", "gnupg", "venv", ".venv",
    "site-packages", "dist-packages", "bin", "lib", "lib64",
    "share", "tmp", "var", "etc", "opt", "usr", "home", "hy",
    "node_modules", ".local", ".cache", ".config",
}


def _read_cmdline(pid: int) -> str:
    """Read /proc/<pid>/cmdline (NUL-separated) → space-joined string."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            raw = fh.read()
    except OSError:
        return ""
    parts = [p.decode("utf-8", "replace") for p in raw.split(b"\0") if p]
    return " ".join(parts)


def _read_comm(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _read_user(pid: int) -> str:
    try:
        st = os.stat(f"/proc/{pid}")
    except OSError:
        return ""
    try:
        import pwd
        return pwd.getpwuid(st.st_uid).pw_name
    except (KeyError, ImportError):
        return str(st.st_uid)


# Regex for `ss -tlnpH` lines. Process column is optional (root-owned procs
# are invisible to non-root callers).
_SS_LINE = re.compile(
    r"""^LISTEN\s+\S+\s+\S+\s+
        (?P<addr>\S+)\s+\S+
        (?:\s+users:\(\("(?P<proc>[^"]+)",pid=(?P<pid>\d+),fd=\d+\)\))?
        \s*$""",
    re.VERBOSE,
)


def _split_addr(addr: str) -> tuple[str, int]:
    """ss prints `127.0.0.1:7998`, `0.0.0.0:80`, or `[::1]:631` etc."""
    if addr.startswith("["):
        host, _, port = addr.rpartition("]:")
        return host[1:], int(port)
    host, _, port = addr.rpartition(":")
    return host, int(port)


def scan_listeners() -> list[Listener]:
    """Run `ss -tlnpH` and parse one Listener per LISTEN row."""
    out: list[Listener] = []
    try:
        r = subprocess.run(
            ["ss", "-tlnpH"],
            capture_output=True, text=True, timeout=4,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return out
    for line in r.stdout.splitlines():
        m = _SS_LINE.match(line)
        if not m:
            continue
        addr = m.group("addr")
        try:
            host, port = _split_addr(addr)
        except (ValueError, IndexError):
            continue
        # Strip systemd-resolved's per-link interface suffix `127.0.0.53%lo`.
        host = host.split("%", 1)[0]
        pid = int(m.group("pid")) if m.group("pid") else 0
        proc = m.group("proc") or ""
        cmdline = _read_cmdline(pid) if pid else ""
        # /proc/<pid>/comm is more accurate than ss's truncated proc name.
        if pid:
            real = _read_comm(pid)
            if real:
                proc = real
        user = _read_user(pid) if pid else "root?"
        out.append(Listener(
            pid=pid, proc=proc, cmdline=cmdline, user=user,
            host=host, port=port, proto="tcp",
        ))
    return out


# ---------- Name derivation ----------

# Well-known system services we don't want to mislabel as "(root)".
SYSTEM_PORTS: dict[int, str] = {
    53:  "systemd-resolved",
    631: "cups",
    5353: "avahi-mdns",
    5355: "systemd-resolved",
}


def _name_from_cmdline(proc: str, cmdline: str) -> str | None:
    """Try to pull a meaningful project/app name from a generic-interpreter
    process's argv. Returns None if nothing distinctive is found."""
    if not cmdline:
        return None
    parts = cmdline.split()

    GENERIC_STEMS = {
        "__main__", "main", "app", "run", "server",
        "index", "bridge", "start", "cli",
    }
    # Sub-directory names that don't identify a project on their own
    # (e.g. .greenbone/admin/app.py — "admin" tells us nothing, walk up).
    WALK_THROUGH_DIRS = {
        "admin", "api", "backend", "frontend", "web", "ui", "gui",
        "service", "services", "app", "apps", "core", "common",
        "bin", "lib", "libs", "src", "scripts", "server", "client",
        "internal", "pkg", "cmd",
    }

    def _meaningful_parent(start: Path) -> str | None:
        """Walk up `start.parents` until we hit a dir name that actually
        identifies a project. Strip a leading dot so `.greenbone` -> 'greenbone'."""
        for parent in start.parents:
            pn = parent.name
            if not pn:
                continue
            if pn in PATH_NOISE or pn in WALK_THROUGH_DIRS:
                continue
            return pn.lstrip(".") or None
        return None

    # 1. /home/hy/apps/<NAME>/...    explicit user convention wins.
    m = re.search(r"/apps/([A-Za-z0-9_.-]+)(?:/|\b)", cmdline)
    if m:
        return m.group(1)

    # 2. python -m <module>          first dotted segment names it.
    if "-m" in parts:
        i = parts.index("-m")
        if i + 1 < len(parts):
            mod = parts[i + 1].split(".")[0]
            if mod and mod not in PATH_NOISE:
                return mod

    # 3. <interp> path/to/script.{py,js,ts,...}
    #    The script path itself usually names the project better than any
    #    enclosing dotfile dir (e.g. .hermes/.../whatsapp-bridge/bridge.js
    #    should yield "whatsapp-bridge", not "hermes").
    SCRIPT_EXTS = (".py", ".js", ".mjs", ".ts", ".cjs", ".rb", ".php", ".pl")
    for p in parts[1:]:
        if not p.endswith(SCRIPT_EXTS) or "/" not in p:
            continue
        sp = Path(p)
        stem = sp.stem
        if stem in GENERIC_STEMS:
            up = _meaningful_parent(sp)
            if up:
                return up
        elif stem and stem not in PATH_NOISE:
            return stem

    # 4. streamlit run X.py / similar `<tool> run <something>` pattern.
    for i, p in enumerate(parts):
        if p == "run" and i + 1 < len(parts):
            cand = Path(parts[i + 1]).stem
            if cand and cand not in PATH_NOISE and cand not in GENERIC_STEMS:
                return cand

    # 5. /home/hy/.<NAME>/...        last-resort hidden-project convention.
    m = re.search(r"/home/[^/]+/\.([A-Za-z][A-Za-z0-9_-]+)(?:/|\b)", cmdline)
    if m and m.group(1) not in PATH_NOISE:
        return m.group(1)

    return None


def derive_name(li: Listener) -> str:
    """Best-effort short label for a listener."""
    if li.port in SYSTEM_PORTS:
        return SYSTEM_PORTS[li.port]
    if li.pid == 0:
        # Privileged process whose cmdline we can't read.
        return f"(权限不足) :{li.port}"

    # Specific tool name wins immediately.
    proc = (li.proc or "").lower()
    if proc and proc not in GENERIC_PROCS:
        # Some tools should still get a project hint appended (multiple ollama
        # instances, multiple redis-server, etc.).
        hint = _name_from_cmdline(proc, li.cmdline)
        if hint and hint != proc:
            return f"{proc}-{hint}"
        return proc

    # Generic interpreter — derive from cmdline.
    name = _name_from_cmdline(proc, li.cmdline)
    if name:
        return name

    return proc or f"pid-{li.pid}"


# ---------- Aggregation ----------

def collect_rows() -> list[Row]:
    listeners = scan_listeners()
    # Group by (port, proto). v4 + v6 listeners on the same port collapse
    # into one row (the v4 entry wins as holder; v6 becomes an alias).
    by_port: dict[tuple[str, int], list[Listener]] = {}
    for li in listeners:
        by_port.setdefault((li.proto, li.port), []).append(li)

    rows: list[Row] = []
    for (proto, port), lis in by_port.items():
        # Prefer the listener with a known PID; among those, prefer v4.
        lis_sorted = sorted(
            lis,
            key=lambda x: (x.pid == 0, x.is_ipv6, x.host),
        )
        head = lis_sorted[0]
        aliases = lis_sorted[1:]
        rows.append(Row(
            name=derive_name(head),
            port=port, host=head.host, proto=proto,
            holder=head, aliases=aliases,
        ))

    # Disambiguate duplicate names: if two rows would share the same display
    # name, suffix `-N` so the user can tell them apart.
    seen: dict[str, int] = {}
    for r in rows:
        n = seen.get(r.name, 0) + 1
        seen[r.name] = n
    counts = dict(seen)
    seen2: dict[str, int] = {}
    for r in rows:
        if counts.get(r.name, 0) > 1:
            seen2[r.name] = seen2.get(r.name, 0) + 1
            r.name = f"{r.name}-{seen2[r.name]}"

    rows.sort(key=lambda r: (r.port,))
    return rows


# ---------- UI helpers ----------

def make_status_dot(color: str = "#26a269") -> Gtk.Label:
    lbl = Gtk.Label(label="●")
    lbl.add_css_class("status-dot")
    lbl.set_markup(f"<span foreground='{color}' size='x-large' weight='bold'>●</span>")
    return lbl


# ---------- Main Window ----------

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title=APP_NAME)

        self._state = load_state()
        w = max(720, min(int(self._state.get("width", 1000)), 10000))
        h = max(480, min(int(self._state.get("height", 640)), 10000))
        self.set_default_size(w, h)
        self.set_size_request(720, 480)
        if self._state.get("maximized"):
            self.maximize()

        # When True, also list well-known system ports (53/631/5353/...).
        self._show_system = bool(self._state.get("show_system", False))

        self._rows: list[Row] = []
        self._selected_key: str | None = None
        self._poll_id: int | None = None
        self._last_scan_at: float = 0.0

        self._build_ui()
        self._install_shortcuts()
        self.connect("close-request", self._on_close_request)
        self.refresh()
        self._start_polling()

    # ----- UI construction -----

    def _build_ui(self) -> None:
        toast_overlay = Adw.ToastOverlay()
        self.set_content(toast_overlay)
        self._toasts = toast_overlay

        split = Adw.NavigationSplitView()
        split.set_max_sidebar_width(360)
        split.set_min_sidebar_width(280)
        toast_overlay.set_child(split)

        # ---- Sidebar ----
        sb_page = Adw.NavigationPage()
        sb_page.set_title(APP_NAME)
        side = Adw.ToolbarView()
        sb_page.set_child(side)

        sb_header = Adw.HeaderBar()
        side.add_top_bar(sb_header)

        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("刷新 (F5)")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        sb_header.pack_start(refresh_btn)

        menu = Gio.Menu()
        menu.append("显示系统端口（53/631/...）", "app.toggle-system")
        menu.append("关于", "app.about")
        menu.append("退出 (Ctrl+Q)", "app.quit")
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(menu)
        sb_header.pack_end(menu_btn)

        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("搜索应用或端口…")
        self._search.connect("search-changed", lambda *_: self._refresh_list())
        sb_header.set_title_widget(self._search)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        self._listbox = Gtk.ListBox()
        self._listbox.add_css_class("navigation-sidebar")
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.connect("row-selected", self._on_row_selected)
        scroller.set_child(self._listbox)
        side.set_content(scroller)

        self._summary = Gtk.Label(xalign=0, margin_start=12, margin_end=12,
                                  margin_top=8, margin_bottom=8)
        self._summary.add_css_class("dim-label")
        side.add_bottom_bar(self._summary)

        split.set_sidebar(sb_page)

        # ---- Detail pane ----
        det_page = Adw.NavigationPage()
        det_page.set_title("详情")
        det_view = Adw.ToolbarView()
        det_header = Adw.HeaderBar()
        det_view.add_top_bar(det_header)

        self._detail_title = Adw.WindowTitle(title="选择左侧应用查看详情", subtitle="")
        det_header.set_title_widget(self._detail_title)

        self._detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._detail_box.set_margin_top(12)
        self._detail_box.set_margin_bottom(12)
        self._detail_box.set_margin_start(18)
        self._detail_box.set_margin_end(18)

        det_scroll = Gtk.ScrolledWindow()
        det_scroll.set_vexpand(True)
        det_scroll.set_child(self._detail_box)
        det_view.set_content(det_scroll)

        det_page.set_child(det_view)
        split.set_content(det_page)

        css = Gtk.CssProvider()
        css.load_from_data(b"""
        .status-dot { padding: 0 6px; }
        .pid-pill { padding: 2px 8px; border-radius: 6px;
                    background: alpha(@theme_fg_color, 0.08); font-family: monospace; }
        .cmdline { font-family: monospace; font-size: 0.92em; }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _install_shortcuts(self) -> None:
        ctrl = Gtk.ShortcutController()
        for accel, cb in (
            ("F5", lambda *_: (self.refresh(), True)[1]),
            ("<primary>r", lambda *_: (self.refresh(), True)[1]),
            ("<primary>q", lambda *_: (self.get_application().quit(), True)[1]),
            ("<primary>w", lambda *_: (self.close(), True)[1]),
            ("<primary>f", lambda *_: (self._search.grab_focus(), True)[1]),
        ):
            sc = Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(accel),
                Gtk.CallbackAction.new(cb),
            )
            ctrl.add_shortcut(sc)
        self.add_controller(ctrl)

    # ----- polling -----

    def _start_polling(self) -> None:
        if self._poll_id is None:
            self._poll_id = GLib.timeout_add_seconds(POLL_SECONDS, self._on_tick)

    def _on_tick(self) -> bool:
        self.refresh(silent=True)
        return GLib.SOURCE_CONTINUE

    # ----- data refresh -----

    def refresh(self, silent: bool = False) -> None:
        self._rows = collect_rows()
        self._last_scan_at = time.time()
        self._refresh_list()
        if self._selected_key:
            for row in self._rows:
                if row.key == self._selected_key:
                    self._render_detail(row)
                    break
            else:
                # Selected port has gone away — clear detail pane.
                self._selected_key = None
                self._render_detail(None)
        if not silent:
            self._toast(f"已刷新 ({len(self._rows)} 个监听端口)")

    def _refresh_list(self) -> None:
        child = self._listbox.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._listbox.remove(child)
            child = nxt

        query = (self._search.get_text() or "").strip().lower()

        visible = 0
        unknown = 0
        system = 0
        for row in self._rows:
            is_system = row.port in SYSTEM_PORTS
            if is_system:
                system += 1
                if not self._show_system and not query:
                    continue
            if row.holder.pid == 0:
                unknown += 1

            if query:
                if (query not in row.name.lower()
                        and query not in str(row.port)
                        and query not in (row.holder.cmdline or "").lower()):
                    continue

            visible += 1
            lr = self._make_list_row(row)
            self._listbox.append(lr)
            if self._selected_key and row.key == self._selected_key:
                self._listbox.select_row(lr)

        if not self._listbox.get_selected_row():
            sel = self._listbox.get_first_child()
            if sel:
                self._listbox.select_row(sel)

        # summary line
        parts = [f"<span foreground='#26a269'>● {len(self._rows)} 监听中</span>"]
        if unknown:
            parts.append(f"<span foreground='#9a9996'>{unknown} 权限不足</span>")
        if system and not self._show_system:
            parts.append(f"<span foreground='#9a9996'>{system} 系统端口已隐藏</span>")
        self._summary.set_markup("   ".join(parts))

    def _make_list_row(self, row: Row) -> Gtk.ListBoxRow:
        lb_row = Gtk.ListBoxRow()
        lb_row._app_row = row  # type: ignore[attr-defined]

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        color = "#9a9996" if row.holder.pid == 0 else "#26a269"
        box.append(make_status_dot(color))

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        name_lbl = Gtk.Label(label=row.name, xalign=0)
        name_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        text.append(name_lbl)
        sub = Gtk.Label(xalign=0)
        host_short = row.host if row.host not in ("0.0.0.0", "127.0.0.1", "::", "::1") else ""
        host_str = f"{host_short}:" if host_short else ":"
        proc_str = row.holder.proc or "?"
        if row.holder.pid:
            tail = f"{proc_str}  ·  pid {row.holder.pid}"
        else:
            tail = "其他用户/系统"
        sub.set_markup(
            f"<small><span foreground='#9a9996'>{host_str}{row.port}  ·  {tail}</span></small>"
        )
        text.append(sub)
        box.append(text)

        lb_row.set_child(box)
        return lb_row

    def _on_row_selected(self, _lb, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            self._render_detail(None)
            return
        app_row: Row = row._app_row  # type: ignore[attr-defined]
        self._selected_key = app_row.key
        self._render_detail(app_row)

    # ----- detail pane -----

    def _render_detail(self, row: Row | None) -> None:
        child = self._detail_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._detail_box.remove(child)
            child = nxt

        if not row:
            self._detail_title.set_title("无选中项")
            self._detail_title.set_subtitle("没有正在监听的端口可以选中")
            return

        self._detail_title.set_title(row.name)
        self._detail_title.set_subtitle(f"端口 {row.port}  ·  {row.proto.upper()}  ·  正在监听")

        # ---- 概要卡 ----
        info = Adw.PreferencesGroup()
        info.set_title("基本信息")
        info.add(self._kv_row("应用名（自动识别）", row.name, copy=True))
        info.add(self._kv_row("端口", str(row.port), copy=True))
        info.add(self._kv_row("Host", row.host or "0.0.0.0", copy=True))
        info.add(self._kv_row("协议", row.proto.upper()))
        if row.aliases:
            extra = ", ".join(f"{a.host}" for a in row.aliases)
            info.add(self._kv_row("同端口其它绑定", extra))
        self._detail_box.append(info)

        # ---- Holder 卡 ----
        h = row.holder
        holder_grp = Adw.PreferencesGroup()
        holder_grp.set_title("当前监听进程")
        if h.pid == 0:
            ar = Adw.ActionRow()
            ar.set_title("(其他用户或内核进程)")
            ar.set_subtitle("以普通用户身份无法读取进程详情。可用 sudo ss -tlnp 查询。")
            holder_grp.add(ar)
        else:
            ar = Adw.ActionRow()
            ar.set_title(f"{h.proc or '?'} (pid {h.pid})")
            ar.set_subtitle(h.cmdline or "(无 cmdline)")
            ar.add_css_class("property")

            copy_pid = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
            copy_pid.set_tooltip_text("复制 PID")
            copy_pid.set_valign(Gtk.Align.CENTER)
            copy_pid.connect("clicked", lambda *_, p=h.pid:
                             self._copy(str(p), f"已复制 PID {p}"))
            ar.add_suffix(copy_pid)

            kill_btn = Gtk.Button(label="结束进程")
            kill_btn.add_css_class("destructive-action")
            kill_btn.set_valign(Gtk.Align.CENTER)
            kill_btn.connect("clicked", lambda *_, r=row: self._confirm_kill(r))
            ar.add_suffix(kill_btn)
            holder_grp.add(ar)

            owner_ar = Adw.ActionRow()
            owner_ar.set_title("属主")
            owner_ar.set_subtitle(h.user or "?")
            holder_grp.add(owner_ar)
        self._detail_box.append(holder_grp)

        # ---- 操作卡 ----
        actions = Adw.PreferencesGroup()
        actions.set_title("操作")

        # 在浏览器中打开 — 仅当 host 是回环或全网卡时才有意义
        url_host = "127.0.0.1" if row.host in ("0.0.0.0", "::", "127.0.0.1", "::1", "") else row.host
        url = f"http://{url_host}:{row.port}/"
        ar = Adw.ActionRow()
        ar.set_title(_("TITLE_TEST_HTTP"))
        ar.set_subtitle(url)
        ar.set_activatable(True)
        ar.connect("activated", lambda *_, u=url: self._ping_http(u))
        ar.add_suffix(Gtk.Image.new_from_icon_name("network-transmit-receive-symbolic"))
        actions.add(ar)

        ar = Adw.ActionRow()
        ar.set_title(_("TITLE_OPEN_BROWSER"))
        ar.set_subtitle(url)
        ar.set_activatable(True)
        ar.connect("activated", lambda *_, u=url: webbrowser.open(u))
        ar.add_suffix(Gtk.Image.new_from_icon_name("external-link-symbolic"))
        actions.add(ar)

        if h.pid:
            ar = Adw.ActionRow()
            ar.set_title(_("TITLE_WITR_CAUSALITY"))
            ar.set_subtitle(f"Why is this running? (witr {h.pid})")
            ar.set_activatable(True)
            ar.connect("activated", lambda *_, r=row: self._show_witr_causality(r))
            ar.add_suffix(Gtk.Image.new_from_icon_name("system-search-symbolic"))
            actions.add(ar)

            ar = Adw.ActionRow()
            ar.set_title(_("TITLE_OPEN_PROC"))
            ar.set_subtitle(f"/proc/{h.pid}")
            ar.set_activatable(True)
            ar.connect("activated", lambda *_, p=h.pid: self._open_proc_dir(p))
            ar.add_suffix(Gtk.Image.new_from_icon_name("folder-symbolic"))
            actions.add(ar)

            ar = Adw.ActionRow()
            ar.set_title(_("TITLE_KILL_PROC"))
            ar.set_subtitle(_("SUBTITLE_KILL_PROC"))
            ar.set_activatable(True)
            ar.connect("activated", lambda *_, r=row: self._confirm_kill_process(r))
            ar.add_suffix(Gtk.Image.new_from_icon_name("process-stop-symbolic"))
            actions.add(ar)

        self._detail_box.append(actions)

    def _kv_row(self, key: str, val: str, copy: bool = False) -> Adw.ActionRow:
        ar = Adw.ActionRow()
        ar.set_title(key)
        ar.set_subtitle(val)
        if copy:
            b = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
            b.set_valign(Gtk.Align.CENTER)
            b.set_tooltip_text("复制")
            b.connect("clicked", lambda *_, v=val: self._copy(v, f"已复制：{v}"))
            ar.add_suffix(b)
        return ar

    # ----- actions -----

    def _copy(self, text: str, toast_msg: str) -> None:
        clip = Gdk.Display.get_default().get_clipboard()
        clip.set(text)
        self._toast(toast_msg)

    def _toast(self, msg: str, timeout: int = 2) -> None:
        t = Adw.Toast.new(msg)
        t.set_timeout(timeout)
        self._toasts.add_toast(t)

    def _confirm_kill(self, row: Row) -> None:
        h = row.holder
        if not h.pid:
            return
        dlg = Adw.MessageDialog.new(
            self,
            f"结束 {h.proc} (pid {h.pid})？",
            f"将向占用端口 {row.port} 的进程发送 SIGTERM，2 秒后未退出再发 SIGKILL。",
        )
        dlg.add_response("cancel", "取消")
        dlg.add_response("ok", "结束进程")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")
        dlg.connect("response", self._on_kill_response, row)
        dlg.present()

    def _on_kill_response(self, dlg, resp: str, row: Row) -> None:
        if resp != "ok" or not row.holder.pid:
            return
        ok, msg = self._kill_pid(row.holder.pid)
        self._toast(msg if ok else f"结束失败：{msg}")
        # Refresh after a short grace period so the row disappears.
        GLib.timeout_add_seconds(1, lambda: (self.refresh(silent=True), False)[1])

    def _kill_pid(self, pid: int) -> tuple[bool, str]:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return True, "进程已不存在"
        except PermissionError:
            return False, "权限不足（需要 sudo）"
        except OSError as e:
            return False, str(e)
        # Give it 2 seconds to exit gracefully.
        for _ in range(20):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True, "已结束"
            time.sleep(0.1)
        try:
            os.kill(pid, signal.SIGKILL)
            return True, "已强制结束 (SIGKILL)"
        except OSError as e:
            return False, str(e)

    def _show_who(self, row: Row) -> None:
        try:
            r = subprocess.run(
                ["ss", "-tlnp", f"sport = :{row.port}"],
                capture_output=True, text=True, timeout=4,
                env={**os.environ, "LC_ALL": "C"},
            )
            out = r.stdout or r.stderr
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            out = str(e)

        if row.holder.pid:
            try:
                r2 = subprocess.run(
                    ["lsof", "-Pn", "-p", str(row.holder.pid)],
                    capture_output=True, text=True, timeout=4,
                )
                if r2.returncode == 0 and r2.stdout:
                    out += "\n\n--- lsof ---\n" + r2.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        dlg = Adw.MessageDialog.new(self, "ss / lsof 输出", "")
        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.get_buffer().set_text(out or "(无输出)")
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(720)
        scroll.set_min_content_height(360)
        scroll.set_child(tv)
        dlg.set_extra_child(scroll)
        dlg.add_response("close", "关闭")
        dlg.set_default_response("close")
        dlg.present()

    def _show_witr_causality(self, row: Row) -> None:
        if not row.holder.pid:
            return
        witr_bin = shutil.which("witr") or os.path.expanduser("~/.local/bin/witr")
        if not os.path.exists(witr_bin):
            out = "未找到 witr 可执行文件。请先运行自动更新脚本安装 witr。"
        else:
            try:
                r = subprocess.run(
                    [witr_bin, "--pid", str(row.holder.pid)],
                    capture_output=True, text=True, timeout=5,
                    env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
                )
                out = r.stdout or r.stderr or "witr 未输出任何结果"
            except Exception as e:
                out = f"调用 witr 失败：{e}"

        dlg = Adw.MessageDialog.new(self, f"进程因果链追溯 (PID {row.holder.pid})", f"witr 分析结果 — 监听端口 :{row.port}")
        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.get_buffer().set_text(out)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(700)
        scroll.set_min_content_height(360)
        scroll.set_child(tv)
        dlg.set_extra_child(scroll)
        dlg.add_response("close", "关闭")
        dlg.set_default_response("close")
        dlg.present()

    def _ping_http(self, url: str) -> None:
        def _check():
            import urllib.request
            import time
            start = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "portcheck-gui/1.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    latency = int((time.time() - start) * 1000)
                    msg = f"HTTP {resp.status} {resp.reason} ({latency}ms)"
            except urllib.error.HTTPError as e:
                latency = int((time.time() - start) * 1000)
                msg = f"HTTP {e.code} {e.reason} ({latency}ms)"
            except Exception as e:
                msg = f"连接失败: {e}"
            GLib.idle_add(lambda: self._toast(msg, timeout=4))

        import threading
        threading.Thread(target=_check, daemon=True).start()

    def _open_path(self, path: Path) -> None:
        try:
            subprocess.Popen(["xdg-open", str(path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError as e:
            self._toast(f"打开失败：{e}")

    # ----- persistence -----

    def _on_close_request(self, *_) -> bool:
        try:
            w, h = self.get_default_size()
            self._state["width"] = int(w)
            self._state["height"] = int(h)
            self._state["maximized"] = bool(self.is_maximized())
            self._state["show_system"] = bool(self._show_system)
            save_state(self._state)
        except Exception:
            pass
        return False


# ---------- Application ----------

class PortCheckApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window: MainWindow | None = None

    def do_startup(self):  # type: ignore[override]
        Adw.Application.do_startup(self)

        for name, handler in [
            ("quit", lambda *_: self.quit()),
            ("about", self._on_about),
            ("toggle-system", self._on_toggle_system),
        ]:
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", handler)
            self.add_action(act)

    def do_activate(self):  # type: ignore[override]
        if self.window is None:
            self.window = MainWindow(self)
        self.window.present()

    def _on_about(self, *_):
        if not self.window:
            return
        dlg = Adw.AboutWindow(
            transient_for=self.window,
            application_name=APP_NAME,
            application_icon="com.local.portcheck",
            developer_name="Local",
            version="0.2.0",
            comments="本机监听端口实时监控器。\n基于 ss + /proc + witr 因果链分析。",
            website="https://github.com/q514168795/portcheck-gui",
            issue_url="https://github.com/q514168795/portcheck-gui/issues",
            support_url="https://github.com/q514168795/portcheck-gui/discussions",
            license_type=Gtk.License.MIT_X11,
        )
        dlg.present()

    def _on_toggle_system(self, *_):
        if not self.window:
            return
        self.window._show_system = not self.window._show_system
        state = "显示" if self.window._show_system else "隐藏"
        self.window._toast(f"系统端口已{state}")
        self.window._refresh_list()


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    GLib.set_prgname(APP_ID)
    GLib.set_application_name(APP_NAME)
    Gtk.Window.set_default_icon_name(APP_ID)
    app = PortCheckApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
