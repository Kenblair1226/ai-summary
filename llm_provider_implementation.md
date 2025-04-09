# LLM Provider Implementation Guide

This document provides detailed implementation instructions for creating an abstraction layer to handle multiple LLM providers in your application.

## 1. File Structure

```
llm_provider.py        # Core abstraction and provider implementations
genai_helper.py        # Refactored helper using the abstraction layer
.env                   # Updated environment variables
requirements.txt       # Updated dependencies
```

## 2. `llm_provider.py` Implementation

The core of our abstraction will be the `llm_provider.py` file with the following components:

### 2.1 Base LLM Provider Class

```python
# llm_provider.py
import os
import abc
import logging
from typing import Dict, List, Union, Optional, Any

class LLMResponse:
    """Standardized response object for all LLM providers"""
    def __init__(self, text: str, raw_response: Any = None):
        self.text = text
        self.raw_response = raw_response

class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(
        self, 
        api_key: str,
        model_name: str,
        generation_config: Dict = None,
        system_prompt: str = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.generation_config = generation_config or {}
        self.system_prompt = system_prompt
        self.setup()
    
    @abc.abstractmethod
    def setup(self) -> None:
        """Set up the provider's client/configuration"""
        pass
    
    @abc.abstractmethod
    def generate_content(self, prompt: str) -> LLMResponse:
        """Generate content based on a text prompt"""
        pass
    
    @abc.abstractmethod
    def generate_content_with_media(self, prompt: str, media_file: str) -> LLMResponse:
        """Generate content based on a prompt and media file"""
        pass
    
    @abc.abstractmethod
    def is_rate_limited(self, error: Exception) -> bool:
        """Check if an error is due to rate limiting"""
        pass
```

### 2.2 Google Gemini Provider Implementation

```python
import google.generativeai as genai

class GeminiProvider(LLMProvider):
    """Implementation for Google Gemini"""
    
    def setup(self) -> None:
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=[self.system_prompt] if self.system_prompt else None
        )
    
    def generate_content(self, prompt: str) -> LLMResponse:
        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                return LLMResponse(response.text, response)
            return LLMResponse(str(response), response)
        except Exception as e:
            logging.error(f"Error generating content with Gemini: {e}")
            if self.is_rate_limited(e):
                logging.warning("Rate limit hit for Gemini")
            raise
    
    def generate_content_with_media(self, prompt: str, media_file: str) -> LLMResponse:
        try:
            file = genai.upload_file(media_file)
            response = self.model.generate_content([file, prompt])
            if hasattr(response, 'text'):
                return LLMResponse(response.text, response)
            return LLMResponse(str(response), response)
        except Exception as e:
            logging.error(f"Error generating content with media using Gemini: {e}")
            if self.is_rate_limited(e):
                logging.warning("Rate limit hit for Gemini")
            raise
    
    def is_rate_limited(self, error: Exception) -> bool:
        # Check if error message contains rate limit indicators
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "quota exceeded", 
            "resource exhausted", 
            "rate limit", 
            "too many requests"
        ])
```

### 2.3 OpenRouter Provider Implementation

```python
from openai import OpenAI

class OpenRouterProvider(LLMProvider):
    """Implementation for OpenRouter"""
    
    def setup(self) -> None:
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def generate_content(self, prompt: str) -> LLMResponse:
        try:
            # Convert generation_config to OpenAI format
            params = {
                "temperature": self.generation_config.get("temperature", 0.7),
                "max_tokens": self.generation_config.get("max_output_tokens", 1024),
                "top_p": self.generation_config.get("top_p", 0.95),
            }
            
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **params
            )
            
            if response.choices and len(response.choices) > 0:
                return LLMResponse(response.choices[0].message.content, response)
            return LLMResponse("", response)
        except Exception as e:
            logging.error(f"Error generating content with OpenRouter: {e}")
            if self.is_rate_limited(e):
                logging.warning("Rate limit hit for OpenRouter")
            raise
    
    def generate_content_with_media(self, prompt: str, media_file: str) -> LLMResponse:
        # OpenRouter doesn't directly support media files via their API
        # For images, we would need to convert to base64 and include in message
        # For audio, this might not be supported
        # This is a simplified version - would need enhancement for production
        
        try:
            import base64
            import mimetypes
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(media_file)
            if not mime_type:
                mime_type = "application/octet-stream"
                
            # Read file and encode as base64
            with open(media_file, "rb") as f:
                base64_data = base64.b64encode(f.read()).decode("utf-8")
            
            # If it's an image, we can handle it
            if mime_type.startswith("image/"):
                messages = []
                if self.system_prompt:
                    messages.append({"role": "system", "content": self.system_prompt})
                
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:{mime_type};base64,{base64_data}"}
                    ]
                })
                
                params = {
                    "temperature": self.generation_config.get("temperature", 0.7),
                    "max_tokens": self.generation_config.get("max_output_tokens", 1024),
                    "top_p": self.generation_config.get("top_p", 0.95),
                }
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **params
                )
                
                if response.choices and len(response.choices) > 0:
                    return LLMResponse(response.choices[0].message.content, response)
                return LLMResponse("", response)
            else:
                # For audio or other media, we'll return an error
                raise NotImplementedError(f"Media type {mime_type} not supported by OpenRouter provider")
                
        except Exception as e:
            logging.error(f"Error generating content with media using OpenRouter: {e}")
            if self.is_rate_limited(e):
                logging.warning("Rate limit hit for OpenRouter")
            raise
    
    def is_rate_limited(self, error: Exception) -> bool:
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "rate limit", 
            "too many requests", 
            "429", 
            "quota exceeded"
        ])
```

