import os
from dotenv import load_dotenv
import requests
from base64 import b64encode
import jwt
import datetime
from genai_helper import article_mp3, generate_slug, humanize_content, find_relevant_tags_with_llm
from youtube_helper import download_audio_from_youtube
import uuid
import shutil
import json
import re

load_dotenv()

CATEGORY_IDS = {
    "stratechery"       : 19,
    "@sharptechpodcast" : 18,
    "allin"             : 16,
    "@technologyreview" : 17,
    "Techcrunch"        : 20,
    "duran"             : 23,
    "sharptech"         : 18,
    "anotherpodcast"    : 25,
    "joerogan"          : 26,
    "nvidia"            : 27,
    "acq"               : 28,
    "a16z"              : 30,
}

def extract_channel_handle(channel_url):
    if '@' in channel_url:
        return channel_url.split('/')[-1]
    return channel_url

def post_to_wordpress(title, content, video_url, post_url, channel_url):
    wp_host = os.getenv('wp_host')
    wp_user = os.getenv('wp_user')
    wp_pass = os.getenv('wp_pass')
    
    url = f"{wp_host}/wp-json/wp/v2/posts"
    auth = b64encode(f"{wp_user}:{wp_pass}".encode()).decode("utf-8")
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    if video_url is not None:
        # attach video url to the content
        content = f"""
        <!-- wp:embed {{\"url\":\"{video_url}\",\"type\":\"video\",\"providerNameSlug\":\"youtube\",\"responsive\":true,\"className\":\"wp-embed-aspect-16-9 wp-has-aspect-ratio\"}} -->\n<figure class=\"wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio\"><div class=\"wp-block-embed__wrapper\">\n{video_url}\n</div></figure>\n<!-- /wp:embed -->\n\n

        {content}
        \n\n
        <p>原始影片：<a>{video_url}</a></p> \n
        
        """
    else: # attach post url to the content
        content = f'{content}\n\n<p>原始連結：<a href="{post_url}">{post_url}</a></p>'

    channel_handle = extract_channel_handle(channel_url)
    category_ids = [CATEGORY_IDS[channel_handle]] if channel_handle in CATEGORY_IDS else []

    data = {
        "title": title,
        "content": content,
        "status": "publish",
        "categories": category_ids,
        "tags": [22], # 22:summary
        "slug": generate_slug(title)
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return response.json()['link']
    return None

def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtu\.be/|youtube\.com/embed/|youtube\.com/watch\?v=)([^&?/]+)',
        r'(?:youtube\.com/shorts/)([^&?/]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def create_lexical_content(content_html, video_url=None, post_url=None):
    nodes = []
    
    if video_url:
        video_id = extract_youtube_id(video_url)
        if video_id:
            nodes.extend([
                {
                    "type": "paragraph",
                    "version": 1,
                    "children": [{"type": "text", "text": ""}]
                },
                {
                    "type": "embed",
                    "version": 1,
                    "embedType": "video",
                    "url": f"https://www.youtube.com/embed/{video_id}",
                    "html": f"<iframe width=\"200\" height=\"113\" src=\"https://www.youtube.com/embed/{video_id}?feature=oembed\" frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" allowfullscreen></iframe>",
                    "caption": "",
                    "width": 200,
                    "height": 113
                }
            ])

    # Add main content as a single markdown block
    nodes.append({
        "type": "paragraph",
        "version": 1,
        "children": [{
            "type": "text",
            "format": "",
            "text": content_html
        }]
    })
    
    # Add source link
    if video_url or post_url:
        source_text = "原始影片：" if video_url else "原始連結："
        source_url = video_url if video_url else post_url
        nodes.append({
            "type": "paragraph",
            "version": 1,
            "children": [
                {"type": "text", "text": source_text},
                {
                    "type": "link",
                    "version": 1,
                    "url": source_url,
                    "rel": None,
                    "target": None,
                    "children": [{"type": "text", "text": source_url}]
                }
            ]
        })
    
    return {
        "root": {
            "type": "root",
            "format": "",
            "indent": 0,
            "version": 1,
            "children": nodes
        }
    }

def remove_html_tags(text):
    """
    Remove HTML tags from a string using regex.
    
    Args:
        text (str): String containing HTML tags
        
    Returns:
        str: Clean text without HTML tags
    """
    # Pattern matches any HTML tag including attributes
    pattern = re.compile('<[^>]+>')
    # Replace all HTML tags with empty string
    clean_text = pattern.sub('', text)
    # Remove extra whitespace
    clean_text = ' '.join(clean_text.split())
    return clean_text

