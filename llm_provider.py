import os
import abc
import logging
from typing import Dict, List, Union, Optional, Any
from dotenv import load_dotenv
import litellm

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        system_prompt: str = None,
        api_base: str = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.generation_config = generation_config or {}
        self.system_prompt = system_prompt
        self.api_base = api_base
        self.setup()
    
    @abc.abstractmethod
    def setup(self) -> None:
        """Set up the provider's client/configuration"""
        pass
    
    @abc.abstractmethod
    def generate_content(self, prompt: Union[str, List, Dict]) -> LLMResponse:
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

class LiteLLMProvider(LLMProvider):
    """Implementation for LiteLLM"""
    
    def setup(self) -> None:
        litellm.api_key = self.api_key
        if self.api_base:
            litellm.api_base = self.api_base
    
    def generate_content(self, prompt: Union[str, List, Dict]) -> LLMResponse:
        try:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            
            if isinstance(prompt, str):
                messages.append({"role": "user", "content": prompt})
            elif isinstance(prompt, list):
                for item in prompt:
                    if isinstance(item, dict) and 'text' in item:
                        messages.append({"role": "user", "content": item['text']})
                    else:
                        messages.append({"role": "user", "content": str(item)})
            elif isinstance(prompt, dict) and 'text' in prompt:
                messages.append({"role": "user", "content": prompt['text']})

            response = litellm.completion(
                model=self.model_name,
                messages=messages,
                custom_llm_provider="openai",
                **self.generation_config
            )
            
            if response.choices and len(response.choices) > 0:
                return LLMResponse(response.choices[0].message.content, response)
            return LLMResponse("", response)
            
        except Exception as e:
            logging.error(f"Error generating content with LiteLLM: {e}")
            if self.is_rate_limited(e):
                logging.warning("Rate limit hit for LiteLLM")
            raise
    
    def generate_content_with_media(self, prompt: str, media_file: str) -> LLMResponse:
        raise NotImplementedError("Media handling not yet implemented for LiteLLM provider.")

    def is_rate_limited(self, error: Exception) -> bool:
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "rate limit", 
            "too many requests", 
            "429", 
            "quota exceeded"
        ])

# Import Gemini provider implementation
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
    
    def generate_content(self, prompt: Union[str, List, Dict]) -> LLMResponse:
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
        """Check if an error is due to rate limiting for Gemini."""
        # Check if error message contains rate limit indicators
        error_str = str(error).lower()
        logging.debug(f"Checking if error is rate limited: {error_str}")
        return any(phrase in error_str for phrase in [
            "quota exceeded",
            "resource exhausted",
            "rate limit",
            "too many requests",
            "429",  # Add HTTP status code
            "exceeded your current quota"  # Explicit message from the error
        ])

# Import OpenRouter provider implementation
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI package not found. OpenRouter provider will not be available.")

class OpenRouterProvider(LLMProvider):
    """Implementation for OpenRouter"""
    
    def setup(self) -> None:
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package is required for OpenRouter provider. Please install with 'pip install openai'.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def generate_content(self, prompt: Union[str, List, Dict]) -> LLMResponse:
        try:
            # Convert generation_config to OpenAI format
            params = {
                "temperature": self.generation_config.get("temperature", 0.7),
                "max_tokens": self.generation_config.get("max_output_tokens", 1024),
                "top_p": self.generation_config.get("top_p", 0.95),
            }
            
            # Handle different prompt formats
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            
            # Handle prompt based on type
            if isinstance(prompt, str):
                messages.append({"role": "user", "content": prompt})
            elif isinstance(prompt, list):
                # For lists, assume it's a list of message dictionaries or text content
                for item in prompt:
                    if isinstance(item, dict):
                        if 'text' in item:
                            messages.append({"role": "user", "content": item['text']})
                        # We don't handle file_data here as that would be sent to generate_content_with_media
                    else:
                        messages.append({"role": "user", "content": str(item)})
            elif isinstance(prompt, dict):
                # For dict, assume it contains a text key
                if 'text' in prompt:
                    messages.append({"role": "user", "content": prompt['text']})
            
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

