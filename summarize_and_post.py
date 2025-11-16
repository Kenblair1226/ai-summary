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
from urllib.parse import urlparse
import mimetypes

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

# Static thumbnail URLs uploaded to Ghost
STATIC_THUMBNAIL_URLS = {
    # Format: "channel_handle": "https://ghost.neorex.xyz/content/images/uploaded_image.jpg"
    # Add entries here after uploading images to Ghost
    "sharptechpodcast": "https://ghost.neorex.xyz/content/images/2025/09/sharptechpodcast.png",
    "stratechery": "https://ghost.neorex.xyz/content/images/2025/09/stratechery-1.svg",
}

def extract_channel_handle(channel_url):
    if '@' in channel_url:
        return channel_url.split('/')[-1]
    return channel_url

def upload_media_to_wordpress(image_url, wp_host, auth):
    """Upload media to WordPress and return media ID"""
    try:
        # Download the image
        response = requests.get(image_url, stream=True)
        if response.status_code != 200:
            print(f"Failed to download image from {image_url}")
            return None
        
        # Extract filename from URL or use default
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path) or "thumbnail.jpg"
        
        # Prepare for upload
        url = f"{wp_host}/wp-json/wp/v2/media"
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": response.headers.get('content-type', 'image/jpeg')
        }
        
        # Upload to WordPress
        upload_response = requests.post(url, headers=headers, data=response.content)
        if upload_response.status_code == 201:
            return upload_response.json()['id']
        else:
            print(f"Failed to upload media: {upload_response.status_code} - {upload_response.text}")
            return None
            
    except Exception as e:
        print(f"Error uploading media to WordPress: {str(e)}")
        return None

def upload_image_to_ghost(image_path):
    """Upload a local image file to Ghost and return the URL"""
    try:
        ghost_url = os.getenv('ghost_url', 'https://ghost.neorex.xyz').rstrip('/')
        token = get_ghost_token()
        
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return None
            
        # Determine content type
        content_type, _ = mimetypes.guess_type(image_path)
        if not content_type or not content_type.startswith('image/'):
            print(f"Invalid image file: {image_path}")
            return None
            
        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        # Extract filename
        filename = os.path.basename(image_path)
        
        # Prepare multipart form data
        files = {
            'file': (filename, image_data, content_type)
        }
        
        headers = {
            'Authorization': f'Ghost {token}',
            'Accept-Version': 'v5.0'
        }
        
        # Upload to Ghost
        upload_url = f"{ghost_url}/ghost/api/admin/images/upload/"
        response = requests.post(upload_url, headers=headers, files=files)
        
        if response.status_code == 201:
            result = response.json()
            if 'images' in result and len(result['images']) > 0:
                uploaded_url = result['images'][0]['url']
                print(f"Successfully uploaded {filename} to Ghost: {uploaded_url}")
                return uploaded_url
            else:
                print(f"Unexpected response format: {result}")
                return None
        else:
            print(f"Failed to upload image to Ghost: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error uploading image to Ghost: {str(e)}")
        return None

