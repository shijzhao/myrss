import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os

def fetch_feed(url, atom_file, title, subtitle, item_selector, link_selector, base_url=None, use_headers=True):
    existing_links = set()
    
    if os.path.exists(atom_file):
        with open(atom_file, 'r', encoding='utf-8') as f:
            existing_feed = f.read()
            existing_links = set(existing_feed.split('<id>')[1:])

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' 
    }

    if use_headers:
        response = requests.get(url, headers=headers)
    else:
        response = requests.get(url)  # No headers

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        fg = FeedGenerator()
        fg.id(url)
        fg.title(title)
        fg.link(href=url)
        fg.subtitle(subtitle)
        fg.updated()

        for article in soup.select(item_selector):
            title_element = article.select_one(link_selector)
            if title_element:
                title_text = title_element.get_text(strip=True)
                link = title_element['href']
                
                if base_url and not link.startswith('http'):
                    link = base_url + link
                    
                if link not in existing_links:
                    entry = fg.add_entry()
                    entry.id(link)
                    entry.title(title_text)
                    entry.content(title_text)
                    entry.link(href=link)

        atom_feed = fg.atom_str(pretty=True)
        with open(atom_file, 'wb') as f:
            f.write(atom_feed)
        print(f"{atom_file} created successfully!")
    else:
        print(f"Failed to retrieve {url}. Status code: {response.status_code}")

# Example usage
fetch_feed(
    url='https://inews.hket.com/sran001/%E5%85%A8%E9%83%A8?mtc=20080',
    atom_file='hket_feed.xml',
    title='HKET News Feed',
    subtitle='Latest news',
    item_selector='div.listing-content-container',
    link_selector='a',
    base_url='https://inews.hket.com/',  # Provide the base URL
    use_headers=True  # Use headers for HKET
)

fetch_feed(
    url='https://www.discuss.com.hk/forumdisplay.php?fid=110&orderby=dateline&ascdesc=DESC&filter=0',
    atom_file='hkdiscuss_feed.xml',
    title='HKDiscuss Feed',
    subtitle='Latest articles',
    item_selector='span.tsubject',
    link_selector='a',
    base_url='https://www.discuss.com.hk/',  # Provide the base URL
    use_headers=False  # No headers for HKDiscuss
)