def get_ghost_token():
    """Generate a Ghost Admin API token"""
    ghost_key = os.getenv('ghost_key')
    [id, secret] = ghost_key.split(':')
    
    iat = int(datetime.datetime.now().timestamp())
    header = {'alg': 'HS256', 'typ': 'JWT', 'kid': id}
    payload = {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/admin/'}
    
    return jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

def get_ghost_tags():
    """Fetch all tags from Ghost"""
    ghost_url = os.getenv('ghost_url', 'https://ghost.neorex.xyz').rstrip('/')
    token = get_ghost_token()
    
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{ghost_url}/ghost/api/admin/tags/?limit=all",
            headers=headers
        )
        if response.status_code == 200:
            return response.json().get('tags', [])
        else:
            print(f"Failed to fetch tags: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching tags: {str(e)}")
        return []

def find_relevant_tags(title, content, available_tags):
    """Find relevant tags based on content and title"""
    # Remove HTML tags and convert to lowercase for better matching
    clean_title = remove_html_tags(title).lower()
    clean_content = remove_html_tags(content).lower()
    combined_text = f"{clean_title} {clean_content}"
    
    relevant_tags = []
    
    # Exclude 'summary' tag from matching as it's added by default
    content_tags = [tag for tag in available_tags if tag['name'].lower() != 'summary']
    
    for tag in content_tags:
        tag_name = tag['name'].lower()
        # Check if tag name appears in title or content
        # Add more sophisticated matching logic here if needed
        if tag_name in combined_text:
            relevant_tags.append({'name': tag['name']})
    
    return relevant_tags

def post_to_ghost(title, content, video_url, post_url, channel_url):
    ghost_url = os.getenv('ghost_url', 'https://ghost.neorex.xyz').rstrip('/')
    token = get_ghost_token()
    
    # Get channel handle for channel tag
    channel_handle = extract_channel_handle(channel_url)
    channel_tag = [{'name': channel_handle}] if channel_handle else []
    
    # Get available tags and find relevant ones using LLM
    available_tags = get_ghost_tags()
    content_tags = find_relevant_tags_with_llm(title, content, available_tags)
    
    # Combine tags: always include 'summary' tag, channel tag if exists, and any relevant content tags
    tags = [{'name': 'summary'}] + channel_tag + content_tags

    # Remove HTML tags from the title
    clean_title = remove_html_tags(title)
    human_content = humanize_content(content)
    
    # Prepare the content with video embed if needed
    if video_url:
        video_id = extract_youtube_id(video_url)
        if video_id:
            iframe = f'<!--kg-card-begin: html--><iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe><!--kg-card-end: html-->'
            content = f"{iframe}<br/><br/>{human_content}"
    
    # Add source link
    source_text = "原始影片：" if video_url else "原始連結："
    source_url = video_url if video_url else post_url
    if source_url:
        content = f"{content}<br/><br/>{source_text}<a href='{source_url}'>{source_url}</a>"

    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }
    
    lexical_content = create_lexical_content(human_content, video_url, post_url)
    data = {
        "posts": [{
            'title': clean_title,
            'lexical': json.dumps(lexical_content),
            'status': 'draft',
            'tags': tags,
            'visibility': 'public',
            'featured': False,
            'slug': generate_slug(clean_title)
        }]
    }
    print(f"data: {data}")
    try:
        response = requests.post(
            f"{ghost_url}/ghost/api/admin/posts/", 
            json=data,
            headers=headers
        )
        if response.status_code == 201:
            return response.json()['posts'][0]['url']
        else:
            print(f"Ghost API error: {response.status_code} - {response.text}")
            print(f"Response content: {response.text}")
            return None
    except Exception as e:
        print(f"Failed to post to Ghost: {str(e)}")
        return None

def get_ghost_posts():
    ghost_url = os.getenv('ghost_url', 'https://ghost.neorex.xyz').rstrip('/')
    token = get_ghost_token()

    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            f"{ghost_url}/ghost/api/admin/posts/67a5992c36e1b300012a1f4a",
            headers=headers
        )

        print(f"Response content: {response.text}")
        return None
    except Exception as e:
        print(f"Failed to post to Ghost: {str(e)}")
        return None
    
if __name__ == "__main__":
    video_url = "https://youtu.be/H6j8LfgQl9k"
    # path = f"{uuid.uuid4()}"
    # title, new_file = download_audio_from_youtube(video_url, path)
    # new_file = f"{path}/{title}.mp3"
    # post_title, article = article_mp3(title, new_file)
    
    # # Post to WordPress
    # wp_response = post_to_wordpress(post_title, article, video_url, None, "https://youtube.com/@sharptechpodcast")
    # if wp_response:
    #     print(f"Summary posted to WordPress successfully. Post URL: {wp_response}")
    # else:
    #     print("Failed to post summary to WordPress.")
    
    # Post to Ghost
    ghost_response = post_to_ghost("<p>test</p>", "<p>test title</p>  \n test content", video_url, None, "https://youtube.com/@sharptechpodcast")
    if ghost_response:
        print(f"Summary posted to Ghost successfully. Post URL: {ghost_response}")
    else:
        print("Failed to post summary to Ghost.")
    
    # get_ghost_posts()

    # shutil.rmtree(path)
