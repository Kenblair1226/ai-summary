import re
import logging
from llm_provider import llm_service, LLMResponse

system_prompt = """
  你是一個專業的科技趨勢分析助手,專門協助使用者分析和討論科技相關話題。請依照以下指示進行回應：
    分析架構
    先說明討論主題的背景與重要性
    總結並提供前瞻觀點與討論可能的影響

    表達方式
    如需提到人名或專有名詞,請保留原文,對談中的人名可使用first name,如果不確定是誰說的就不要使用人名
    內容中如有舉例或實際案例或經驗分享,請務必整理進文章
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
"""

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# The model configuration is now handled by the LLM service
# Configuration is loaded from environment variables

# --- Model specifically for Video Tasks ---
# Using 1.5 Flash as it's faster and cheaper for potentially long videos
# Ensure this model is available and suitable for your use case.
# Video model configuration is now handled by the LLM service

def summarize_youtube_video(video_url, **kwargs):
    """Summarizes a YouTube video using the configured LLM provider.
    Args:
        video_url: URL of the YouTube video to summarize
        **kwargs: Additional arguments to pass to the LLM service
    Returns:
        String containing the summary or None if there was an error
    """
    try:
        logging.info(f"Generating summary for video: {video_url} using LLM provider")
        prompt = f"""
針對影片內容撰寫一篇深度分析文章
文章內容只需包含對話內容的摘要,不需包含詳細討論
如果有不同主題可分段落呈現

對於較長的分析內容,建議採用以下大綱,並針對每個段落產生一個副標題
不要使用下列標題文字：
主題概述：簡要說明討論主題
核心分析：詳細的分析內容
討論要點：提出值得進一步探討的問題
"""
        response = llm_service.generate_content(
            prompt=[
                {"text": prompt},
                {"file_data": {"file_uri": video_url}}
            ],
            model_tier="heavy",
            **kwargs
        )
        logging.info(f"Successfully generated summary for {video_url}")
        return response.text
    except Exception as e:
        logging.error(f"Error generating summary for {video_url}: {e}")
        return None

def summarize_text(title, content, **kwargs):
    """Summarizes text content with a title using the configured LLM provider.
    Args:
        title: Title of the content
        content: Text content to summarize
        **kwargs: Additional arguments to pass to the LLM service
    Returns:
        Tuple containing (title, summary_content)
    """
    try:
        logging.info(f"Generating text summary using LLM provider")
        prompt = f"""
標題：{title}
字幕：{content}
針對字幕內容撰寫一篇簡短文章摘要,需包含以下內容：
第一行請綜合上述標題與內容發想一個適合的標題,以繁體中文輸出,以 \n 結尾
第二行以後為摘要內容,文章內容只需包含對話內容的摘要,不需包含詳細討論

對於較長的分析內容,建議採用以下大綱,並針對每個段落產生一個副標題,,使用h3標籤
不要使用下列標題文字：
主題概述：簡要說明討論主題
核心分析：詳細的分析內容
討論要點：提出值得進一步探討的問題
"""
        response = llm_service.generate_content(prompt, model_tier="heavy", **kwargs)
        response_lines = response.text.split('\n')
        title = response_lines[0]
        content = '\n'.join(response_lines[1:])
        return title, content
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        raise

def generate_article(content, **kwargs):
    """Generates a detailed article based on content using the configured LLM provider.
    Args:
        content: Text content to analyze
        **kwargs: Additional arguments to pass to the LLM service
    Returns:
        String containing the generated article
    """
    try:
        logging.info(f"Generating article using LLM provider")
        prompt = f"""
字幕：{content}
針對字幕內容撰寫一篇詳細分析討論,需包含以下內容：
文章內容只需包含細節討論,盡量詳細呈現對話內容,如有實例須包含在文章中

對於較長的分析內容,建議採用以下大綱,並針對每個段落產生一個副標題,,使用h3標籤
不要使用下列標題文字：
主題概述：簡要說明討論主題
核心分析：詳細的分析內容
討論要點：提出值得進一步探討的問題
"""
        response = llm_service.generate_content(prompt, model_tier="heavy", **kwargs)
        return response.text
    except Exception as e:
        logging.error(f"Error generating article: {e}")
        raise


