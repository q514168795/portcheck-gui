# Port Checker (portcheck-gui) 🌐

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GUI: GTK4 / Libadwaita](https://img.shields.io/badge/GUI-GTK4%20%2F%20Libadwaita-brightgreen)](https://gitlab.gnome.org/GNOME/libadwaita)
[![Languages: En / Es / Zh](https://img.shields.io/badge/i18n-English%20%7C%20Espa%C3%B1ol%20%7C%20%E4%B8%AD%E6%96%87-blueviolet)]()
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()

[English](#english) | [Español](#español) | [简体中文](#简体中文)

---

## English

A modern, fast, and lightweight **Linux Desktop Port & Process Monitor** built with GTK4 and Libadwaita. It helps developers and sysadmins inspect active TCP/UDP listening ports, test HTTP connectivity, and trace process causality chains.

![Port Checker Screenshot](https://raw.githubusercontent.com/q514168795/portcheck-gui/main/screenshot.png) <!-- Replace with actual screenshot if available -->

### ✨ Features
* ⚡ **Live Port Scan**: Inspect listening sockets (`ss` + `/proc`) in real time.
* 🌳 **Process Causality Tracing**: Integrated with `witr` to trace parent process trees, Systemd services, and Docker container origins.
* 📡 **HTTP Connectivity Test**: In-app HTTP pinging with latency and status code toasts.
* 🛡️ **Non-root Linux Capabilities**: Inspect root-owned processes (e.g., Postfix on `:25`, Docker proxy on `:5000`) without running GUI as `sudo`.
* 🌍 **Internationalization (i18n)**: Automatic language switching for **English**, **Spanish**, and **Simplified Chinese**.
* 🎨 **Native GNOME Design**: Dark/Light mode support following GNOME Human Interface Guidelines (HIG).

### 🚀 Quick Start
```bash
git clone https://github.com/q514168795/portcheck-gui.git
cd portcheck-gui

# Setup Linux Capabilities for non-root process inspection
chmod +x setup_caps.sh
./setup_caps.sh

# Run application
./run.sh
```

### 🙏 Credits & Acknowledgments
* **[witr](https://github.com/pranshuparmar/witr)** by [@pranshuparmar](https://github.com/pranshuparmar) (Apache-2.0 License) — Used for deep process causality tree analysis.
* **[GNOME Libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)** — Modern GTK4 widget library.

---

## Español

Un monitor moderno y ligero de **puertos y procesos para Linux** construido con GTK4 y Libadwaita.

### ✨ Características
* ⚡ **Escaneo de Puertos en Tiempo Real**: Inspección de sockets activos (`ss` + `/proc`).
* 🌳 **Rastreo de Causalidad de Procesos**: Integración con `witr` para rastrear árboles de procesos padres, servicios Systemd y contenedores Docker.
* 📡 **Prueba de Conectividad HTTP**: Prueba rápida de latencia y código de estado HTTP desde la interfaz.
* 🛡️ **Capacidades de Linux**: Inspecciona procesos de `root` (como Postfix en `:25` o Docker proxy en `:5000`) sin ejecutar la interfaz con `sudo`.
* 🌍 **Soporte Multilingüe (i18n)**: Detección automática de idioma para **Inglés**, **Español** y **Chino Simplificado**.
* 🎨 **Diseño Nativo de GNOME**: Soporte para modo claro/oscuro siguiendo las guías de interfaz de GNOME (HIG).

### 🚀 Inicio Rápido
```bash
git clone https://github.com/q514168795/portcheck-gui.git
cd portcheck-gui
chmod +x setup_caps.sh
./setup_caps.sh
./run.sh
```

---

## 简体中文

基于 GTK4 + Libadwaita 构建的现代化 Linux 本机端口与进程实时监控器。

### ✨ 核心特性
* ⚡ **实时端口扫描**：调用 `ss` 与 `/proc` 引擎秒级感知本机所有 LISTEN 监听端口。
* 🌳 **进程因果链追溯**：无缝集成 `witr`，一键追溯父进程树、Systemd 服务名与 Docker 容器来源。
* 📡 **HTTP 连通性测试**：无需打开浏览器，直接在 GUI 内测试 HTTP 状态码与握手耗时。
* 🛡️ **Capabilities 免 Sudo 提权**：通过 Linux Capabilities 轻松窥透 root 进程（如 25 端口 Postfix、5000 端口 Docker proxy）。
* 🌍 **多语言国际化**：自动匹配系统的 **英文**、**西班牙语** 与 **简体中文** 语言环境。
* 🎨 **原生 GNOME 设计**：完美贴合 GNOME 桌面 HIG 设计规范，支持跟随系统切换深色/浅色主题。

### 🚀 快速使用
```bash
git clone https://github.com/q514168795/portcheck-gui.git
cd portcheck-gui

# 配置 Linux Capabilities（免 sudo 查看 root 进程）
chmod +x setup_caps.sh
./setup_caps.sh

# 启动应用
./run.sh
```

### 🙏 致谢与开源声明
* **[witr](https://github.com/pranshuparmar/witr)** (作者: [@pranshuparmar](https://github.com/pranshuparmar), Apache-2.0 协议) — 用于进程因果链深度分析。
* **[GNOME Libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)** — 现代化 Linux 桌面组件库。

---

## 📄 License
[MIT License](LICENSE)
