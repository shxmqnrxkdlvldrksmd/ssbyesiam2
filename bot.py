# -*- coding: utf-8 -*-
"""민주당·국회·청와대 기사 → 텔레그램 채널 발송 봇.

사용법
  python bot.py            # 수집 후 발송 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 환경변수 필요)
  python bot.py --dry-run  # 발송 없이 걸린 기사만 화면에 출력
  python bot.py --seed     # 지금 있는 기사를 '본 것'으로만 기록 (첫 실행 도배 방지)
"""
import argparse
import calendar
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

import config

KST = timezone(timedelta(hours=9))
SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen.json")
UA = "Mozilla/5.0 (compatible; politics-news-bot/1.0)"


# ── 중복 기록 ─────────────────────────────────────────────
def load_seen():
    if not os.path.exists(SEEN_PATH):
        return None
    with open(SEEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen):
    cutoff = time.time() - config.SEEN_KEEP_DAYS * 86400
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=0, sort_keys=True)


def title_key(title):
    """언론사마다 붙는 말머리·기호를 지워 같은 기사(같은 제목)를 하나로 본다."""
    t = re.sub(r"^\s*[\[\(【<][^\]\)】>]{1,12}[\]\)】>]\s*", "", title)
    t = re.sub(r"[^0-9A-Za-z가-힣]", "", t)
    return hashlib.sha1(t[:40].encode()).hexdigest()[:16]


# ── 수집 ─────────────────────────────────────────────
def split_source(title, entry, feed_name):
    """구글뉴스 제목은 '제목 - 언론사' 형식이라 언론사를 떼어낸다."""
    src = (entry.get("source") or {}).get("title")
    if feed_name == "구글뉴스":
        m = re.match(r"^(.*)\s+-\s+([^-]{1,30})$", title)
        if m:
            title, src = m.group(1), src or m.group(2)
    return title.strip(), (src or feed_name).strip()


def classify(title, fixed):
    tags = [c for c, words in config.CATEGORIES.items() if any(w in title for w in words)]
    if not tags and fixed:  # 제목엔 키워드가 없지만 검색 결과로 들어온 기사
        tags = [fixed]
    return tags


def fetch_all():
    now = time.time()
    max_age = config.MAX_AGE_HOURS * 3600
    items, failed = [], []
    for feed in config.FEEDS:
        try:
            r = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=15)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            if parsed.bozo and not parsed.entries:
                raise ValueError("RSS 해석 실패")
        except Exception as e:
            failed.append(f'{feed["name"]}: {e.__class__.__name__} {str(e)[:80]}')
            continue
        for e in parsed.entries:
            raw = html.unescape(e.get("title", "")).strip()
            if not raw or any(x in raw for x in config.EXCLUDE):
                continue
            ts_struct = e.get("published_parsed") or e.get("updated_parsed")
            ts = calendar.timegm(ts_struct) if ts_struct else now
            if now - ts > max_age:
                continue
            title, source = split_source(raw, e, feed["name"])
            tags = classify(title, feed.get("category"))
            if not tags:
                continue
            items.append({"title": title, "source": source, "link": e.get("link", ""),
                          "ts": ts, "tags": tags, "key": title_key(title)})
    # 같은 제목이 여러 피드에서 오면 태그를 합쳐 하나로
    merged = {}
    for it in items:
        if it["key"] in merged:
            m = merged[it["key"]]
            m["tags"] += [t for t in it["tags"] if t not in m["tags"]]
            m["ts"] = min(m["ts"], it["ts"])
        else:
            merged[it["key"]] = it
    return sorted(merged.values(), key=lambda x: x["ts"]), failed


# ── 발송 ─────────────────────────────────────────────
def format_msg(it):
    tags = " ".join(f"[{t}]" for t in it["tags"])
    when = datetime.fromtimestamp(it["ts"], KST).strftime("%m.%d %H:%M")
    return (f'<b>{html.escape(tags)}</b> <a href="{html.escape(it["link"], quote=True)}">'
            f'{html.escape(it["title"])}</a>\n{html.escape(it["source"])} · {when}')


def send(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
               "disable_web_page_preview": not config.LINK_PREVIEW}
    for _ in range(3):
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code == 429:
            time.sleep(r.json().get("parameters", {}).get("retry_after", 5) + 1)
            continue
        if not r.ok:
            print(f"  발송 실패 {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return r.ok
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", action="store_true")
    args = ap.parse_args()

    seen = load_seen()
    first_run = seen is None
    seen = seen or {}

    items, failed = fetch_all()
    for f in failed:
        print(f"피드 실패 · {f}")
    new = [it for it in items if it["key"] not in seen]
    print(f"수집 {len(items)}건 / 새 기사 {len(new)}건")

    if args.dry_run:
        for it in new:
            print("-", format_msg(it).replace("\n", " | "))
        return

    if args.seed or first_run:
        for it in new:
            seen[it["key"]] = it["ts"]
        save_seen(seen)
        print("첫 실행: 기존 기사는 기록만 하고 발송하지 않았습니다. 다음 실행부터 새 기사가 올라갑니다.")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        sys.exit("TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 환경변수가 필요합니다.")

    sent = 0
    for it in new[-config.MAX_POSTS_PER_RUN:]:
        if send(token, chat_id, format_msg(it)):
            sent += 1
        time.sleep(config.SEND_INTERVAL_SEC)
    for it in new:  # 한도 초과로 못 보낸 오래된 기사도 다시 쌓이지 않게 기록
        seen[it["key"]] = it["ts"]
    save_seen(seen)
    print(f"발송 {sent}건")


if __name__ == "__main__":
    main()
