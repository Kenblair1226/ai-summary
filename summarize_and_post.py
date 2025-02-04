import os
from dotenv import load_dotenv
import requests
from base64 import b64encode
import jwt
import datetime
from genai_helper import article_mp3, generate_slug, humanize_content
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
        "slug": generate_slug(title, content)
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
        # Add video embed as iframe
        video_id = extract_youtube_id(video_url)
        if video_id:
            nodes.append({
                "type": "paragraph",
                "version": 1,
                "children": [{
                    "type": "text",
                    "text": ""
                }]
            })
            nodes.append({
                "type": "embed",
                "version": 1,
                "embedType": "video",
                "url": f"https://www.youtube.com/embed/{video_id}",
                "html": f"<iframe width=\"200\" height=\"113\" src=\"https://www.youtube.com/embed/{video_id}?feature=oembed\" frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" referrerpolicy=\"strict-origin-when-cross-origin\" allowfullscreen ></iframe>",
                "caption": "",
                "width": 200,
                "height": 113
            })
    
    # Split content into paragraphs and add each as a node
    paragraphs = content_html.split('\n')
    for para in paragraphs:
        if para.strip():  # Skip empty paragraphs
            nodes.append({
                "type": "paragraph",
                "version": 1,
                "children": [{
                    "type": "text",
                    "text": para.strip()
                }]
            })
    
    # Add source link
    if video_url:
        nodes.append({
            "type": "paragraph",
            "version": 1,
            "children": [
                {
                    "type": "text",
                    "text": "原始影片："
                },
                {
                    "type": "link",
                    "version": 1,
                    "url": video_url,
                    "rel": None,
                    "target": None,
                    "children": [{
                        "type": "text",
                        "text": video_url
                    }]
                }
            ]
        })
    elif post_url:
        nodes.append({
            "type": "paragraph",
            "version": 1,
            "children": [
                {
                    "type": "text",
                    "text": "原始連結："
                },
                {
                    "type": "link",
                    "version": 1,
                    "url": post_url,
                    "rel": None,
                    "target": None,
                    "children": [{
                        "type": "text",
                        "text": post_url
                    }]
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

def post_to_ghost(title, content, video_url, post_url, channel_url):
    ghost_url = os.getenv('ghost_url', 'https://ghost.neorex.xyz').rstrip('/')
    ghost_key = os.getenv('ghost_key')
    
    # Split the key into ID and SECRET
    [id, secret] = ghost_key.split(':')
    
    # Create the token
    iat = int(datetime.datetime.now().timestamp())
    
    header = {
        'alg': 'HS256',
        'typ': 'JWT',
        'kid': id
    }
    
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,
        'aud': '/admin/'
    }

    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    # Get channel handle for tags
    channel_handle = extract_channel_handle(channel_url)
    tags = [{'name': 'summary'}, {'name': channel_handle}] if channel_handle else [{'name': 'summary'}]
    
    # Remove HTML tags from the title
    clean_title = remove_html_tags(title)
    
    # Remove HTML tags from content before creating lexical content
    clean_content = humanize_content(content)
    lexical_content = create_lexical_content(clean_content, video_url, post_url)

    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    data = {
        "posts": [{
            'title': clean_title,
            'lexical': json.dumps(lexical_content),
            'status': 'published',
            'tags': tags,
            'visibility': 'public',
            'featured': False,
            'slug': generate_slug(clean_title, content)
        }]
    }
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
    ghost_key = os.getenv('ghost_key')
    
    # Split the key into ID and SECRET
    [id, secret] = ghost_key.split(':')
    
    # Create the token
    iat = int(datetime.datetime.now().timestamp())
    
    header = {
        'alg': 'HS256',
        'typ': 'JWT',
        'kid': id
    }
    
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,
        'aud': '/admin/'
    }

    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            f"{ghost_url}/ghost/api/admin/posts/",
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
    ghost_response = post_to_ghost("<p>test</p>", "test content", video_url, None, "https://youtube.com/@sharptechpodcast")
    if ghost_response:
        print(f"Summary posted to Ghost successfully. Post URL: {ghost_response}")
    else:
        print("Failed to post summary to Ghost.")
    
    # get_ghost_posts()

    # shutil.rmtree(path)