import feedparser
import requests
import os

# 1. 수집할 저널의 RSS 피드 주소 (예시: arXiv 인공지능(AI) 분야 최신 논문)
RSS_URL = "http://export.arxiv.org/rss/cs.AI"

# 2. 환경변수에서 텔레그램 토큰과 Chat ID 불러오기 (보안을 위해 환경변수 사용)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    """텔레그램으로 메시지를 전송하는 함수"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML", 
        "disable_web_page_preview": True 
    }
    response = requests.post(url, data=payload)
    return response.json()

def main():
    # RSS 피드 파싱
    feed = feedparser.parse(RSS_URL)
    
    # 보낼 메시지 제목 작성
    message = "📚 <b>오늘의 관심 분야 최신 논문</b>\n\n"
    
    # 최신 논문 상위 5개만 추출
    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link
        # 제목과 링크를 결합
        message += f"🔹 <a href='{link}'>{title}</a>\n\n"
        
    # 텔레그램으로 전송
    send_telegram_message(message)
    print("메시지 전송 완료!")

if __name__ == "__main__":
    main()
