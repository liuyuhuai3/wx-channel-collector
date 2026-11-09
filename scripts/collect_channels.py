#!/usr/bin/env python3
"""视频号客户端采集脚本.

依赖：本机已运行 wx_video_download（API 127.0.0.1:2022），
且微信里打开过一次任意视频号页面（建立会话）。

用法:
    python3 collect_channels.py 厦门广电 --limit 5 -o output.json
    python3 collect_channels.py 厦门广电 --limit 5 --probe   # 附带验证直链可下载性
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request

API = "http://127.0.0.1:2022"


def api_get(path, **params):
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{API}{path}?{qs}", timeout=30) as r:
        body = json.load(r)
    if body.get("code") != 0:
        raise RuntimeError(f"API 错误: {body}")
    return body["data"]


def search_account(keyword):
    data = api_get("/api/channels/contact/search", keyword=keyword)
    objs = (data.get("data") or {}).get("object") or []
    if not objs:
        sys.exit(f"未搜到账号: {keyword}")
    first = objs[0]
    return first["username"], first.get("nickname", "")


def fetch_feed(username):
    data = api_get("/api/channels/contact/feed/list", username=username)
    return (data.get("data") or {}).get("object") or []


def share_url(oid):
    try:
        data = api_get("/api/channels/feed/share_url", oid=oid)
        return (data.get("data") or {}).get("feedH5Url", "")
    except Exception:
        return ""


def probe(url):
    """HEAD 前缀验证直链可用性，返回 http code。"""
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-m", "25", "-r", "0-1023", "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=30)
        return out.stdout.strip()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", help="视频号账号名称，如: 厦门广电")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("-o", "--output", default=None, help="输出 JSON 路径")
    ap.add_argument("--probe", action="store_true", help="验证直链可下载性(较慢)")
    args = ap.parse_args()

    username, nickname = search_account(args.keyword)
    print(f"账号: {nickname} ({username[:30]}...)", file=sys.stderr)

    objects = fetch_feed(username)[: args.limit]
    results = []
    for o in objects:
        m = (o.get("objectDesc") or {}).get("media") or [{}]
        m = m[0]
        oid, nid = o["id"], o.get("objectNonceId", "")
        full = (m.get("url") or "") + (m.get("urlToken") or "")
        item = {
            "title": ((o.get("objectDesc") or {}).get("description") or "").strip(),
            "share_url": share_url(oid),
            "page_url": f"https://channels.weixin.qq.com/web/pages/feed?oid={oid}&nid={nid}",
            "video_url": full,
            "duration_sec": m.get("videoPlayLen"),
            "resolution": f"{m.get('width')}x{m.get('height')}",
            "file_size": m.get("fileSize"),
            "decode_key": str(m.get("decodeKey", "")),
            "md5": m.get("md5sum", ""),
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(o.get("createtime", 0))),
        }
        if args.probe and full:
            item["probe_http"] = probe(full)
        results.append(item)
        print(f"  [{item.get('probe_http', '--')}] {item['title'][:40]}", file=sys.stderr)

    out = json.dumps({"account": {"keyword": args.keyword, "username": username, "nickname": nickname},
                      "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "count": len(results), "items": results},
                     ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(out)
        print(f"已写入 {args.output} ({len(results)} 条)", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
