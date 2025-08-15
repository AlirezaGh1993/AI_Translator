# modules/ai_handler.py

import google.generativeai as genai
import requests
import time
import os
from langdetect import detect

# --- Configuration ---
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
RPM_LIMITS = {
    'gemini': 50,  # Example: 50 requests per minute
    'deepseek': 25 # Example: 25 requests per minute
}
TIME_PER_REQUEST = {
    'gemini': 60 / RPM_LIMITS['gemini'],
    'deepseek': 60 / RPM_LIMITS['deepseek']
}

def set_proxy(proxy_url):
    """Sets proxy for both requests and google-generativeai."""
    if proxy_url:
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        return {'http': proxy_url, 'https': proxy_url}
    else:
        # Unset proxy if not provided
        if 'http_proxy' in os.environ: del os.environ['http_proxy']
        if 'https_proxy' in os.environ: del os.environ['https_proxy']
        return None

def detect_language(text):
    """Detects the language of a given text."""
    try:
        return detect(text)
    except:
        return "en" # Default to English on failure

def get_translation_prompt(text, style, target_lang, source_lang="auto"):
    """Creates a detailed prompt for the AI."""
    if source_lang == "auto":
        detected_lang = detect_language(text[:200]) # Detect from first 200 chars
        source_lang_text = f"from the auto-detected language '{detected_lang}'"
    else:
        source_lang_text = f"from {source_lang}"

    style_instructions = {
        "Formal": "Use a formal and official tone.",
        "Colloquial": "Use a casual, conversational, and everyday tone.",
        "Literary": "Translate with a literary and artistic style, paying attention to nuances and poetic elements.",
        "Novel": "Translate in a style suitable for web novels or light novels, focusing on readability and engaging dialogue.",
        "Journalistic": "Use a clear, concise, and objective tone suitable for news articles.",
        "Technical": "Translate with high precision for technical terms and jargon. Maintain the original meaning accurately.",
        "Transcreation": "Adapt the text culturally and emotionally for the target audience, not just a literal translation. Recreate the original intent and impact."
    }

    prompt = f"""
    **Task**: Translate the following text into **{target_lang}** {source_lang_text}.
    **Style**: {style}. {style_instructions.get(style, "")}
    **Rules**:
    1.  Translate the content accurately while adhering to the specified style.
    2.  **CRITICAL**: Preserve all original formatting, including markdown, line breaks, HTML tags (like `<i>`, `<b>`), and special markers (like `{{...}}`) EXACTLY as they are. Do not add or remove them.
    3.  Provide ONLY the translated text as the output, without any extra explanations, introductory phrases, or apologies.

    **Text to Translate**:
    ---
    {text}
    ---
    """
    return prompt

def translate_gemini(api_key, text, style, target_lang, proxy_url):
    """Translates text using Google Gemini API."""
    set_proxy(proxy_url)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = get_translation_prompt(text, style, target_lang)
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = model.generate_content(prompt)
            time.sleep(TIME_PER_REQUEST['gemini']) # Rate limiting
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API Error (Attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                return f"GEMINI TRANSLATION FAILED: {text}" # Return original on failure

def translate_deepseek(api_key, text, style, target_lang, proxy_url):
    """Translates text using DeepSeek API."""
    proxies = set_proxy(proxy_url)
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    prompt = get_translation_prompt(text, style, target_lang)
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=60)
            response.raise_for_status()
            translation = response.json()['choices'][0]['message']['content']
            time.sleep(TIME_PER_REQUEST['deepseek']) # Rate limiting
            return translation.strip()
        except requests.exceptions.RequestException as e:
            print(f"DeepSeek API Error (Attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                return f"DEEPSEEK TRANSLATION FAILED: {text}" # Return original on failure

def get_translator_func(provider):
    """Returns the correct translation function based on the provider name."""
    if provider == 'gemini':
        return translate_gemini
    elif provider == 'deepseek':
        return translate_deepseek
    else:
        raise ValueError("Invalid AI provider specified.")
