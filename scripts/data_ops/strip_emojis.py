
import os
import re

files = [
    'app/scraping/core/tokopedia.py', 
    'app/scraping/core/lazada.py', 
    'app/scraping/scraper_manager.py'
]

emojis = re.compile('[\U00010000-\U0010ffff]', flags=re.UNICODE)

for f_path in files:
    if os.path.exists(f_path):
        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = emojis.sub(lambda m: '*', content)
        with open(f_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Stripped emojis from {f_path}')