def summarize_mp3(path, **kwargs):
    """Summarizes MP3 content using the configured LLM provider.
    Args:
        path: Path to the MP3 file
        **kwargs: Additional arguments to pass to the LLM service
    Returns:
        LLMResponse object containing the summary
    """
    try:
        logging.info(f"Generating MP3 summary using LLM provider")
        prompt = f"""
針對音檔內容撰寫一篇簡短文章摘要,需包含以下內容：
第一行請以內容為主發想一個適合且幽默的標題,以 \n 結尾
第二行以後為摘要內容,文章內容只需包含對話內容的摘要,不需包含詳細討論
如果有不同主題可分段落呈現

對於較長的分析內容,建議採用以下大綱,並針對每個段落產生一個副標題,,使用h3標籤
不要使用下列標題文字：
主題概述：簡要說明討論主題
核心分析：詳細的分析內容
討論要點：提出值得進一步探討的問題
"""
        response = llm_service.generate_content_with_media(prompt, path, model_tier="heavy", **kwargs)
        return response
    except Exception as e:
        logging.error(f"Error summarizing MP3: {e}")
        raise
  
def article_mp3(title, path, **kwargs):
    """Generates an article from an MP3 file using the configured LLM provider.
    Args:
        title: Title of the audio content
        path: Path to the MP3 file
        **kwargs: Additional arguments to pass to the LLM service
    Returns:
        Tuple containing (title, article_content)
    """
    try:
        logging.info(f"Generating article from MP3 using LLM provider")
        prompt = f"""
標題：{title}
針對音檔內容撰寫一篇詳細分析討論,需包含以下內容：
第一行請以內容及標題為主發想一個適合且幽默的標題,以 \n 結尾
第二行以後為文章內容分析包含細節討論,如有實例須包含在文章中
如果內容很長，請先列出大綱，再進行詳細分析
如果有不同主題可分段落呈現,並在段落最前端放上副標題,使用h3標籤
使用html語法並盡量讓文章美觀易讀

對於較長的分析內容,建議採用以下大綱,並針對每個段落產生一個副標題,,使用h3標籤
相似內容整合成一段,不要使用下列標題文字：
主題概述：簡要說明討論主題
核心分析：詳細的分析內容
討論要點：提出值得進一步探討的問題
"""
        response = llm_service.generate_content_with_media(prompt, path, model_tier="heavy", **kwargs)
        response_lines = response.text.split('\n')
        title = response_lines[0]
        content = '\n'.join(response_lines[1:])
        return title, content
    except Exception as e:
        logging.error(f"Error generating article from MP3: {e}")
        raise
  
def summarize_article(title, content, **kwargs):
    """Summarizes an article using the configured LLM provider.
    Args:
        title: Title of the article
        content: Content of the article
        **kwargs: Additional arguments to pass to the LLM service
    Returns:
        Tuple containing (title, summarized_content)
    """
    try:
        logging.info(f"Generating article summary using LLM provider")
        prompt = f"""
標題：{title}
文章內容：{content}
針對文章內容撰寫一篇詳細分析討論,需包含以下內容：
第一行請以內容及標題為主發想一個適合且幽默的標題,以 \n 結尾
第二行以後為文章內容分析包含細節討論,如有實例須包含在文章中
如果有不同主題可分段落呈現,並在段落最前端放上副標題
使用html語法並盡量讓文章美觀易讀

對於較長的分析內容,建議採用以下大綱,並針對每個段落產生一個副標題,,使用h3標籤
不要使用下列標題文字：
主題概述：簡要說明討論主題
核心分析：詳細的分析內容
討論要點：提出值得進一步探討的問題
"""
        response = llm_service.generate_content(prompt, model_tier="heavy", **kwargs)
        response_lines = response.text.split('\n')
        title = response_lines[0]
        content = '\n'.join(response_lines[1:])
        return title, content
    except Exception as e:
        logging.error(f"Error summarizing article: {e}")
        raise

def generate_slug(title, count=0, **kwargs):
    """Generate a WordPress-friendly slug using the configured LLM provider.
    
    Args:
        title: Title to generate slug from
        count: Internal counter for recursion (default: 0)
        **kwargs: Additional arguments to pass to the LLM service
    
    Returns:
        String containing the generated slug
    """
    try:
        logging.info(f"Generating slug using LLM provider")
        prompt = f"""
Title: {title}

Generate a short URL-friendly slug for this article that meets these requirements:
- Use only lowercase English letters, numbers, and hyphens, do not use Chinese characters
- Maximum 50 characters
- Make it SEO-friendly and readable
- Capture the main topic
- Do not use special characters or spaces or non-English words
- Return only the slug, nothing else

Example good slugs:
"ai-transformation-tech-industry"
"apple-vision-pro-review"
"microsoft-q4-earnings-report"
"""
        response = llm_service.generate_content(prompt, model_tier="light", **kwargs)
        
        slug = response.text.strip().lower()
        # Clean up any remaining invalid characters
        slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
        slug = slug[:50].rstrip('-')
        
        # Examine the slug with regex, if it contains non-alphanumeric characters or hyphens, regenerate
        if not bool(re.fullmatch(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug)) and count < 5:
            count += 1
            logging.info(f"Regenerating slug: {slug}, count: {count}")
            return generate_slug(title, count, **kwargs)
        return slug
    except Exception as e:
        logging.error(f"Error generating slug: {e}")
        # Fallback to a basic slug in case of failure
        if count >= 5:
            return ''.join(c if c.isalnum() or c == '-' else '-' for c in title[:30].lower())
        raise

