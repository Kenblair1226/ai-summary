import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

system_prompt = """
  你是一個專業的科技趨勢分析助手,專門協助使用者分析和討論科技相關話題。請依照以下指示進行回應：
    分析架構
    先說明討論主題的背景與重要性
    總結並提供前瞻觀點

    表達方式
    如需提到人名或專有名詞,請保留原文,對談中的人名可使用first name,如果不確定是誰說的就不要使用人名
    以繁體中文輸出,不要使用markdown格式,連結要加上html標籤

    範例對話
    使用者：「最近生成式 AI 的發展如何？」
    助手回應架構：
    1. 概述近期生成式 AI 的重要進展
    2. 分析關鍵技術突破（如模型架構、訓練方法等）
    3. 討論主要應用領域與創新案例
    4. 評估對產業的影響
    5. 提出未來發展趨勢
    6. 討論需關注的議題（如倫理、隱私等）

    注意事項

    資訊準確性
    確保引用的資訊來源可靠
    明確區分事實與推測
    適時更新知識範圍

    討論深度
    根據使用者專業程度調整內容深度
    在保持專業的同時確保易懂性
    適時補充基礎知識說明


    輸出格式
    對於較長的分析內容,建議採用以下格式,但不要把主題文字放到文章中：

    主題概述：簡要說明討論主題

    核心分析：詳細的分析內容

    討論要點：提出值得進一步探討的問題
"""

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction=[ system_prompt ],
)

def summarize_text(title, content):

    response = model.generate_content(f"""
    標題：{title}
    字幕：{content}
    針對字幕內容撰寫一篇簡短文章摘要,需包含以下內容：
    第一行請綜合上述標題與內容發想一個適合的標題,以繁體中文輸出,以 \n 結尾
    第二行以後為摘要內容,文章內容只需包含對話內容的摘要,不需包含詳細討論
    """)
    response_lines = response.text.split('\n')
    title = response_lines[0]
    content = '\n'.join(response_lines[1:])
    return title, content

def generate_article(content):

    response = model.generate_content(f"""
    字幕：{content}
    針對字幕內容撰寫一篇詳細分析討論,需包含以下內容：
    文章內容只需包含細節討論,盡量詳細呈現對話內容,如有實例須包含在文章中
    """)

    return response.text


def summarize_mp3(path):
  prompt = f"""
    針對音檔內容撰寫一篇簡短文章摘要,需包含以下內容：
    第一行請以內容為主發想一個適合且幽默的標題,以 \n 結尾
    第二行以後為摘要內容,文章內容只需包含對話內容的摘要,不需包含詳細討論
    如果有不同主題可分段落呈現
    """
  myfile = genai.upload_file(path)

  return model.generate_content([myfile, prompt])
  
def article_mp3(title, path):
  prompt = f"""
    標題：{title}
    針對音檔內容撰寫一篇詳細分析討論,需包含以下內容：
    第一行請以內容及標題為主發想一個適合且幽默的標題,以 \n 結尾
    第二行以後為文章內容分析包含細節討論,如有實例須包含在文章中
    如果內容很長，請先列出大綱，再進行詳細分析
    如果有不同主題可分段落呈現,使用html<p>tag語法,並在段落最前端放上副標題
    使用html語法並盡量讓文章美觀易讀
    """
  myfile = genai.upload_file(path)

  response = model.generate_content([myfile, prompt])

  response_lines = response.text.split('\n')
  title = response_lines[0]
  content = '\n'.join(response_lines[1:])

  return title, content
  
def summarize_article(title, content):
    response = model.generate_content(f"""
    標題：{title}
    文章內容：{content}
    針對文章內容撰寫一篇詳細分析討論,需包含以下內容：
    第一行請以內容及標題為主發想一個適合且幽默的標題,以 \n 結尾
    第二行以後為文章內容分析包含細節討論,如有實例須包含在文章中
    如果有不同主題可分段落呈現,使用html<p>tag語法,並在段落最前端放上副標題
    使用html語法並盡量讓文章美觀易讀
    """)
    
    response_lines = response.text.split('\n')
    title = response_lines[0]
    content = '\n'.join(response_lines[1:])
    
    return title, content

def generate_slug(title, content):
    """Generate a WordPress-friendly slug using Gemini"""
    response = model.generate_content(f"""
    Title: {title}
    Content: {content}
    
    Generate a short URL-friendly slug for this article that meets these requirements:
    - Use only lowercase English letters, numbers, and hyphens
    - Maximum 50 characters
    - Make it SEO-friendly and readable
    - Capture the main topic
    - Do not use special characters or spaces
    - Return only the slug, nothing else
    
    Example good slugs:
    "ai-transformation-tech-industry"
    "apple-vision-pro-review"
    "microsoft-q4-earnings-report"
    """)
    
    slug = response.text.strip().lower()
    # Clean up any remaining invalid characters
    slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
    slug = slug[:50].rstrip('-')
    return slug

if __name__ == "__main__":
    # path = "allin.mp3"
    # title, content = article_mp3('DOGE kills its first bill, Zuck vs OpenAI, Google’s AI comeback with bestie Aaron Levie', path)
    # print(f"{title=}")
    # print(f"{content=}")
    slug = generate_slug("科技界風雲變幻 聚合理論的黃昏 AI的黎明", "在這次的預覽中 Jeremy首先提到 Doug O'Lafflin在新的一年中發表了一個引人注目的觀點 認為“聚合理論的時代已經過去了”這一論斷的基礎在於測試時間計算和軟體業務邊際成本的出現 Doug的觀點認為 AI正在使技術再次變得昂貴 這與網際網路時代的思維方式背道而馳。他指出 超大規模企業的商業模式主要建立在邊際成本為零的基礎上 但這個時代即將結束 未來將更加複雜且運算密集")
    print(f"{slug=}")