class LLMService:
    """Service to manage LLM providers and handle fallbacks"""
    
    def __init__(self, default_provider: str = "litellm"):
        self.providers = {}
        self.default_provider = default_provider
        self.heavy_models = os.getenv("HEAVY_MODELS", "").split(',')
        self.light_models = os.getenv("LIGHT_MODELS", "").split(',')
        self.init_providers()
    
    def init_providers(self):
        """Initialize available providers from environment variables"""
        system_prompt = os.getenv("SYSTEM_PROMPT", "")

        # LiteLLM setup
        litellm_api_key = os.getenv("LITELLM_API_KEY")
        litellm_model = os.getenv("LITELLM_MODEL")
        litellm_api_base = os.getenv("LITELLM_API_BASE")

        if litellm_api_key and litellm_model:
            generation_config = {
                "temperature": float(os.getenv("LITELLM_TEMPERATURE", "1.0")),
                "top_p": float(os.getenv("LITELLM_TOP_P", "0.95")),
                "max_tokens": int(os.getenv("LITELLM_MAX_TOKENS", "8192")),
            }
            try:
                self.providers["litellm"] = LiteLLMProvider(
                    api_key=litellm_api_key,
                    model_name=litellm_model,
                    generation_config=generation_config,
                    system_prompt=system_prompt,
                    api_base=litellm_api_base
                )
                logging.info(f"LiteLLM provider initialized with model {litellm_model}")
            except Exception as e:
                logging.error(f"Failed to initialize LiteLLM provider: {e}")
        else:
            logging.warning("LITELLM_API_KEY or LITELLM_MODEL not found. LiteLLM provider not initialized.")

        # Gemini setup
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
        
        if gemini_api_key:
            generation_config = {
                "temperature": float(os.getenv("GEMINI_TEMPERATURE", "1.0")),
                "top_p": float(os.getenv("GEMINI_TOP_P", "0.95")),
                "top_k": int(os.getenv("GEMINI_TOP_K", "40")),
                "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "8192")),
                "response_mime_type": "text/plain",
            }
            
            try:
                self.providers["gemini"] = GeminiProvider(
                    api_key=gemini_api_key,
                    model_name=gemini_model,
                    generation_config=generation_config,
                    system_prompt=system_prompt
                )
                logging.info(f"Gemini provider initialized with model {gemini_model}")
            except Exception as e:
                logging.error(f"Failed to initialize Gemini provider: {e}")
        else:
            logging.warning("GEMINI_API_KEY not found in environment variables. Gemini provider not initialized.")
        
        # OpenRouter setup
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-pro-exp-03-25:free")
        
        if openrouter_api_key and OPENAI_AVAILABLE:
            generation_config = {
                "temperature": float(os.getenv("OPENROUTER_TEMPERATURE", "1.0")),
                "top_p": float(os.getenv("OPENROUTER_TOP_P", "0.95")),
                "max_output_tokens": int(os.getenv("OPENROUTER_MAX_TOKENS", "8192")),
            }
            
            try:
                self.providers["openrouter"] = OpenRouterProvider(
                    api_key=openrouter_api_key,
                    model_name=openrouter_model,
                    generation_config=generation_config,
                    system_prompt=system_prompt
                )
                logging.info(f"OpenRouter provider initialized with model {openrouter_model}")
            except Exception as e:
                logging.error(f"Failed to initialize OpenRouter provider: {e}")
        elif not OPENAI_AVAILABLE:
            logging.warning("OpenAI package not available. OpenRouter provider not initialized.")
        else:
            logging.warning("OPENROUTER_API_KEY not found in environment variables. OpenRouter provider not initialized.")
        
        # Set default provider from env if specified
        env_default = os.getenv("DEFAULT_LLM_PROVIDER")
        if env_default and env_default in self.providers:
            self.default_provider = env_default
            logging.info(f"Using {self.default_provider} as default LLM provider")
        
        # Fallback if default provider isn't available
        if self.default_provider not in self.providers and self.providers:
            self.default_provider = list(self.providers.keys())[0]
            logging.warning(f"Default provider not available, falling back to {self.default_provider}")
        
        if not self.providers:
            logging.error("No LLM providers initialized. Please check your API keys and dependencies.")
    
    def generate_content(
        self,
        prompt: Union[str, List, Dict],
        provider: str = None,
        model_tier: str = "heavy",
        fallback: bool = True
    ) -> LLMResponse:
        """Generate content with specified provider and model tier, with optional fallback"""
        provider_name = provider or self.default_provider
        models = self.heavy_models if model_tier == "heavy" else self.light_models

        if provider_name not in self.providers:
            available = list(self.providers.keys())
            if not available:
                raise ValueError("No LLM providers available")
            provider_name = available[0]
            logging.warning(f"Provider {provider} not available, using {provider_name}")

        for model in models:
            try:
                self.providers[provider_name].model_name = model
                return self.providers[provider_name].generate_content(prompt)
            except Exception as e:
                logging.error(f"Error with provider {provider_name} and model {model}: {e}")
                if fallback and self.providers[provider_name].is_rate_limited(e):
                    logging.warning(f"Rate limit hit for {provider_name} with model {model}, trying next model.")
                    continue
                else:
                    raise e
        raise Exception("All models in the tier failed.")
    
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
            # Log the full error for debugging
            logging.error(f"Error with provider {provider_name} for media content: {e}")
            
            # Check if it's a rate limit error
            is_rate_limit = self.providers[provider_name].is_rate_limited(e)
            logging.info(f"Is rate limit error for {provider_name}: {is_rate_limit}")
            
            if fallback and is_rate_limit:
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
                    except Exception as fallback_error:
                        logging.error(f"Fallback to {fallback_provider} also failed: {fallback_error}")
                        raise  # Re-raise the fallback error
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