def format_html_content(content):
    """Format content for Ghost CMS."""
    import re
    
    # Convert URLs to clickable links
    url_pattern = r'(https?://[^\s<]+)'
    content = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', content)
    
    # Split content into paragraphs
    paragraphs = re.split(r'\n\s*\n', content)
    
    # Process each paragraph
    formatted_paragraphs = []
    for para in paragraphs:
        if para.strip():
            # Convert single newlines to spaces within paragraphs
            para = re.sub(r'\n', ' ', para)
            # Remove any extra spaces
            para = re.sub(r'\s+', ' ', para)
            formatted_paragraphs.append(para.strip())
    
    # Join paragraphs with double newlines
    return '\n\n'.join(formatted_paragraphs)

def humanize_content(content, **kwargs):
    """Make the content more natural and conversational with proper HTML formatting.
    
    Args:
        content: Content to humanize
        **kwargs: Additional arguments to pass to the LLM service
    
    Returns:
        String containing the humanized content
    """
    try:
        logging.info(f"Humanizing content using LLM provider")
        prompt = f"""
Content: {content}

Rewrite this content to make it more natural. Requirements:
- Use a professional tone like a tech journalist writing for their blog
- Remove any stiff or formal language, but keep the main concepts
- Dive deeper into the topic and provide more context if possible
- Keep the key information and examples
- Make it feel like it was written by a human, not AI
- Keep it in Traditional Chinese
- Return only the rewritten content, no other text
- Includes important quotes from speakers (use direct quotations with attribution)
- Supporting evidence, examples, and case studies mentioned
- Any specialized terminology or concepts explained
- Connections between different segments of the discussion
- Context for the topics discussed (historical background, relevant current events, etc.)
- Areas of agreement and disagreement between speakers
- Questions raised but not fully answered
- Recommended resources mentioned during the episode

Structure the digest with clear headings and sections for easy navigation. Maintain the tone and perspective of the original speakers while presenting the information accurately.
"""
        response = llm_service.generate_content(prompt, model_tier="heavy", **kwargs)
        
        # Format the response with proper HTML
        return format_html_content(response.text.strip())
    except Exception as e:
        logging.error(f"Error humanizing content: {e}")
        return content  # Return original content on error

def find_relevant_tags_with_llm(title, content, available_tags, **kwargs):
    """Use the configured LLM provider to analyze content and suggest relevant tags from available options.
    
    Args:
        title: Title of the content
        content: Content to analyze
        available_tags: List of available tags
        **kwargs: Additional arguments to pass to the LLM service
    
    Returns:
        List of relevant tag objects
    """
    try:
        logging.info(f"Finding relevant tags using LLM provider")
        # Extract tag names for prompt
        tag_names = [tag['name'] for tag in available_tags if tag['name'].lower() != 'summary']
        tag_list = ', '.join(tag_names)
        
        prompt = f"""
Title: {title}
Content: {content}
Available tags: {tag_list}

Analyze the title and content, then suggest the most relevant tags from the available tags list.
Requirements:
- Only select tags that are truly relevant to the main topics discussed
- Focus on key themes and technologies mentioned
- Consider industry segments and companies discussed
- Do not suggest tags just because a word appears once
- Return only the relevant tag names separated by commas, nothing else
- If no tags are relevant, return "none"
"""
        response = llm_service.generate_content(prompt, model_tier="light", **kwargs)
        
        suggested_tags = response.text.strip().lower()
        if suggested_tags == "none":
            return []
            
        # Convert suggested tags back to tag objects
        relevant_tags = []
        for tag_name in [t.strip() for t in suggested_tags.split(',')]:
            matching_tags = [tag for tag in available_tags if tag['name'].lower() == tag_name]
            if matching_tags:
                relevant_tags.append({'name': matching_tags[0]['name']})
                
        return relevant_tags
    except Exception as e:
        logging.error(f"Error finding relevant tags: {e}")
        return []  # Return empty list on error

if __name__ == "__main__":
    # Test the generate_slug function
    slug = generate_slug("科技界風雲變幻 聚合理論的黃昏 AI的黎明")
    print(f"Generated slug: {slug}")