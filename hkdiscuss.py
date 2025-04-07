import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import os
import hashlib
from pathlib import Path

def get_thread_description(thread_url):
    """Fetch additional details from thread page for description"""
    try:
        response = requests.get(thread_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract first post content
            if post := soup.find('div', class_='t_msgfont'):
                # Get the text and images
                description_parts = []

                # Add text content
                description_parts.append(str(post))  # Converting the entire post to HTML

                # Add images
                for img in post.find_all('img'):
                    img_src = img['src']  # Get the image source
                    description_parts.append(f'<img src="{img_src}" alt="" style="max-width:100%; height:auto;"/>')

                return '<br>'.join(description_parts) + "..."  # Join parts with line breaks
    except Exception as e:
        print(f"Couldn't fetch description from {thread_url}: {e}")
    return None

def get_existing_entries(atom_file):
    """Get existing entries from either gh-pages branch or local file"""
    existing_titles = set()
    
    # Check both possible locations (gh-pages branch and local file)
    possible_paths = [
        Path("gh-pages-deploy") / atom_file,  # From fetched gh-pages branch
        Path(atom_file)                       # Local file (if exists)
    ]
    
    for file_path in possible_paths:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'xml')
                    for entry in soup.find_all('entry'):
                        if entry.title and entry.title.text:
                            normalized_title = entry.title.text.strip().lower()
                            existing_titles.add(normalized_title)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
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


def fetch_feed(url, base_url, atom_file, title, subtitle, item_selector, link_selector):
    fg = FeedGenerator()
    fg.id(url)
    fg.title(title)
    fg.link(href=url)
    fg.subtitle(subtitle)
    fg.updated(datetime.now(timezone.utc))

    existing_titles = get_existing_entries(atom_file)
    new_entries = 0

    response = requests.get(url)
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
    url='https://www.discuss.com.hk/forumdisplay.php?fid=57&orderby=dateline&ascdesc=DESC&filter=0',
    base_url='https://www.discuss.com.hk/',
    atom_file='hkdiscuss_money.xml',
    title='HKDiscuss money',
    subtitle='Latest articles',
    item_selector='tbody.forumdisplay_thread',
    link_selector='span.tsubject a'
)

fetch_feed(
    url='https://www.discuss.com.hk/forumdisplay.php?fid=110&orderby=dateline&ascdesc=DESC&filter=0',
    base_url='https://www.discuss.com.hk/',
    atom_file='hkdiscuss_house.xml',
    title='HKDiscuss house',
    subtitle='Latest articles',
    item_selector='tbody.forumdisplay_thread',
    link_selector='span.tsubject a'
)

fetch_feed(
    url='https://www.discuss.com.hk/hottopics.php', 
    base_url='https://www.discuss.com.hk/',
    atom_file='hkdiscuss_hottopics.xml',
    title='HKDiscuss Hot Topics',
    subtitle='Latest hot topics',
    item_selector='div.section.hslice ul li:not([style*="text-align:right"])',
    link_selector='a'
)
