# 环境搭建与运行手册

实测环境：macOS（Apple Silicon）+ 微信 macOS 4.1.15 + 工具 v260907

## 1. 环境要求

| 项目 | 要求 | 检查命令 |
|------|------|---------|
| 芯片 | Apple Silicon（也有 darwin_amd64 包） | `uname -m` |
| 微信 | 桌面版已登录；**4.1.15 实测通过**，其他 4.1.x 小版本未验证，升级有兼容风险（详见 README「版本适配」） | 微信 → 关于 |
| 网络 | 能访问 GitHub（下载发布包） | — |

## 2. 下载与校验

```bash
mkdir -p ~/wx_test && cd ~/wx_test
V=v260907
curl -L --retry 3 -C - -o wxv.zip \
  "https://github.com/ltaoo/wx_channels_download/releases/download/${V}/wx_video_download_${V}_darwin_arm64.zip"
# 校验（官方 checksums）
curl -sL "https://github.com/ltaoo/wx_channels_download/releases/download/${V}/wx_video_download_${V}_checksums.txt" \
  | grep darwin_arm64
shasum -a 256 wxv.zip
unzip -o -q wxv.zip
```

## 3. 配置

仓库里提供了 [config.example.yaml](../config.example.yaml)，复制为 `config.yaml`。关键项：

```yaml
api:
  enabled: true
  hostname: "127.0.0.1"
  port: 2022
proxy:
  enabled: true
  hostname: "127.0.0.1"
  port: 2023
  system: true          # 自动设置系统代理
mp:
  enabled: true         # 公众号功能（采文章必须开启）
```

> 注意：默认发布包配置里 `mp.enabled` 为 false，采公众号文章前必须手动开启后重启。

## 4. 启动与证书授权

```bash
./wx_video_download        # 前台运行（含代理+API），Ctrl+C 退出
```

首次启动会执行 `security add-trusted-cert -d` 安装 SunnyNet 根证书到系统钥匙串，**macOS 会弹管理员密码授权框，必须输入密码确认**。已装过则不再弹。

启动成功的标志：

```bash
lsof -nP -iTCP:2022 -iTCP:2023 -sTCP:LISTEN   # 两个端口都在 LISTEN
curl -s http://127.0.0.1:2022/api/channels/status
# {"code":0,"msg":"成功","data":{"available":true}}
```

验证代理链路：

```bash
curl -s -x http://127.0.0.1:2023 https://www.baidu.com -o /dev/null -w "%{http_code}\n"
# 200
```

## 5. 建立会话（关键一步）

在**已登录的微信**里打开任意视频号主页并滚动一两屏。代理日志出现：

```
match channels.weixin.qq.com  pathname=/web/pages/profile
loaded  file=/inject/utils.js
start download websocket connection
```

说明注入与会话建立成功。之后即可脱离页面用命令行采集。

日志位置：`$(sysconfig)/T/wx_channels_download/app.log`（前台输出同时重定向更方便）。

## 6. 常见问题排查

| 现象 | 原因 | 处理 |
|------|------|------|
| 2023 端口没监听 | 用了 `server` 子命令且 proxy.enabled=false，或配置没生效 | 检查 config.yaml，用主命令启动；改配置后必须重启进程 |
| 页面无注入 | 流量没走代理 | 检查系统代理是否指向 2023；若装有 Clash/TUN（SOCKS 7897）注意流量分流 |
| 公众号页面无注入 | `mp.enabled: false` | 开启后重启工具，**关闭旧文章页重新点开**（旧页面不会补注入） |
| 改了配置不生效 | 进程启动时读一次配置 | `kill <pid>` 后重新启动；`server restart` 只管守护进程模式 |
| 文章打不开 | 证书/代理异常 | 重新走一遍第 4 步，确认系统代理与证书信任状态 |

## 7. 停止与清理

```bash
kill <wx_video_download pid>
# 恢复系统代理（如需）：系统设置 → 网络 → 详细信息 → 代理，关闭 HTTP/HTTPS 代理
# 如需卸载证书：钥匙串访问 → 系统 → 删除 SunnyNet 证书
```
