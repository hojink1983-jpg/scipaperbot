import os
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape, unescape

import requests

# 1. 텔레그램 토큰과 Chat ID
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 2. 검색할 3가지 주제
TOPICS = {
    "🩸 미세유체칩 기반 혈액 분리": "microfluidic blood separation",
    "🤖 휴머노이드 응용 촉각센서": "tactile sensor humanoid robot",
    "🔬 미세유체칩 기반 면역검사": "microfluidic immunoassay"
}

# 3. [핵심 추가] 내 분야의 Q1, Q2 타겟 저널 목록 (소문자로 작성)
# 여기에 본인 분야의 주요 SCI(E) 저널 이름을 계속 추가하시면 됩니다.
TARGET_JOURNALS = [
    "lab on a chip",
    "biosensors and bioelectronics",
    "sensors and actuators b",
    "analytical chemistry",
    "microfluidics and nanofluidics",
    "biomicrofluidics",
    "ieee transactions on robotics",
    "ieee robotics and automation letters",
    "ieee sensors journal",
    "nature biomedical engineering",
    "science robotics",
    "advanced materials",
    "advanced functional materials"
]

# Crossref는 연락처가 담긴 User-Agent를 권장합니다 (차단/오류 확률이 줄어듭니다).
# 원하시면 저장소 Settings > Secrets에 CROSSREF_MAILTO 를 추가해 주세요.
CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "").strip()
HEADERS = {
    "User-Agent": "scipaperbot/1.0 (+https://github.com/hojink1983-jpg/scipaperbot)"
}

KST = timezone(timedelta(hours=9))


def search_papers(keyword, limit=3, retries=3):
    """Crossref API로 논문을 찾고, 지정된 우수 저널만 필터링하는 함수

    - 일시적인 429/5xx 응답은 몇 초 기다렸다가 다시 시도합니다.
    - 조회 자체가 실패하면 None을 돌려줍니다(논문이 없는 것과 구분하기 위함).
    """
    url = "https://api.crossref.org/works"

    # 우수 저널에서만 골라내야 하므로, 넉넉하게 최근 논문 50개를 먼저 가져옵니다.
    params = {
        "query": keyword,
        "select": "title,URL,container-title",  # container-title이 저널 이름입니다.
        "sort": "published",
        "order": "desc",
        "rows": 50
    }
    if CROSSREF_MAILTO:
        params["mailto"] = CROSSREF_MAILTO

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=30)

            # Crossref가 혼잡할 때 돌려주는 응답은 JSON이 아니라 HTML일 수 있습니다.
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code}")

            response.raise_for_status()
            data = response.json()
            items = data.get("message", {}).get("items", [])

            results = []
            for item in items:
                if "title" in item and "URL" in item and "container-title" in item:
                    title = item["title"][0]
                    link = item["URL"]
                    # 저널 이름을 소문자로 변환
                    journal_name = item["container-title"][0].lower()

                    # 가져온 논문의 저널 이름이 TARGET_JOURNALS 목록에 포함되어 있는지 확인
                    if any(target in journal_name for target in TARGET_JOURNALS):
                        results.append({
                            "title": title,
                            "link": link,
                            "journal": item["container-title"][0]  # 원래 대소문자 저널명
                        })

                # 원하는 개수(limit)만큼 찾았으면 탐색 종료
                if len(results) >= limit:
                    break

            return results

        except (requests.RequestException, ValueError) as e:
            last_error = e
            print(f"검색 중 에러 발생 ({attempt}/{retries}): {keyword} -> {e}")
            if attempt < retries:
                time.sleep(5 * attempt)

    print(f"검색 실패: {keyword} (마지막 오류: {last_error})")
    return None


def html_text(value):
    """Telegram HTML 모드에서 안전하도록 텍스트를 정리합니다."""
    return escape(unescape(value or ""), quote=False)


def send_telegram_message(text):
    """텔레그램 전송 함수 (실패하면 예외를 올려 워크플로가 빨간색으로 표시되게 함)"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID secret이 설정되어 있지 않습니다.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    # 텔레그램 한도(4096자)를 넘지 않도록 줄 단위로 나눠 보냅니다.
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > 4000:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)

    for chunk in chunks:
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(url, data=payload, timeout=30)
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code != 200 or not body.get("ok"):
            raise RuntimeError(
                f"텔레그램 전송 실패: HTTP {response.status_code} {body.get('description') or response.text[:200]}"
            )


def main():
    today_str = datetime.now(KST).strftime("%Y년 %m월 %d일")
    final_message = f"📚 <b>{today_str} Top Journal (Q1/Q2) 논문 알림</b>\n\n"

    failed_topics = []

    for topic_name, keyword in TOPICS.items():
        final_message += f"<b>[{topic_name}]</b>\n"

        # 주제별로 타겟 저널에 속한 논문만 최대 3개 추출
        papers = search_papers(keyword, limit=3)

        if papers is None:
            failed_topics.append(topic_name)
            final_message += "🔸 오늘은 알림을 가져오지 못했습니다. (검색 오류, 내일 다시 시도합니다)\n\n"
        elif papers:
            for paper in papers:
                final_message += f"🔹 <b>{html_text(paper['title'])}</b>\n"
                final_message += f"📓 <i>{html_text(paper['journal'])}</i>\n"  # 어떤 저널인지 표시
                final_message += f"🔗 {html_text(paper['link'])}\n\n"
        else:
            final_message += "🔸 오늘은 지정하신 우수 저널에 새로 업데이트된 논문이 없습니다.\n\n"

        final_message += "ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n\n"

    send_telegram_message(final_message)
    print("메시지 전송 완료!")

    if failed_topics:
        print(f"일부 주제 검색 실패: {', '.join(failed_topics)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
