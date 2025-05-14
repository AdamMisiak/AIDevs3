import re
import html

def find_flag_in_text(text: str) -> str:
    flag_patterns = [
        r'FLG:[A-Z0-9_]+',                 # Standard format: FLG:ABC123
        r'FLG:[ \n\r\t]*[A-Z0-9_]+',       # With possible whitespace: FLG: ABC123 or split across lines
        r'F[ \n\r\t]*L[ \n\r\t]*G[ \n\r\t]*:[ \n\r\t]*[A-Z0-9_]+',  # Spaced out: F L G : ABC123
        r'[Ff][Ll][Gg][ \n\r\t]*:[ \n\r\t]*[A-Z0-9_]+'  # Case insensitive: flg: ABC123
    ]
    
    for pattern in flag_patterns:
        flag_match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        print(f'🔍 [*] Trying pattern: {pattern}')
        if flag_match:
            flag = flag_match.group(0)
            flag = re.sub(r'[\n\r\t ]+', '', flag)
            print(f'✅ [+] Match found: {flag}')
            return flag
    
    raise Exception("No flag found in the response")

def prepare_text_for_search(text: str) -> str:
    if not text:
        return ""
        
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    try:
        text = html.unescape(text)
    except Exception as e:
        print(f"⚠️ HTML unescape error: {e}")
    
    text = re.sub(r'[\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]', ' ', text)
    
    lines = text.split('\n')
    for i in range(len(lines) - 1):
        if (re.search(r'https?:/?/?$|FLG:?$|FLAG:?$', lines[i], re.IGNORECASE) and 
            re.search(r'^/?[A-Za-z0-9_.~:/?#[\]@!$&\'()*+,;=]+', lines[i+1])):
            lines[i] = lines[i] + lines[i+1]
            lines[i+1] = ''
    
    text = '\n'.join(lines)
    
    return text
