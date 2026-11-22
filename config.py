# -*- coding: utf-8 -*-
"""봇 설정. 키워드·피드는 여기서만 고치면 된다."""

# ── 분류 키워드 ─────────────────────────────────────────────
# 제목에 아래 단어가 하나라도 들어가면 해당 태그를 붙인다. 여러 개 걸리면 태그도 여러 개.
CATEGORIES = {
    "민주당": ["민주당", "더불어민주당", "민주 지도부", "김민석 대표", "한병도"],
    "국회": [
        "국회", "본회의", "상임위", "법사위", "예결위", "행안위", "운영위",
        "국정감사", "국감", "원내대표", "원내대책", "의원총회", "인사청문",
        "법안", "특검법", "국정조사", "여야",
    ],
    "청와대": [
        "청와대", "대통령실", "이재명 대통령", "李대통령", "李 대통령",
        "비서실장", "정무수석", "강훈식", "홍익표 수석", "국무회의", "대변인 브리핑",
    ],
}

# 제목에 이 단어가 있으면 버린다.
EXCLUDE = ["[포토]", "[사진]", "[부고]", "[인사]", "[게시판]", "[운세]", "국회의장배", "포토뉴스"]

# ── 수집 피드 ─────────────────────────────────────────────
# category 를 지정한 피드는 검색 결과 자체가 해당 분류라고 보고 키워드 검사 없이 태그를 붙인다.
# category 가 없는 피드(언론사 정치면)는 제목 키워드가 걸려야만 올린다.
def _gnews(q):
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(q)}+when:2h&hl=ko&gl=KR&ceid=KR:ko"

FEEDS = [
    # 구글 뉴스 검색: 국내 언론사 대부분을 한 번에 훑는다
    {"name": "구글뉴스", "url": _gnews("더불어민주당"), "category": "민주당"},
    {"name": "구글뉴스", "url": _gnews("국회 본회의 OR 상임위 OR 원내대표"), "category": "국회"},
    {"name": "구글뉴스", "url": _gnews("청와대 OR 대통령실"), "category": "청와대"},
    # 언론사 정치면 RSS (주소가 바뀌면 실행 기록에 '피드 실패'로 뜬다. 고치거나 지우면 됨)
    {"name": "연합뉴스", "url": "https://www.yna.co.kr/rss/politics.xml"},
    {"name": "한겨레", "url": "https://www.hani.co.kr/rss/politics/"},
    {"name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/politic_news.xml"},
    {"name": "동아일보", "url": "https://rss.donga.com/politics.xml"},
    {"name": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/politics/?outputType=xml"},
    {"name": "매일경제", "url": "https://www.mk.co.kr/rss/30200030/"},
]

# ── 동작 옵션 ─────────────────────────────────────────────
MAX_AGE_HOURS = 3          # 이보다 오래된 기사는 무시
MAX_POSTS_PER_RUN = 40     # 한 번 실행에 최대 발송 수 (도배 방지)
SEND_INTERVAL_SEC = 3.1    # 텔레그램 채널 발송 간격 (분당 20건 제한)
SEEN_KEEP_DAYS = 4         # 중복 판별 기록 보관 기간
LINK_PREVIEW = False       # 링크 미리보기 카드 표시 여부
