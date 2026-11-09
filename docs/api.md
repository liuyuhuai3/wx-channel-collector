# API 使用手册

本地 API 地址：`http://127.0.0.1:2022`（视频号接口需先用微信打开过一次视频号页面建立会话）。

统一返回结构：`{"code":0,"msg":"成功","data":{...}}`，业务数据基本在 `data.data` 里。

## 视频号

### 搜索账号

```bash
curl -s --get --data-urlencode "keyword=厦门广电" \
  "http://127.0.0.1:2022/api/channels/contact/search"
```

返回中关键字段：`data.data.object[].username`（形如 `v2_060000...@finder`，后续所有接口都用它）。

### 拉取作品列表（核心接口）

```bash
curl -s --get --data-urlencode "username=v2_xxx@finder" \
  "http://127.0.0.1:2022/api/channels/contact/feed/list"
```

一次返回约 15 条。每条 `object` 的关键字段：

| 字段 | 含义 |
|------|------|
| `id` | 作品 oid（页面链接用） |
| `objectNonceId` | nid（页面链接用） |
| `objectDesc.description` | 标题/文案 |
| `objectDesc.media[0].url` | 视频直链（不含签名） |
| `objectDesc.media[0].urlToken` | 签名参数，**拼在 url 后面即可直接下载** |
| `objectDesc.media[0].decodeKey` | 解密密钥（下载后的文件是加密的） |
| `objectDesc.media[0].md5sum` | 文件 md5 |
| `objectDesc.media[0].videoPlayLen / width / height / fileSize` | 时长(秒)/分辨率/字节数 |
| `createtime` | 发布时间（unix 秒） |

页面链接构造：`https://channels.weixin.qq.com/web/pages/feed?oid={id}&nid={objectNonceId}`

直链下载验证（返回 206 即可用，支持 Range 断点续传）：

```bash
curl -s -o /dev/null -m 25 -r 0-1023 -w "%{http_code}\n" "$URL$TOKEN"
```

### 分享短链

```bash
curl -s --get --data-urlencode "oid=15046464095003544756" \
  "http://127.0.0.1:2022/api/channels/feed/share_url"
# data.data.feedH5Url → https://weixin.qq.com/sph/xxxx
```

### 单条详情 / 解析分享链接

```bash
# 详情（oid + nid）
curl -s --get --data-urlencode "oid=..." --data-urlencode "nid=..." \
  "http://127.0.0.1:2022/api/channels/feed/profile"

# 分享链接 → 视频信息（返回里含 urlToken）
curl -s --get --data-urlencode "url=https://weixin.qq.com/sph/A3D4GPJJCQ" \
  "http://127.0.0.1:2022/api/channels/parse_sph"
```

### 视频解密（待端到端验证）

下载的原始文件首字节不是 `ftyp`（加密态）。media 里的 `decodeKey` + `/api/channels/decrypt` 端点用于解密成可播放 mp4。该步骤交接时**尚未实测**，是第一个待办。

## 公众号（需 `mp.enabled: true`）

| 端点 | 用途 |
|------|------|
| `GET /api/mp/ws_pool` | 查看当前注入的公众号页面会话（空=还没有文章页被注入） |
| `GET /api/mp/list` | 已采集文章列表（分页/keyword） |
| `GET /api/mp/msg/list` | 推送消息列表 |
| `GET /api/mp/article/list` | 文章列表 |
| `GET /api/mp/biz/msg/list` | 按公众号 biz 枚举历史推文 |
| `GET /api/mp/page/content` | 文章正文内容 |
| `POST /api/mp/refresh` | 刷新 |
| `GET /rss/mp` `/rss/mpbiz` | RSS 输出 |

### 公众号采集流程（重要限制）

1. 订阅号消息流（推流列表）是**原生渲染**，不经过系统代理，**无法直接截取列表**。
2. 只有**点开的具体文章页**（`mp.weixin.qq.com`）会被代理拦截注入。
3. 流程：开启 `mp.enabled` → 重启工具 → 在微信里点开目标公众号任意一篇文章 → 检查 `/api/mp/ws_pool` 出现会话 → 之后用上面的接口枚举/下载。
4. 改配置或重启后，旧文章页不会补注入，必须关闭重开。

## 采集脚本

```bash
# 搜索账号并导出前 N 条（标题/分享链接/页面链接/直链/规格）到 JSON
python3 scripts/collect_channels.py 厦门广电 --limit 5 -o output.json
```
