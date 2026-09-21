"""
GPT Agent Service for analyzing scraped data and recommending retail product values
"""
import openai
import json
import logging
import httpx
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from app.core.config import settings
from app.schemas.retail_product import RetailProductRecommendation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTService:
    """
    GPT Agent service for analyzing scraped data and recommending retail product values
    """
    
    def __init__(self):
        # Configure OpenAI (fallback)
        openai.api_key = settings.OPENAI_API_KEY
        
        # Configure AvalAI.ir
        self.avalai_api_key = settings.AVALAI_API_KEY
        self.avalai_api_key_4o = settings.AVALAI_API_KEY_4O
        self.avalai_base_url = settings.AVALAI_BASE_URL
        self.avalai_model = settings.AVALAI_MODEL
    
    # نرخ مدل‌ها (واحد: اعتبار به ازای هر 1M توکن)
    MODEL_PRICING = {
        "gpt-4o": {
            "input": 2.5,
            "input_cached": 1.25,
            "output": 10,
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "input_cached": 0.075,
            "output": 0.6,
        }
    }

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int, cached: bool = False) -> dict:
        """
        محاسبه هزینه بر اساس مدل و تعداد توکن‌ها
        """
        model_key = "gpt-4o" if model == "4o" else "gpt-4o-mini"
        pricing = self.MODEL_PRICING.get(model_key, self.MODEL_PRICING["gpt-4o-mini"])
        input_rate = pricing["input_cached"] if cached else pricing["input"]
        output_rate = pricing["output"]

        # هزینه به واحد اعتبار
        input_cost = (prompt_tokens / 1_000_000) * input_rate
        output_cost = (completion_tokens / 1_000_000) * output_rate
        total_cost = input_cost + output_cost

        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "currency": "credit"
        }

    def _build_analysis_prompt(self, html_content: str, client_recommendation: str, actions: Dict[str, Any]) -> str:
        """
        Build the prompt for GPT analysis
        """
        prompt = f"""
شما یک کارشناس خبره استخراج اطلاعات محصولات خرده‌فروشی از صفحات HTML هستید.

هدف: فقط و فقط اطلاعات محصول اصلی مورد نظر کاربر را از HTML استخراج کن. اگر محصولات دیگری هم در صفحه بودند، آن‌ها را نادیده بگیر و فقط محصول هدف را بر اساس توضیحات و اکشن‌های کاربر پیدا کن.

راهنما:
- در بخش "CLIENT RECOMMENDATION"، ابتدا نام محصول آمده و سپس کاربر توضیح داده که چگونه محصول مطلوب را در صفحه پیدا کرده (مثلاً روی چه گزینه‌هایی کلیک کرده یا چه ویژگی‌هایی را انتخاب کرده است).
- در بخش "USER ACTIONS"، لیستی از اکشن‌های کاربر (شامل تگ و آی‌دی) آمده که به یافتن محصول هدف کمک می‌کند.

دقت کن:
- فقط اطلاعات محصول هدف را استخراج کن، حتی اگر محصولات دیگری هم در HTML وجود داشتند.
- اگر مطمئن نبودی، مقدار را null قرار بده.
- هیچ متن اضافی یا توضیحی خارج از JSON بازنگردان.

**قیمت‌گذاری و تبدیل واحد:**
- قیمت‌ها باید همیشه به ریال بازگردانده شوند.
- اگر قیمت در HTML به تومان ذکر شده (مثلاً "۵۰,۰۰۰ تومان" یا "50,000 تومان")، آن را در ۱۰ ضرب کن تا به ریال تبدیل شود.
- اگر قیمت به ریال ذکر شده، همان مقدار را استفاده کن.
- برای تشخیص واحد قیمت، به کلمات "تومان"، "ریال"، "تومن" یا "تومان" در متن دقت کن.
- اگر واحد مشخص نشده بود، بر اساس اندازه عدد و الگوی سایت تصمیم بگیر (اعداد کوچک‌تر معمولاً تومان هستند).

HTML صفحه:
{html_content}

توضیحات کاربر و نام محصول (CLIENT RECOMMENDATION):
{client_recommendation}

اکشن‌های کاربر (USER ACTIONS):
{json.dumps(actions, indent=2) if actions else "No actions recorded"}

خروجی فقط باید یک JSON با این فیلدها باشد (اگر داده‌ای نبود مقدار را null قرار بده):
- description: توضیحات محصول (متن ۳ تا ۴ خطی)
- summary:  خلاصه کوتاه (۱تا ۵ گذاره ۱ تا ۴ کلمه ای که با , از هم جدا شده اند) از یوزر اکشن ها استفاده کن که دقیقتر باشی
- price: قیمت به ریال (عدد اعشاری) - حتماً به ریال تبدیل کن
- discount: مقدار تخفیف به ریال (عدد اعشاری، پیش‌فرض ۰) - حتماً به ریال تبدیل کن
- preparation: زمان آماده‌سازی به روز (عدد صحیح)
- count_type: نوع واحد (۰=تعدادی، ۱=کیلوگرم، ۲=گرم، ۳=متر، ۴=سانتی‌متر، ۵=شکل)
- weight: وزن به گرم (عدد صحیح)
- weight_with_packaging: وزن با بسته‌بندی به گرم (عدد صحیح)
- payk_delivery: ۰=فعال، ۱=غیرفعال
- post_delivery: ۰=فعال، ۱=غیرفعال
- coverage_area: ۰=سراسر کشور، ۱=فقط شهر مبدا
- image_1: آدرس تصویر اصلی (رشته)
- image_2: آدرس تصویر دوم (رشته)
- image_3: آدرس تصویر سوم (رشته)

فقط و فقط همین JSON را بازگردان.
"""
        
        return prompt
    
    async def analyze_scraped_data(
        self,
        html_content: str,
        client_recommendation: str,
        actions: Dict[str, Any],
        avalai_model: str = "4o-mini"
    ) -> Tuple[RetailProductRecommendation, Dict[str, Any], str, dict]:
        """
        Analyze scraped data and recommend retail product values using GPT
        Returns tuple of (recommendation, token_usage, raw_response, cost)
        """
        try:
            logger.info(f"[analyze_scraped_data] Starting analysis")
            
            # Build the analysis prompt
            prompt = self._build_analysis_prompt(html_content, client_recommendation, actions)
            
            # Call GPT API
            response, token_usage = await self._call_gpt_api(prompt, avalai_model=avalai_model)
            
            # Parse the response
            recommendation = self._parse_gpt_response(response)
            
            # محاسبه هزینه
            cost = self._calculate_cost(
                model=avalai_model,
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                cached=False  # اگر caching فعال شد این را True کنید
            )
            
            logger.info(f"[analyze_scraped_data] Analysis completed")
            
            return recommendation, token_usage, response, cost
            
        except Exception as e:
            logger.error(f"[analyze_scraped_data] Error analyzing scraped data: {str(e)}", exc_info=True)
            raise
    
    async def _call_gpt_api(self, prompt: str, avalai_model: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call GPT API with the given prompt (supports both OpenAI and AvalAI.ir)
        Returns tuple of (response_content, token_usage)
        """
        try:
            # Try AvalAI.ir first if configured
            if self.avalai_api_key:
                logger.info(f"[_call_gpt_api] Calling AvalAI.ir API with model: {avalai_model}")
                return await self._call_avalai_api(prompt, avalai_model)
            
            # Fallback to OpenAI
            logger.info(f"[_call_gpt_api] Calling OpenAI API")
            return await self._call_openai_api(prompt)
            
        except Exception as e:
            logger.error(f"[_call_gpt_api] Error calling GPT API: {str(e)}", exc_info=True)
            raise
    
    async def _call_avalai_api(self, prompt: str, avalai_model: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call AvalAI.ir API with the given prompt
        Returns tuple of (response_content, token_usage)
        """
        try:
            logger.info(f"[_call_avalai_api] Calling AvalAI.ir API with model: {avalai_model}")

            # Map short model names to AvalAI's expected model names
            avalai_model_map = {
                "4o": "gpt-4o",
                "4o-mini": "gpt-4o-mini"
            }
            avalai_model_name = avalai_model_map.get(avalai_model, avalai_model)

            # Choose the appropriate API key based on model
            api_key = self.avalai_api_key_4o if avalai_model == "4o" else self.avalai_api_key
            
            if not api_key:
                raise ValueError(f"No API key available for model {avalai_model}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.avalai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": avalai_model_name,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert retail product analyst. Extract product information from HTML content and client recommendations. Return only valid JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3
                    },
                    timeout=60.0
                )
                
                response.raise_for_status()
                data = response.json()
                
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                usage = data.get('usage', {})
                
                token_usage = {
                    "prompt_tokens": usage.get('prompt_tokens', 0),
                    "completion_tokens": usage.get('completion_tokens', 0),
                    "total_tokens": usage.get('total_tokens', 0),
                    "model": avalai_model_name,
                    "provider": "avalai"
                }
                
                logger.info(f"[_call_avalai_api] AvalAI.ir response received: {len(content)} characters, tokens: {token_usage['total_tokens']}")
                
                return content, token_usage
                
        except Exception as e:
            logger.error(f"[_call_avalai_api] Error calling AvalAI.ir API: {str(e)}", exc_info=True)
            raise
    
    async def _call_openai_api(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call OpenAI API with the given prompt
        Returns tuple of (response_content, token_usage)
        """
        try:
            logger.info(f"[_call_openai_api] Calling OpenAI API")
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert retail product analyst. Extract product information from HTML content and client recommendations. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3
            )
            
            # Handle response as dictionary
            if isinstance(response, dict):
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                usage = response.get('usage', {})
            else:
                # Fallback for different response types
                content = str(response)
                usage = {}
            
            token_usage = {
                "prompt_tokens": usage.get('prompt_tokens', 0),
                "completion_tokens": usage.get('completion_tokens', 0),
                "total_tokens": usage.get('total_tokens', 0),
                "model": "gpt-4",
                "provider": "openai"
            }
            
            logger.info(f"[_call_openai_api] OpenAI response received: {len(content)} characters, tokens: {token_usage['total_tokens']}")
            
            return content, token_usage
            
        except Exception as e:
            logger.error(f"[_call_openai_api] Error calling OpenAI API: {str(e)}", exc_info=True)
            raise
    
    def _parse_gpt_response(self, response: str) -> RetailProductRecommendation:
        """
        Parse GPT response and convert to RetailProductRecommendation
        """
        try:
            logger.info(f"[_parse_gpt_response] Parsing GPT response")
            
            # Extract JSON from response (handle potential markdown formatting)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in GPT response")
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            # Convert to RetailProductRecommendation
            recommendation = RetailProductRecommendation(
                description=data.get('description'),
                summary=data.get('summary'),
                price=Decimal(str(data['price'])) if data.get('price') else None,
                discount=Decimal(str(data['discount'])) if data.get('discount') else None,
                preparation=data.get('preparation'),
                count_type=data.get('count_type'),
                weight=data.get('weight'),
                weight_with_packaging=data.get('weight_with_packaging'),
                payk_delivery=data.get('payk_delivery'),
                post_delivery=data.get('post_delivery'),
                coverage_area=data.get('coverage_area'),
                image_1=data.get('image_1'),
                image_2=data.get('image_2'),
                image_3=data.get('image_3')
            )
            
            logger.info(f"[_parse_gpt_response] Successfully parsed recommendation")
            return recommendation
            
        except Exception as e:
            logger.error(f"[_parse_gpt_response] Error parsing GPT response: {str(e)}", exc_info=True)
            raise

 