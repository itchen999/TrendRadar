# coding=utf-8
"""
同花順 iFinD 財經新聞爬蟲

從同花順公開頁面抓取財經快訊與要聞，轉換為 RSSItem 格式
整合進 TrendRadar 的 RSS 管道，無需額外通知 / 儲存改動
"""

import re
import time
import random
from datetime import datetime, timezone as tz
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

import requests

from trendradar.storage.base import RSSItem


# ── 來源定義 ────────────────────────────────────────────────────────

@dataclass
class IFindSourceConfig:
    """單一 iFinD 抓取來源配置"""
    id: str
    name: str
    type: str          # "quick" | "news"
    enabled: bool = True
    max_items: int = 50


# ── 核心爬蟲 ────────────────────────────────────────────────────────

class IFindFetcher:
    """
    同花順 iFinD 財經新聞爬蟲

    支援兩種資料類型：
    - quick : 7*24 滾動快訊  (news.10jqka.com.cn/gdkx_list/)
    - news  : 財經要聞       (news.10jqka.com.cn/)
    """

    # ── 抓取端點 ──
    QUICK_NEWS_JSON_URL = (
        "https://np-cjmkt.10jqka.com.cn/mobile/api/public/v1/mtp_news_list"
    )
    QUICK_NEWS_HTML_URL = "https://news.10jqka.com.cn/gdkx_list/"
    FINANCIAL_NEWS_URL  = "https://news.10jqka.com.cn/"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.91 Mobile Safari/537.36"
        ),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Referer": "https://news.10jqka.com.cn/",
    }

    def __init__(
        self,
        sources: List[IFindSourceConfig],
        timeout: int = 15,
        request_interval: int = 1000,
        proxy_url: Optional[str] = None,
    ):
        self.sources = [s for s in sources if s.enabled]
        self.timeout = timeout
        self.request_interval = request_interval
        self.proxy_url = proxy_url
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update(self.DEFAULT_HEADERS)
        if self.proxy_url:
            s.proxies = {"http": self.proxy_url, "https": self.proxy_url}
        return s

    # ── 7*24 快訊：先嘗試 JSON API，失敗則解析 HTML ──

    def _fetch_quick_news_json(self, max_items: int) -> Optional[List[RSSItem]]:
        """嘗試呼叫同花順移動端 JSON API"""
        try:
            params = {"ctime": "0", "size": str(max_items)}
            resp = self.session.get(
                self.QUICK_NEWS_JSON_URL, params=params, timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()

            items: List[RSSItem] = []
            for entry in data.get("data", data.get("list", [])):
                title = (entry.get("title") or entry.get("content", "")).strip()
                if not title:
                    continue
                url = entry.get("url") or entry.get("link", "")
                pub = entry.get("ctime") or entry.get("time") or entry.get("pubtime", "")
                pub_iso = _normalize_timestamp(pub)

                items.append(RSSItem(
                    title=title,
                    feed_id="ifind-quick",
                    feed_name="同花順 7*24快訊",
                    url=url,
                    published_at=pub_iso,
                    summary="",
                    author="同花順",
                ))

            if items:
                print(f"[iFinD] 7*24快訊 JSON 成功：{len(items)} 條")
                return items

        except Exception as e:
            print(f"[iFinD] 7*24快訊 JSON 失敗 ({e})，嘗試 HTML 解析")

        return None

    def _fetch_quick_news_html(self, max_items: int) -> List[RSSItem]:
        """解析 7*24 滾動快訊頁面"""
        try:
            resp = self.session.get(self.QUICK_NEWS_HTML_URL, timeout=self.timeout)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return _parse_gdkx_html(resp.text, max_items)
        except Exception as e:
            print(f"[iFinD] 7*24快訊 HTML 失敗: {e}")
            return []

    def fetch_quick_news(self, max_items: int = 50) -> List[RSSItem]:
        """抓取 7*24 滾動快訊"""
        result = self._fetch_quick_news_json(max_items)
        if result is not None:
            return result
        return self._fetch_quick_news_html(max_items)

    # ── 財經要聞 ──

    def fetch_financial_news(self, max_items: int = 30) -> List[RSSItem]:
        """抓取財經要聞頭條"""
        try:
            resp = self.session.get(self.FINANCIAL_NEWS_URL, timeout=self.timeout)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            items = _parse_financial_news_html(resp.text, max_items)
            print(f"[iFinD] 財經要聞：{len(items)} 條")
            return items
        except Exception as e:
            print(f"[iFinD] 財經要聞失敗: {e}")
            return []

    # ── 統一抓取入口 ──

    def fetch_all(self) -> List[RSSItem]:
        """按配置抓取所有啟用的 iFinD 來源，回傳 RSSItem 清單"""
        all_items: List[RSSItem] = []

        for i, source in enumerate(self.sources):
            if i > 0:
                interval = self.request_interval / 1000
                time.sleep(interval + random.uniform(-0.1, 0.2) * interval)

            try:
                if source.type == "quick":
                    items = self.fetch_quick_news(source.max_items)
                elif source.type == "news":
                    items = self.fetch_financial_news(source.max_items)
                else:
                    print(f"[iFinD] 未知來源類型: {source.type}，跳過 {source.id}")
                    continue

                # 覆寫 feed_id / feed_name 為設定中指定的值
                for item in items:
                    item.feed_id = source.id
                    item.feed_name = source.name

                all_items.extend(items)

            except Exception as e:
                print(f"[iFinD] 抓取 {source.id} 失敗: {e}")

        print(f"[iFinD] 共抓取 {len(all_items)} 條財經新聞")
        return all_items


# ── HTML 解析輔助函式 ────────────────────────────────────────────────

def _parse_gdkx_html(html: str, max_items: int) -> List[RSSItem]:
    """
    解析 https://news.10jqka.com.cn/gdkx_list/ 的 7*24 滾動快訊

    頁面結構（簡化）：
      <ul class="newsList">
        <li>
          <span class="time">10:30</span>
          <a href="https://...">標題文字</a>
        </li>
        ...
      </ul>
    """
    items: List[RSSItem] = []

    # 先嘗試抓巢狀 JSON（部分頁面用 __DATA__ 或 window.__data 嵌入）
    json_match = re.search(r'window\.__(?:DATA|data)__\s*=\s*(\{.*?\});', html, re.S)
    if json_match:
        try:
            import json
            data = json.loads(json_match.group(1))
            for entry in _flatten_json_news(data)[:max_items]:
                items.append(_make_rss_item(entry, "ifind-quick", "同花順 7*24快訊"))
            if items:
                return items
        except Exception:
            pass

    # 正則解析 HTML <li> 條目
    li_pattern = re.compile(
        r'<li[^>]*>.*?'
        r'(?:<span[^>]*class="[^"]*time[^"]*"[^>]*>(.*?)</span>)?.*?'
        r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>.*?</li>',
        re.S | re.I,
    )

    today_str = datetime.now(tz.utc).strftime("%Y-%m-%d")
    for m in li_pattern.finditer(html):
        time_str, url, raw_title = m.group(1), m.group(2), m.group(3)
        title = re.sub(r'<[^>]+>', '', raw_title).strip()

        if not title or not url.startswith("http"):
            continue
        if len(title) < 5 or len(title) > 200:
            continue

        pub_iso = ""
        if time_str:
            t = time_str.strip()
            pub_iso = f"{today_str}T{t}:00+08:00" if re.match(r'\d{2}:\d{2}', t) else ""

        items.append(RSSItem(
            title=title,
            feed_id="ifind-quick",
            feed_name="同花順 7*24快訊",
            url=url,
            published_at=pub_iso,
            summary="",
            author="同花順",
        ))

        if len(items) >= max_items:
            break

    return items


def _parse_financial_news_html(html: str, max_items: int) -> List[RSSItem]:
    """
    解析 https://news.10jqka.com.cn/ 的財經要聞清單

    頁面結構（簡化）：
      <ul class="newsList" ...>
        <li><a href="https://..." title="標題">標題</a></li>
        ...
      </ul>
    """
    items: List[RSSItem] = []

    # 抓所有符合財經新聞連結的 <a> 標籤
    a_pattern = re.compile(
        r'<a\s+(?:[^>]*\s+)?href="(https?://(?:news|m)\.10jqka\.com\.cn/[^"]+)"'
        r'(?:[^>]*\s+title="([^"]*)")?[^>]*>(.*?)</a>',
        re.S | re.I,
    )

    seen: set = set()
    for m in a_pattern.finditer(html):
        url = m.group(1)
        title = (m.group(2) or re.sub(r'<[^>]+>', '', m.group(3))).strip()

        if not title or url in seen:
            continue
        if len(title) < 8 or len(title) > 150:
            continue
        # 排除導覽列 / 分類連結
        if any(kw in url for kw in ["/list/", "/index", "/channel", "/special"]):
            continue

        seen.add(url)
        items.append(RSSItem(
            title=title,
            feed_id="ifind-news",
            feed_name="同花順 財經要聞",
            url=url,
            published_at="",
            summary="",
            author="同花順",
        ))

        if len(items) >= max_items:
            break

    return items


def _flatten_json_news(data: dict) -> List[Dict]:
    """遞迴找出 JSON 中的新聞清單"""
    if isinstance(data, list):
        return data
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v
        if isinstance(v, dict):
            result = _flatten_json_news(v)
            if result:
                return result
    return []


def _make_rss_item(entry: dict, feed_id: str, feed_name: str) -> RSSItem:
    title = (entry.get("title") or entry.get("content", "")).strip()
    url   = entry.get("url") or entry.get("link", "")
    pub   = entry.get("ctime") or entry.get("time") or entry.get("pubtime", "")
    return RSSItem(
        title=title,
        feed_id=feed_id,
        feed_name=feed_name,
        url=url,
        published_at=_normalize_timestamp(pub),
        summary="",
        author="同花順",
    )


def _normalize_timestamp(raw: str) -> str:
    """將各種時間字串統一轉為 ISO 8601（帶 +08:00）"""
    if not raw:
        return ""
    raw = str(raw).strip()

    # Unix timestamp（秒或毫秒）
    if re.match(r'^\d{10}$', raw):
        dt = datetime.fromtimestamp(int(raw), tz=tz.utc)
        return dt.isoformat()
    if re.match(r'^\d{13}$', raw):
        dt = datetime.fromtimestamp(int(raw) / 1000, tz=tz.utc)
        return dt.isoformat()

    # 已是 ISO 格式
    if re.match(r'^\d{4}-\d{2}-\d{2}T', raw):
        return raw

    # "YYYY-MM-DD HH:MM:SS" 或 "YYYY-MM-DD HH:MM"
    m = re.match(r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', raw)
    if m:
        return f"{m.group(1)}T{m.group(2)}:00+08:00"

    # "HH:MM" 只有時間 → 假設今天
    m = re.match(r'^(\d{2}:\d{2})$', raw)
    if m:
        today = datetime.now(tz.utc).strftime("%Y-%m-%d")
        return f"{today}T{m.group(1)}:00+08:00"

    return ""
