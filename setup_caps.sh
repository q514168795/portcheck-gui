#!/usr/bin/env bash
# 自动配置 Linux Capabilities，解决普通用户无法查看 root 进程套接字的限制

echo "正在为 ss 配置读取权限..."
sudo setcap cap_dac_read_search,cap_sys_ptrace+ep /usr/bin/ss

if command -v witr &> /dev/null; then
    echo "正在为 witr 配置读取权限..."
    sudo setcap cap_dac_read_search,cap_sys_ptrace+ep "$(which witr)"
elif [ -f "$HOME/.local/bin/witr" ]; then
    echo "正在为 ~/.local/bin/witr 配置读取权限..."
    sudo setcap cap_dac_read_search,cap_sys_ptrace+ep "$HOME/.local/bin/witr"
fi

echo "配置完成！现在无需 sudo 即可完整查看 root 进程与端口占用关系。"
