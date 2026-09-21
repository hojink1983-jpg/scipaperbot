import requests
import os
from datetime import datetime

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

def search_papers(keyword, limit=3):
    """Crossref API로 논문을 찾고, 지정된 우수 저널만 필터링하는 함수"""
    url = "https://api.crossref.org/works"
    
    # 우수 저널에서만 골라내야 하므로, 넉넉하게 최근 논문 50개를 먼저 가져옵니다.
    params = {
        "query": keyword,
        "select": "title,URL,container-title", # container-title이 저널 이름입니다.
        "sort": "published",
        "order": "desc",
        "rows": 50 
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        items = data.get('message', {}).get('items', [])
        
        results = []
        for item in items:
            if 'title' in item and 'URL' in item and 'container-title' in item:
                title = item['title'][0]
                link = item['URL']
                # 저널 이름을 소문자로 변환
                journal_name = item['container-title'][0].lower() 
                
                # 가져온 논문의 저널 이름이 TARGET_JOURNALS 목록에 포함되어 있는지 확인
                if any(target in journal_name for target in TARGET_JOURNALS):
                    results.append({
                        "title": title,
                        "link": link,
                        "journal": item['container-title'][0] # 원래 대소문자 저널명
                    })
                    
            # 원하는 개수(limit)만큼 찾았으면 탐색 종료
            if len(results) >= limit:
                break
                
        return results
    except Exception as e:
        print(f"검색 중 에러 발생: {e}")
        return []

def send_telegram_message(text):
    """텔레그램 전송 함수"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML", 
        "disable_web_page_preview": True 
    }
    requests.post(url, data=payload)

def main():
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    final_message = f"📚 <b>{today_str} Top Journal (Q1/Q2) 논문 알림</b>\n\n"
    
    for topic_name, keyword in TOPICS.items():
        final_message += f"<b>[{topic_name}]</b>\n"
        
        # 주제별로 타겟 저널에 속한 논문만 최대 3개 추출
        papers = search_papers(keyword, limit=3)
        
        if papers:
            for paper in papers:
                final_message += f"🔹 <b>{paper['title']}</b>\n"
                final_message += f"📓 <i>{paper['journal']}</i>\n" # 어떤 저널인지 표시
                final_message += f"🔗 {paper['link']}\n\n"
        else:
            final_message += "🔸 오늘은 지정하신 우수 저널에 새로 업데이트된 논문이 없습니다.\n\n"
            
        final_message += "ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n\n"
        
    send_telegram_message(final_message)
    print("메시지 전송 완료!")

if __name__ == "__main__":
    main()
