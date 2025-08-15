# modules/sub_handler.py

import pysubs2
import math

def translate_subtitle(filepath, output_path, translate_func, api_key, style, target_lang, proxy_url, update_progress):
    """Translates a subtitle file (SRT, ASS) line by line."""
    try:
        subs = pysubs2.load(filepath, encoding='utf-8')
    except Exception as e:
        # Fallback for different encodings
        subs = pysubs2.load(filepath, encoding='latin-1')

    total_lines = len(subs)
    
    for i, line in enumerate(subs):
        if line.text.strip(): # Only translate non-empty lines
            # For ASS, tags are like {\i1\c&H00FFFF&}
            # The AI prompt specifically asks to preserve these tags
            original_text = line.text
            translated_text = translate_func(api_key, original_text, style, target_lang, proxy_url)
            line.text = translated_text
        
        progress = math.ceil(((i + 1) / total_lines) * 100)
        update_progress(progress, f"Translating line {i+1}/{total_lines}...")

    subs.save(output_path)
