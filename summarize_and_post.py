import os
from dotenv import load_dotenv
import requests
from base64 import b64encode
from genai_helper import article_mp3, generate_slug
from youtube_helper import download_audio_from_youtube
import uuid
import shutil

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
    "NVIDIA"            : 27,
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
        content = f"{content}\n\n<p>原始連結：<a>{post_url}</a></p>"

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

if __name__ == "__main__":
    video_url = "https://youtu.be/H6j8LfgQl9k"
    path = f"{uuid.uuid4()}"
    title, new_file = download_audio_from_youtube(video_url, path)
    # path = "213527c8-db02-46e6-8a3c-2ad4b66bd95a"
    # title = "Anduril's Effort to Modernize US Defense Software | Sharp Tech with Ben Thompson"
    new_file = f"{path}/{title}.mp3"
    post_title, article = article_mp3(title, new_file)
    response = post_to_wordpress(post_title, article, video_url, None, "https://youtube.com/@sharptechpodcast")
    if response:
        print(f"Summary posted to WordPress successfully. Post URL: {response}")
    else:
        print("Failed to post summary to WordPress.")
    
    # shutil.rmtree(path)