### 2.4 LLM Service Manager

```python
class LLMService:
    """Service to manage LLM providers and handle fallbacks"""
    
    def __init__(self, default_provider: str = "gemini"):
        self.providers = {}
        self.default_provider = default_provider
        self.init_providers()
    
    def init_providers(self):
        """Initialize available providers from environment variables"""
        # Gemini setup
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
        system_prompt = os.getenv("SYSTEM_PROMPT", "")
        
        if gemini_api_key:
            generation_config = {
                "temperature": float(os.getenv("GEMINI_TEMPERATURE", "1.0")),
                "top_p": float(os.getenv("GEMINI_TOP_P", "0.95")),
                "top_k": int(os.getenv("GEMINI_TOP_K", "40")),
                "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "8192")),
                "response_mime_type": "text/plain",
            }
            
            self.providers["gemini"] = GeminiProvider(
                api_key=gemini_api_key,
                model_name=gemini_model,
                generation_config=generation_config,
                system_prompt=system_prompt
            )
        
        # OpenRouter setup
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-opus")
        
        if openrouter_api_key:
            generation_config = {
                "temperature": float(os.getenv("OPENROUTER_TEMPERATURE", "1.0")),
                "top_p": float(os.getenv("OPENROUTER_TOP_P", "0.95")),
                "max_output_tokens": int(os.getenv("OPENROUTER_MAX_TOKENS", "8192")),
            }
            
            self.providers["openrouter"] = OpenRouterProvider(
                api_key=openrouter_api_key,
                model_name=openrouter_model,
                generation_config=generation_config,
                system_prompt=system_prompt
            )
        
        # Set default provider from env if specified
        env_default = os.getenv("DEFAULT_LLM_PROVIDER")
        if env_default and env_default in self.providers:
            self.default_provider = env_default
        
        # Fallback if default provider isn't available
        if self.default_provider not in self.providers and self.providers:
            self.default_provider = list(self.providers.keys())[0]
            logging.warning(f"Default provider not available, falling back to {self.default_provider}")
    
    def generate_content(
        self, 
        prompt: str, 
        provider: str = None, 
        fallback: bool = True
    ) -> LLMResponse:
        """Generate content with specified provider, with optional fallback"""
        provider_name = provider or self.default_provider
        
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            if not available:
                raise ValueError("No LLM providers available")
            provider_name = available[0]
            logging.warning(f"Provider {provider} not available, using {provider_name}")
        
        try:
            return self.providers[provider_name].generate_content(prompt)
        except Exception as e:
            if fallback and self.providers[provider_name].is_rate_limited(e):
                fallback_provider = self._get_fallback_provider(provider_name)
                if fallback_provider:
                    logging.warning(
                        f"Rate limit hit for {provider_name}, falling back to {fallback_provider}"
                    )
                    return self.providers[fallback_provider].generate_content(prompt)
            # If no fallback or not rate-limited, re-raise the exception
            raise
    
    def generate_content_with_media(
        self, 
        prompt: str, 
        media_file: str, 
        provider: str = None, 
        fallback: bool = True
    ) -> LLMResponse:
        """Generate content with media using specified provider, with optional fallback"""
        provider_name = provider or self.default_provider
        
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            if not available:
                raise ValueError("No LLM providers available")
            provider_name = available[0]
            logging.warning(f"Provider {provider} not available, using {provider_name}")
        
        try:
            return self.providers[provider_name].generate_content_with_media(prompt, media_file)
        except Exception as e:
            if fallback and self.providers[provider_name].is_rate_limited(e):
                fallback_provider = self._get_fallback_provider(provider_name)
                if fallback_provider:
                    logging.warning(
                        f"Rate limit hit for {provider_name}, falling back to {fallback_provider}"
                    )
                    try:
                        return self.providers[fallback_provider].generate_content_with_media(prompt, media_file)
                    except NotImplementedError:
                        # If fallback doesn't support media, try just the text prompt
                        logging.warning(
                            f"Provider {fallback_provider} doesn't support this media type, trying text-only"
                        )
                        return self.providers[fallback_provider].generate_content(
                            f"[Media described in prompt] {prompt}"
                        )
            # If no fallback or not rate-limited, re-raise the exception
            raise
    
    def _get_fallback_provider(self, current_provider: str) -> Optional[str]:
        """Get the next available provider to fallback to"""
        available = [p for p in self.providers.keys() if p != current_provider]
        if not available:
            return None
        return available[0]  # In future, could implement smarter selection

# Create a global instance for use throughout the application
llm_service = LLMService()
```

