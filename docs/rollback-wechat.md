# 微信升级到 4.2 后的回滚方案

## 背景

微信 macOS 客户端自动升级到 **4.2**（如 4.2.0.13）后，视频号页面不再出现注入的下载按钮，采集链路中断。

上游情况（2026-11-10 核实）：

| 事实 | 来源 |
|------|------|
| 上游最新版 **v261106**（2026-11-06）修复了「新版微信视频号页面白屏」#596 | 上游 release notes |
| 但仍有用户反馈 v261106 + 微信 4.2.0.13 依然没有下载按钮 | 上游 issue #603 |
| 用户实测：降到 4.1.x 按钮恢复；但微信下次启动会自动升回 4.2 | issue #603 评论 |
| 作者本人称其 4.2 环境有按钮（macOS/Windows 均测过） | issue #603 回复 |
| 上游**未提供**微信 4.2 的官方适配声明或版本清单 | 仓库文档核实 |

结论：4.2 的适配尚不稳定，**回滚到 4.1.15 是当前确定性最高的方案**，但必须同时阻断自动更新。

---

## 处理顺序（先低成本，再动大手术）

| 步骤 | 操作 | 成本 | 风险 |
|------|------|------|------|
| ① | 采集工具升级到 **v261106**（当前用的 v260907 已落后两个版本） | 5 分钟 | 低 |
| ② | 若仍无按钮 → 回滚微信到 **4.1.15** + 关闭自动更新 | 20 分钟 | 中（见风险章节） |
| ③ | 若回滚不可行 → 等上游适配，或改用「本地缓存文件提取」方案 | — | — |

**先做 ①**：v260907 → v261106 是纯程序升级，不动微信，且官方明确修了新版微信的页面问题。

---

## 回滚前置：必须有 4.1.15 安装包

微信升级会原地覆盖 `/Applications/WeChat.app`，**不能靠系统自带手段回退**（macOS 没有 app 版本回滚）。因此降级源必须提前留存。

已验证可用的降级源：

- 开发机（MacBook Air）上的 `/Applications/WeChat.app`，版本 **4.1.15**，**universal 二进制（x86_64 + arm64）**，1.4GB，适用于 Intel / Apple Silicon 任何 Mac
- 已打包备份：`~/Backups/WeChat_4.1.15_universal.app.zip`（`ditto` 打包，保留代码签名）

> ⚠️ 开发机自身也开启了自动更新（`SUEnableAutomaticChecks=1`，每 300 秒检查），随时可能被升到 4.2。**备份包是唯一可靠的降级源，请勿删除**，并建议另存一份到网盘/移动硬盘。

若备份丢失，其他途径：未升级的同事机器上复制、可信的第三方历史版本镜像（需自行校验签名）。

---

## 回滚步骤（在目标机上执行）

### 1. 完全退出微信

```bash
osascript -e 'quit app "WeChat"' 2>/dev/null
sleep 3
pkill -f WeChat 2>/dev/null
pgrep -lf WeChat || echo "已全部退出"
```

### 2. 备份微信数据（**必做**）

4.2 可能已升级本地数据库，降级后存在读不了或丢最近记录的风险，必须先备份。

```bash
mkdir -p ~/Backups
tar -czf ~/Backups/wechat-data-$(date +%Y%m%d-%H%M).tar.gz \
  ~/Library/Containers/com.tencent.xinWeChat \
  ~/Library/Application\ Support/com.tencent.xinWeChat 2>/dev/null
ls -lh ~/Backups/wechat-data-*.tar.gz | tail -1
```

### 3. 保留 4.2 现状，再替换为 4.1.15

```bash
# 3.1 现有 4.2 改名留档（出问题可快速切回）
sudo mv /Applications/WeChat.app /Applications/WeChat-4.2.app

# 3.2 情况 A：本机已有备份包
sudo ditto -x -k ~/Backups/WeChat_4.1.15_universal.app.zip /Applications/

# 3.3 情况 B：从开发机直接传（在开发机执行）
# rsync -a --info=progress2 /Applications/WeChat.app/ \
#   wangzhixiong@192.168.3.162:/tmp/WeChat-4.1.15.app/
# 然后在目标机：sudo ditto /tmp/WeChat-4.1.15.app /Applications/WeChat.app
```

### 4. 清理隔离属性并验证签名

```bash
sudo xattr -dr com.apple.quarantine /Applications/WeChat.app
codesign --verify --deep --strict /Applications/WeChat.app && echo "签名 OK"
defaults read /Applications/WeChat.app/Contents/Info.plist CFBundleShortVersionString
# 期望输出：4.1.15
```

### 5. 关闭自动更新（**关键**）

不做这步，微信几分钟内就会升回 4.2。Sparkle 实测配置为：

```
SUAutomaticallyUpdate = 1        # 自动安装更新
SUEnableAutomaticChecks = 1      # 自动检查
SUScheduledCheckInterval = 300   # 每 300 秒（5 分钟）检查一次
```

**必须在微信完全退出状态下写入**（否则运行中的实例会在退出时覆盖配置）：

```bash
defaults write com.tencent.xinWeChat SUEnableAutomaticChecks -bool false
defaults write com.tencent.xinWeChat SUAutomaticallyUpdate -bool false
defaults read com.tencent.xinWeChat | grep -E "SUEnableAutomaticChecks|SUAutomaticallyUpdate"
# 期望两者均为 0
```

再补一层：微信内 **设置 → 通用 → 关闭「自动更新」**。

> 若后续仍被升级，可再设置 `SUSkippedVersion` 跳过指定构建号（值为 4.2 的 `CFBundleVersion`，需从升级包或日志确认，不要猜测填写）。

### 6. 启动并登录

首次启动 4.1.15 会重新走登录流程，扫码登录后确认：

- 视频号页面出现下载按钮（或侧边/底部悬浮按钮）
- 或查看采集工具日志出现 `match channels.weixin.qq.com`

---

## 风险与缓解

| 风险 | 说明 | 缓解 |
|------|------|------|
| **本地数据不兼容** | 4.2 升级过数据库 schema，4.1.15 可能读不了，或丢最近聊天记录 | 第 2 步全量备份；保留 `WeChat-4.2.app` 可切回 |
| **再次自动升级** | Sparkle 每 5 分钟检查一次 | 第 5 步关闭两项自动更新 + UI 开关，双保险 |
| **服务端强制最低版本** | 腾讯可能要求 4.1.15 以上才能登录 | 实测 issue 中用户降级后可正常登录；若被拒则只能等上游适配 |
| **采集工具仍在旧版** | v260907 对新版页面兼容性差 | 先执行升级到 v261106 |
| **重装后需重新登录** | 降级等同重装，登录态丢失 | 提前准备好手机扫码 |

---

## 验证清单

- [ ] 微信版本显示 4.1.15（`defaults read ... CFBundleShortVersionString`）
- [ ] 自动更新已关闭（两个 SU 键为 0，且 UI 开关关闭）
- [ ] 微信能正常登录、收发消息
- [ ] 打开视频号页面出现下载按钮
- [ ] 采集工具日志出现 `match channels.weixin.qq.com` 与 `loaded utils.js`
- [ ] `curl -s http://127.0.0.1:2022/api/channels/status` 返回 `available: true`
- [ ] 实测拉取一次列表成功

---

## 附：为什么不能「在线回退」

- 微信 macOS 客户端没有内置版本回退功能，App Store 版本只能升不能降。
- 更新由 Sparkle 框架完成，安装即覆盖 `/Applications/WeChat.app`，旧版本不留存。
- 因此**唯一可行路径 = 外部留存旧版 app + 手动替换 + 阻断自动更新**。