def upload_static_thumbnails():
    """Upload all images from public folder to Ghost and update STATIC_THUMBNAIL_URLS"""
    public_dir = "public"
    if not os.path.exists(public_dir):
        print(f"Public directory not found: {public_dir}")
        return
        
    uploaded_urls = {}
    
    # Find all image files in public directory
    for filename in os.listdir(public_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            image_path = os.path.join(public_dir, filename)
            
            # Extract channel handle from filename (remove extension)
            channel_handle = os.path.splitext(filename)[0]
            
            print(f"Uploading {filename} for channel: {channel_handle}")
            uploaded_url = upload_image_to_ghost(image_path)
            
            if uploaded_url:
                uploaded_urls[channel_handle] = uploaded_url
                
    # Print the results for manual addition to STATIC_THUMBNAIL_URLS
    if uploaded_urls:
        print("\n" + "="*50)
        print("UPLOAD RESULTS - Add these to STATIC_THUMBNAIL_URLS:")
        print("="*50)
        for channel, url in uploaded_urls.items():
            print(f'    "{channel}": "{url}",')
        print("="*50)
    else:
        print("No images were uploaded successfully.")
        
    return uploaded_urls

def upload_svg_to_ghost_if_needed(thumbnail_path):
    """Upload SVG file to Ghost dynamically if it's a local SVG file"""
    if not thumbnail_path or not thumbnail_path.startswith('public/') or not thumbnail_path.lower().endswith('.svg'):
        return thumbnail_path
    
    try:
        print(f"Uploading SVG to Ghost: {thumbnail_path}")
        ghost_url = upload_image_to_ghost(thumbnail_path)
        if ghost_url:
            print(f"Successfully uploaded SVG to Ghost: {ghost_url}")
            
            # Extract channel name for future reference
            filename = os.path.basename(thumbnail_path)
            channel_name = os.path.splitext(filename)[0].lower()
            print(f"Suggestion: Add this to STATIC_THUMBNAIL_URLS for future use:")
            print(f'    "{channel_name}": "{ghost_url}",')
            
            return ghost_url
        else:
            print(f"Failed to upload SVG, using local path: {thumbnail_path}")
            return thumbnail_path
            
    except Exception as e:
        print(f"Error uploading SVG to Ghost: {str(e)}")
        return thumbnail_path

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

    # Get thumbnail URL
    thumbnail_url = get_thumbnail_url(video_url, post_url, channel_url)

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
    
    # Add featured media if thumbnail is available
    if thumbnail_url and thumbnail_url.startswith('http'):
        # For external URLs (YouTube thumbnails), we need to upload to WordPress first
        media_id = upload_media_to_wordpress(thumbnail_url, wp_host, auth)
        if media_id:
            data["featured_media"] = media_id
    
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

def get_youtube_thumbnail(video_url):
    """Get YouTube thumbnail URL from video URL"""
    video_id = extract_youtube_id(video_url)
    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    return None

def get_static_thumbnail(channel_url):
    """Get static thumbnail URL from uploaded Ghost URLs or local files"""
    try:
        channel_handle = extract_channel_handle(channel_url)
        if channel_handle:
            # Remove @ symbol if present
            clean_handle = channel_handle.replace('@', '')
            
            # First check if we have an uploaded Ghost URL
            if clean_handle in STATIC_THUMBNAIL_URLS:
                return STATIC_THUMBNAIL_URLS[clean_handle]
            
            # Check for SVG files (case-insensitive)
            for filename in os.listdir("public") if os.path.exists("public") else []:
                name_without_ext = os.path.splitext(filename)[0].lower()
                if name_without_ext == clean_handle.lower() and filename.lower().endswith('.svg'):
                    return f"public/{filename}"
            
            # Fallback to local files (for backward compatibility)
            thumbnail_path = f"public/{clean_handle}.jpg"
            if os.path.exists(thumbnail_path):
                return thumbnail_path
                
            # Try with png extension
            thumbnail_path = f"public/{clean_handle}.png"
            if os.path.exists(thumbnail_path):
                return thumbnail_path
                
    except Exception as e:
        print(f"Error getting static thumbnail: {str(e)}")
    
    return None

def get_thumbnail_url(video_url=None, post_url=None, channel_url=None):
    """Get appropriate thumbnail URL based on content type"""
    # For YouTube videos, get YouTube thumbnail
    if video_url:
        return get_youtube_thumbnail(video_url)
    
    # For podcast/RSS feeds, try to get static image
    if channel_url:
        return get_static_thumbnail(channel_url)
    
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
    
    # Combine tags: always include 'summary' tag, channel tag if exists
    tags = [{'name': 'summary'}] + channel_tag

    # Remove HTML tags from the title
    clean_title = remove_html_tags(title)
    human_content = humanize_content(content)
    
    # Get thumbnail URL
    thumbnail_url = get_thumbnail_url(video_url, post_url, channel_url)
    
    # For local SVG files, upload them to Ghost dynamically
    if thumbnail_url and thumbnail_url.startswith('public/') and thumbnail_url.lower().endswith('.svg'):
        thumbnail_url = upload_svg_to_ghost_if_needed(thumbnail_url)
    
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
    post_data = {
        'title': clean_title,
        'lexical': json.dumps(lexical_content),
        'status': 'draft',
        'tags': tags,
        'visibility': 'public',
        'featured': False,
        'slug': generate_slug(clean_title)
    }
    
    # Add featured image if thumbnail is available
    if thumbnail_url:
        if thumbnail_url.startswith('http'):
            # For external URLs (YouTube thumbnails or Ghost URLs), use directly
            post_data['feature_image'] = thumbnail_url
        else:
            # For local files, we'd need to upload to Ghost first
            print(f"Local thumbnail found but not uploaded to Ghost: {thumbnail_url}")
            print("Use upload_static_thumbnails() to upload local images to Ghost")
    
    data = {"posts": [post_data]}
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
    
def upload_and_update_urls():
    """Helper function to upload images and generate code to update STATIC_THUMBNAIL_URLS"""
    print("Uploading all images from public/ folder to Ghost...")
    uploaded_urls = upload_static_thumbnails()
    
    if uploaded_urls:
        print("\n" + "="*60)
        print("COPY AND PASTE THE FOLLOWING INTO STATIC_THUMBNAIL_URLS:")
        print("="*60)
        for channel, url in uploaded_urls.items():
            print(f'    "{channel}": "{url}",')
        print("="*60)
        print("After updating STATIC_THUMBNAIL_URLS, your posts will use these Ghost URLs for thumbnails!")
    
    return uploaded_urls

if __name__ == "__main__":
    # Uncomment the line below to upload all images from public/ folder to Ghost
    # upload_and_update_urls()
    
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
