# PortCheck GUI

一个遵循 GNOME Libadwaita 原生设计规范的 Linux 本机监听端口监控与分析工具。

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![GTK4](https://img.shields.io/badge/GUI-GTK4%20%2F%20Libadwaita-brightgreen)

---

## 🌟 核心特性

- **⚡ 实时端口监控**：通过 Linux 内核原生 `ss` 引擎与 `/proc` 虚拟文件系统，毫秒级扫描所有 TCP 监听端口与占用进程。
- **🌳 进程因果链分析 (Causality)**：深度集成 [witr (Why is this running?)](https://github.com/pranshuparmar/witr)，支持一键追溯进程来源（服务/容器/父 Shell/Cronjob 关系链）。
- **📡 快捷 HTTP 连通性测试 (Ping)**：无需打开浏览器，直接在软件内测试端口响应状态码与延迟。
- **🛡️ 免 Sudo 查看 Root 进程**：通过 Linux Capabilities 机制，安全无感查阅 25/5000 等特权端口的属主信息。
- **🎨 现代化 GNOME 体验**：原生支持 Libadwaita 深色模式、自动响应式卡片与平滑动画。

---

## 📂 项目结构

```text
portcheck-gui/
├── main.py              # 主程序 (GTK4/Libadwaita 应用逻辑与 UI)
├── run.sh               # 快速启动脚本
├── setup_caps.sh        # Linux Capabilities 自动提权配置脚本
├── README.md            # 项目文档
└── LICENSE              # MIT 开源许可证
```

---

## 🚀 快速开始

### 1. 环境准备 (Ubuntu / Debian)

安装必要的依赖：

```bash
sudo apt update
sudo apt install python3 python3-gi libadwaita-1-0 iproute2
```

### 2. 权限优化 (推荐)

为使普通用户无感知查看 `root` 权限进程（如 Postfix/Docker）：

```bash
chmod +x setup_caps.sh
./setup_caps.sh
```

### 3. 运行程序

```bash
./run.sh
```

---

## 🤝 致谢与引用 (Credits & Acknowledgments)

本项目在开发过程中引用和集成了以下优质开源项目：

1. **[witr](https://github.com/pranshuparmar/witr)** (by [@pranshuparmar](https://github.com/pranshuparmar))
   - **用途**：提供强大的底层进程因果链追溯 (Causality Tree) 分析能力。
   - **协议**：Apache-2.0 License

2. **[GNOME Libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)**
   - **用途**：提供现代化 Linux 桌面 UI 控件与 HIG 设计规范。
   - **协议**：LGPL-2.1 License

---

## 📜 许可证 (License)

本项目采用 [MIT License](LICENSE) 许可证开源。
