import requests
import os
from datetime import datetime

# 1. 텔레그램 토큰과 Chat ID 불러오기
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 2. 검색할 3가지 주제와 각각의 영어 검색 키워드 설정
# 한국어 주제명 : 영어 검색어(논문 데이터베이스는 영어로 검색해야 정확함)
TOPICS = {
    "🩸 미세유체칩 기반 혈액 분리 (Blood Separation)": "microfluidic blood separation",
    "🤖 휴머노이드 응용 촉각센서 (Humanoid Tactile Sensor)": "tactile sensor humanoid robot",
    "🔬 미세유체칩 기반 면역검사 (Microfluidic Immunoassay)": "microfluidic immunoassay"
}

def search_papers(keyword, limit=3):
    """Crossref API를 사용하여 키워드로 최신 논문을 검색하는 함수"""
    # Crossref API 주소 (정확도 순으로 정렬하되, 최근 발행된 것 위주로 검색)
    url = "https://api.crossref.org/works"
    params = {
        "query": keyword,           # 검색어
        "select": "title,URL",      # 제목과 링크만 가져오기
        "sort": "published",        # 출판일 기준 정렬
        "order": "desc",            # 최신순(내림차순)
        "rows": limit               # 가져올 논문 개수
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        items = data.get('message', {}).get('items', [])
        
        results = []
        for item in items:
            # 제목과 링크가 모두 있는 데이터만 추출
            if 'title' in item and 'URL' in item:
                title = item['title'][0]
                link = item['URL']
                results.append((title, link))
        return results
    except Exception as e:
        print(f"검색 중 에러 발생: {e}")
        return []

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
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    final_message = f"📚 <b>{today_str} 맞춤형 논문 알림</b>\n\n"
    
    # 설정한 3가지 주제를 순회하며 검색 및 메시지 작성
    for topic_name, keyword in TOPICS.items():
        final_message += f"<b>[{topic_name}]</b>\n"
        
        # 주제별로 상위 3개의 논문 검색
        papers = search_papers(keyword, limit=3)
        
        if papers:
            for title, link in papers:
                final_message += f"🔹 <b>{title}</b>\n🔗 {link}\n\n"
        else:
            final_message += "🔸 오늘은 새로 업데이트된 관련 논문이 없습니다.\n\n"
            
        final_message += "ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n\n"
        
    # 텔레그램으로 최종 통합 메시지 전송
    send_telegram_message(final_message)
    print("맞춤형 논문 메시지 전송 완료!")

if __name__ == "__main__":
    main()
