# 视频号客户端采集方案（wx-channel-collector）

基于开源项目 [ltaoo/wx_channels_download](https://github.com/ltaoo/wx_channels_download) 的微信客户端采集方案，已在 macOS（Apple Silicon）+ 微信 4.1.15 环境实测跑通。

## 实测结论（2026-11-05，本机验证通过）

| 能力 | 状态 | 说明 |
|------|------|------|
| 按账号拉取视频号作品列表 | ✅ 已验证 | 一次 API 调用返回 15 条（标题/时长/分辨率/md5/带签名视频直链） |
| 视频直链下载 | ✅ 已验证 | `finder.video.qq.com/stodownload?...` 带 token 可 HTTP 206 分段下载 |
| 分享短链获取 | ✅ 已验证 | `https://weixin.qq.com/sph/xxx` 格式 |
| 视频文件解密 | ⚠️ 待验证 | 原始文件是加密的（首字节非 `ftyp`），需用 `decodeKey` 调 `/api/channels/decrypt` |
| 公众号文章采集 | ⚠️ 半验证 | 注入生效需 `mp.enabled: true`；订阅号消息流本身是原生渲染截不到，只能采点开后的文章页 |

实测样本见 [data/xiamen_5_sample.json](data/xiamen_5_sample.json)（厦门广电视频号最近 5 条：标题 + 分享链接 + 页面链接 + 带签名直链）。

## 原理（四层）

```
微信内嵌浏览器(WeChatAppEx)
   │  HTTPS（系统代理 127.0.0.1:2023）
   ▼
MITM 代理（SunnyNet 根证书解密流量）
   │  命中 channels.weixin.qq.com / mp.weixin.qq.com
   ▼
JS 注入（hook XHR/fetch，截获接口数据，注入下载按钮）
   │  HTTP/WS → 127.0.0.1:2022
   ▼
本地 API 服务 + SQLite（content_video / content_article 等表）
```

关键点：**它不是破解微信客户端**，而是站在微信内置浏览器和服务器之间——看得见数据（TLS 解密）、能改页面（注入 JS）、还能借用页面里的登录态（cookie/ticket 复用后代调微信内部 web 接口）。所以只需在微信里打开过一次视频号页面，之后命令行即可全自动采集。

## 快速开始

详细步骤见 [docs/setup.md](docs/setup.md)。

```bash
# 1. 下载发布包（v260907 有 darwin_arm64）
# https://github.com/ltaoo/wx_channels_download/releases
unzip wx_video_download_v260907_darwin_arm64.zip -d wx_test && cd wx_test

# 2. 校验并启动（首次会请求钥匙串授权安装根证书）
shasum -a 256 -c <(grep darwin_arm64 checksums.txt)
./wx_video_download          # 前台运行，含代理+API

# 3. 确认两个端口：2022(API) 2023(代理)；系统代理会自动指向 2023

# 4. 微信里打开任意视频号主页一次（注入建立会话）

# 5. 命令行采集
python3 scripts/collect_channels.py 厦门广电 --limit 5
```

## 核心 API

见 [docs/api.md](docs/api.md)，常用：

- `GET /api/channels/contact/search?keyword=账号名` → 搜视频号账号
- `GET /api/channels/contact/feed/list?username=v2_xxx@finder` → 作品列表
- `GET /api/channels/feed/share_url?oid=xxx` → 分享短链
- `POST /api/channels/decrypt` → 解密视频文件（配合 media 里的 `decodeKey`）
- `GET /api/mp/*` → 公众号文章相关（需 `mp.enabled: true`）

## 已知限制

1. **直链时效**：`token/sign` 绑定会话，过期需重新调 feed/list 刷新。
2. **视频加密**：下载的原始文件需解密才是可播放 mp4。
3. **兼容性风险**：微信小版本更新可能破坏注入（项目 issue 里 4.1.x 系列有成功也有失败），升级微信前先备份。
4. **合规提醒**：仅限授权范围内采集，注意频率与版权。
5. **环境依赖**：系统代理指向 127.0.0.1:2023；若机器上有 Clash 等 TUN/SOCKS（7897 端口）并存，注意微信流量实际走向。

## 环境交接清单

- [x] macOS Apple Silicon + 微信 4.1.15 实测通过
- [x] 工具运行目录：`/tmp/wx_test/`（临时目录，建议迁移到正式位置）
- [x] 根证书（SunnyNet）已装入系统钥匙串并信任
- [ ] 待办：视频文件解密端到端验证（`/api/channels/decrypt`）
- [ ] 待办：公众号 `mp.enabled` 全流程验证（改配置→重启→重开文章页→检查 `/api/mp/ws_pool`）
- [ ] 待办：采集脚本的定时任务化与入库对接

## 上游依赖

- 工具本体：https://github.com/ltaoo/wx_channels_download （本仓库不含其二进制，需从上游 release 下载）
- 接口定义：上游仓库 `docs/public/openapi/` 目录
