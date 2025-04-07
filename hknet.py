import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import os
import hashlib

def get_thread_description(thread_url):
    """Fetch additional details from thread page for description"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(thread_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find('div', class_='article-detail-content-container')
            if container:
                posts = container.find_all('p')
            else:
                posts = soup.select('div.article-detail-content-container > p')

            if posts:
                description_parts = []
                for post in posts:
                    text = post.get_text(' ', strip=True)
                    if text:  # Only add if there's actual text
                        description_parts.append(text[:5000])  # Limit length

                # Handle images
                images = container.select('img')
                for img in images:
                    img_src = img.get('data-src', img.get('src', ''))
                    if img_src:
                        description_parts.append(f'<img src="{img_src}" alt="" style="max-width:100%; height:auto;"/>')

                return '<br>'.join(description_parts) + "..." if description_parts else None
    except Exception as e:
        print(f"Couldn't fetch description from {thread_url}: {e}")
    return None

def get_existing_entries(atom_file):
    """Get existing entries using only titles as markers"""
    existing_titles = set()
    if os.path.exists(atom_file):
        try:
            with open(atom_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'xml')
                for entry in soup.find_all('entry'):
                    if entry.title and entry.title.text:
                        # Normalize the title by stripping whitespace and lowercasing
                        normalized_title = entry.title.text.strip().lower()
                        existing_titles.add(normalized_title)
        except Exception as e:
            print(f"Error reading existing feed: {e}")
    return existing_titles


def parse_time(time_element):
    """Parse time element with timezone"""
    try:
        if time_element and time_element.has_attr('title'):
            dt = datetime.strptime(time_element['title'], '%Y-%m-%d %H:%M')
            return dt.replace(tzinfo=timezone(timedelta(hours=8)))  # HK Timezone
    except Exception as e:
        print(f"Time parsing error: {e}")
    return datetime.now(timezone.utc)


def fetch_feed(url, base_url, atom_file, title, subtitle, item_selector, link_selector, use_headers=True):

    fg = FeedGenerator()
    fg.id(url)
    fg.title(title)
    fg.link(href=url)
    fg.subtitle(subtitle)
    fg.updated(datetime.now(timezone.utc))

    existing_titles = get_existing_entries(atom_file)
    new_entries = 0


    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' 
    }

    if use_headers:
        response = requests.get(url, headers=headers)
    else:
        response = requests.get(url)  # No headers

    if response.status_code != 200:
        print(f"Failed to retrieve {url}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    for thread in soup.select(item_selector):

        title_tag = thread.select_one(link_selector)
        if not title_tag:
            continue

        entry_title = title_tag.get_text(strip=True)
        if not entry_title:
            print("Skipping entry with empty title.")
            continue
        
        thread_url = urljoin(url, title_tag['href'])
        pub_date = parse_time(thread.select_one('td.lastpost em span'))

        normalized_title = entry_title.strip().lower()

        if normalized_title in existing_titles:
            continue

        description = ''
        if thread_desc := get_thread_description(thread_url):
            description += f"\n\n{thread_desc}"

        # Create feed entry
        entry = fg.add_entry()
        entry.id(thread_url)
        entry.title(entry_title)
        entry.link(href=thread_url)
        entry.published(pub_date)
        entry.updated(pub_date)
        entry.content(description, type='html')

        # Add author info
        if author := thread.select_one('td.author cite a'):
            entry.author({'name': author.get_text(strip=True)})

        # Check if any required field is missing
        if not entry_title or not thread_url or not pub_date:
            print("Error: Missing required fields for entry.")
            continue

        new_entries += 1
        existing_titles.add(normalized_title)

    if new_entries > 0:
        fg.atom_file(atom_file)
        print(f"Feed updated with {new_entries} new entries: {atom_file}")
    else:
        print(f"No new entries found. Feed not updated: {atom_file}")


fetch_feed(
    url='https://inews.hket.com/sran001/%E5%85%A8%E9%83%A8?mtc=20080',
    base_url='https://inews.hket.com/',
    atom_file='hknet.xml',
    title='HKET News Feed',
    subtitle='Latest news',
    item_selector='div.listing-content-container',
    link_selector='a',
    use_headers=True  # Use headers for HKET
)