## 3. Refactoring `genai_helper.py`

The refactored `genai_helper.py` will maintain the same function signatures for backward compatibility but use the new abstraction layer internally.

### 3.1 Imports and Initial Setup

```python
import os
import re
import logging
from dotenv import load_dotenv
from llm_provider import llm_service, LLMResponse

load_dotenv()

# Set constants
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
```

### 3.2 Refactored Functions

Each function will be refactored to use the LLM service instead of directly calling Gemini API:

```python
def summarize_youtube_video(video_url, provider=None):
    """Summarizes a YouTube video using the configured LLM provider."""
    logging.info(f"Generating summary for video: {video_url} using LLM provider")
    try:
        # Prepare the prompt
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
        # Use the media content handling specific to YouTube
        response = llm_service.generate_content(
            contents=[
                {"text": prompt},
                {"file_data": {"file_uri": video_url}}
            ],
            provider=provider
        )
        
        logging.info(f"Successfully generated summary for {video_url}")
        return response.text
        
    except Exception as e:
        logging.error(f"Error generating summary for {video_url}: {e}")
        return None

def summarize_text(title, content, provider=None):
    try:
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
        response = llm_service.generate_content(prompt, provider=provider)
        response_lines = response.text.split('\n')
        title = response_lines[0]
        content = '\n'.join(response_lines[1:])
        return title, content
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        raise

# Continue refactoring all other functions in genai_helper.py...
```

### 3.3 Media Handling Functions

Special attention for functions that handle media:

```python
def summarize_mp3(path, provider=None):
    try:
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
        response = llm_service.generate_content_with_media(prompt, path, provider=provider)
        return response
    except Exception as e:
        logging.error(f"Error summarizing MP3: {e}")
        raise
```

## 4. Environment Variables

Update your `.env` file to include:

```
# Google Gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-pro-exp-03-25
GEMINI_TEMPERATURE=1.0
GEMINI_TOP_P=0.95
GEMINI_TOP_K=40
GEMINI_MAX_TOKENS=8192

# OpenRouter 
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=anthropic/claude-3-opus
OPENROUTER_TEMPERATURE=1.0
OPENROUTER_TOP_P=0.95
OPENROUTER_MAX_TOKENS=8192

# LLM Service Configuration
DEFAULT_LLM_PROVIDER=gemini  # or openrouter
SYSTEM_PROMPT=your_system_prompt
```

## 5. Requirements.txt Update

Update `requirements.txt` to include:

```
openai>=1.0.0  # For OpenRouter API
```

## 6. Error Handling Strategies

### 6.1 Rate Limit Detection

Different providers have different ways of indicating rate limits:

- **Google Gemini**: Often returns errors containing phrases like "quota exceeded" or "resource exhausted"
- **OpenRouter**: Typically returns HTTP 429 errors with "too many requests" messages

Our implementation detects these error patterns and triggers fallbacks when appropriate.

### 6.2 Graceful Degradation

When media handling isn't supported by a fallback provider, the system attempts to:

1. First try the media with the fallback provider
2. If that fails, fall back to text-only mode with additional context

## 7. Testing Strategies

Test the implementation in stages:

1. Test individual provider implementations with simple prompts
2. Test fallback mechanism by deliberately triggering rate limits
3. Test with media files to ensure proper handling
4. Test end-to-end workflows from your application

## 8. Deployment Considerations

When deploying:

1. Ensure all API keys are securely stored as environment variables
2. Monitor usage across providers to manage costs
3. Consider implementing a caching layer for frequently requested content