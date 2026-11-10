# 部署机器连接手册

本文档描述视频号采集项目的**目标部署机**、**连接方式**、**连通性检查**与**部署前置条件**。

> 项目必须与已登录的微信客户端同机运行（采集依赖代理微信内嵌浏览器流量），因此"部署机器"= 一台常开、装有微信的 Mac。

---

## 1. 机器清单

| 角色 | 主机名 | IP | 用户 | 芯片/系统 | 用途 |
|------|--------|----|------|-----------|------|
| **目标部署机** | `WangzxdeMac-mini.local`（显示名：Wangzx的Mac mini） | `192.168.3.162` | `wangzhixiong` | Mac mini（待登录确认芯片/系统） | 长期运行采集 + 微信 |
| 开发调试机 | `MacBook-Air.local` | `192.168.3.31` / `192.168.101.124` | `xmt` | Apple M5 / macOS 26.6.2 | 已完成全流程实测 |

网络实测（2026-11-10）：`ping 192.168.3.162` 丢包 0%，平均延迟 9.4ms。

---

## 2. 连接方式

### 2.1 SSH（主用）

本机 `~/.ssh/config` 已存在别名：

```
Host wangzhixiong
    HostName 192.168.3.162
    User wangzhixiong
```

目标机 SSH 认证方式为 **密码登录**（`publickey,password,keyboard-interactive`），当前**尚未为本机配置免密**。

```bash
# 直连（会提示输入密码）
ssh wangzhixiong@192.168.3.162

# 或使用别名
ssh wangzhixiong
```

**配置免密（推荐，只做一次）**

```bash
ssh-copy-id wangzhixiong@192.168.3.162   # 输入一次密码
ssh wangzhixiong@192.168.3.162 'hostname' # 验证免密生效
```

配置免密后，自动化脚本、`scp`、`rsync` 都不再需要交互输入密码。

### 2.2 屏幕共享（GUI 操作用）

以下操作**必须在目标机图形界面完成**，无法纯 SSH 完成：

- 微信扫码登录
- 首次启动采集工具时的**钥匙串授权弹窗**（安装 SunnyNet 根证书，需输入管理员密码）
- 在微信里打开一次视频号主页（建立采集会话）

连接方式：macOS 自带「屏幕共享」App → 连接 `192.168.3.162`，或用 VNC 客户端。目标机需在「系统设置 → 通用 → 共享 → 屏幕共享」中开启。

### 2.3 文件共享（可选）

目标机已开启 SMB / SFTP 服务，可用于传包、取产物：

```bash
# SFTP（走 SSH 通道）
sftp wangzhixiong@192.168.3.162

# rsync 传发布包
rsync -avP wxv.zip wangzhixiong@192.168.3.162:~/wx_test/
```

Finder 中访问：`smb://192.168.3.162`。

---

## 3. 连通性检查

在开发机上执行，逐项确认：

```bash
# 1) 主机可达
ping -c 3 192.168.3.162

# 2) SSH 端口开放
nc -z -G 3 192.168.3.162 22 && echo "SSH OK"

# 3) 免密是否已配置
ssh -o BatchMode=yes -o ConnectTimeout=5 wangzhixiong@192.168.3.162 'echo LOGIN_OK'

# 4) 采集端口是否被占用（应为 free）
for p in 2022 2023; do nc -z -G 2 192.168.3.162 $p >/dev/null 2>&1 \
  && echo "port $p: 已被占用" || echo "port $p: 空闲"; done
```

**当前实测结果（2026-11-10）**

| 检查项 | 结果 |
|--------|------|
| ping 可达 | ✅ 0% 丢包，9.4ms |
| 22 端口 | ✅ 开放 |
| 免密登录 | ❌ 未配置（需 `ssh-copy-id`） |
| 2022 / 2023 端口 | ✅ 空闲 |
| 8080 端口 | ⚠️ 已被其他项目占用（不影响本项目） |

---

## 4. 部署前置条件（登录后逐项确认）

```bash
ssh wangzhixiong@192.168.3.162 '

echo "== 芯片与系统 =="; uname -m; sw_vers -productVersion
echo "== 磁盘余量 ==";   df -h /
echo "== 内存 ==";       sysctl -n hw.memsize
echo "== 已占用端口 =="; lsof -nP -iTCP -sTCP:LISTEN | head -20
echo "== 微信是否安装 =="; ls -d /Applications/WeChat.app 2>/dev/null \
  && defaults read /Applications/WeChat.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null \
  || echo 未安装
echo "== 是否已有部署 =="; pgrep -lf wx_video_download; ls -d ~/wx_test /tmp/wx_test 2>/dev/null
echo "== 证书是否已装 =="; security find-certificate -c SunnyNet /Library/Keychains/System.keychain >/dev/null 2>&1 \
  && echo 已装 || echo 未装
echo "== 防睡眠设置 =="; pmset -g | grep -E "sleep|displaysleep|womp"
'
```

### 判定标准

| 项目 | 要求 | 不满足时的处理 |
|------|------|----------------|
| 芯片 | Apple Silicon → 用 `darwin_arm64` 包；Intel → `darwin_amd64` | 按 `uname -m` 选包 |
| 磁盘余量 | **≥ 50GB**（按 0.3–1GB/天视频增长，留 1–2 个月缓冲） | 配置视频自动清理，或改存外置盘 |
| 内存 | ≥ 4GB 空闲即可（工具常驻仅 100–200MB） | — |
| 端口 2022/2023 | 空闲 | 改 `config.yaml` 里的 `api.port` / `proxy.port` |
| 微信 | 已安装并**已登录**；版本建议对齐 **4.1.15**（本项目唯一实测通过的版本，上游未公布适配范围） | 屏幕共享扫码登录；版本不符先按 README「版本适配」评估 |
| 深度睡眠 | 关闭（否则代理中断、注入失效） | `sudo pmset -a sleep 0 disksleep 0` |
| 已有部署 | 确认是否残留旧进程/旧证书 | 有则先停进程、复用证书 |

---

## 5. 部署步骤（连接后的执行顺序）

```bash
# ① 建目录
ssh wangzhixiong@192.168.3.162 'mkdir -p ~/wx_test'

# ② 传发布包（在开发机执行，包从上游 release 下载）
scp wx_video_download_v260907_darwin_arm64.zip wangzhixiong@192.168.3.162:~/wx_test/

# ③ 解压 + 放配置
ssh wangzhixiong@192.168.3.162 'cd ~/wx_test && unzip -o -q *.zip && ls'
scp config.yaml wangzhixiong@192.168.3.162:~/wx_test/

# ④ 首次启动（必须图形界面：会弹钥匙串授权）
#    通过屏幕共享在目标机终端执行：
#    cd ~/wx_test && ./wx_video_download

# ⑤ 微信里打开一次视频号主页，建立会话

# ⑥ 验证
curl -s http://127.0.0.1:2022/api/channels/status
curl -s -x http://127.0.0.1:2023 https://www.baidu.com -o /dev/null -w "%{http_code}\n"
```

详细参数与排错见 [setup.md](setup.md)，接口清单见 [api.md](api.md)。

---

## 6. 多项目共存的注意事项

目标机上已运行其他项目（8080 端口被占用），本项目与之共存需要确认：

1. **端口不冲突**：本项目固定用 2022（API）和 2023（代理），实测均空闲。若冲突，在 `config.yaml` 改端口并同步调整脚本里的 `API` 常量。
2. **系统代理影响**：本项目默认会把整机系统代理指向 `127.0.0.1:2023`（MITM）。若其他项目有依赖系统代理的 HTTP 请求，可能被接管或干扰。
   - 规避：将 `config.yaml` 中 `proxy.system` 设为 `false`，只让微信走代理（需按上游文档手动为该进程配置代理）。
3. **磁盘共享**：视频文件是主要增长项，建议单独指定下载目录并配置定期清理。
4. **睡眠策略冲突**：若其他项目也依赖机器常开，防睡眠设置可复用，无冲突。

---

## 7. 常见连接问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `Permission denied (publickey,password)` | 目标机只允许密码登录，本机密钥未授权 | 执行 `ssh-copy-id`，或直接输密码 |
| `No route to host` / ping 通但 SSH 不通 | 目标机防火墙/共享未开 | 目标机「系统设置 → 通用 → 共享 → 远程登录」开启 |
| mDNS 名称解析失败 | 网络不支持 Bonjour | 直接用 IP `192.168.3.162` |
| 连上但 `hostname` 显示不是 Mac mini | 局域网有多台同名设备（实测另有两台 M1/M4 mini） | 以 IP + mDNS 全名 `WangzxdeMac-mini.local` 双重确认 |
| 部署后工具起不来，报端口占用 | 其他项目改用了 2022/2023 | 改端口或停冲突进程 |

---

## 8. 安全提示

- 免密登录仅限可信内网（当前为 `192.168.3.x` 网段），**不要**在公网暴露 22 端口。
- 目标机根证书安装后，该机的 HTTPS 流量对本地代理可见，属敏感操作，交接时需说明并在项目结束时评估是否移除。
- 文档中不记录任何密码；认证一律走 `ssh-copy-id` 或钥匙串。
