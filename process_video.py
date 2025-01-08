import ssl
from pytubefix import YouTube

ssl._create_default_https_context = ssl._create_unverified_context

def process_video(video_url, language='en'):
    yt = YouTube(video_url)
    title = yt.title
    if language in yt.captions:
      caption = yt.captions[language]
    elif 'a.en' in yt.captions:
      caption = yt.captions['a.en']
    else:
      caption = None
    return title, caption

if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=-qXlSIeKs8M"
    language = 'a.en'
    caption = process_video(video_url, language)
    if caption:
        print("Caption downloaded successfully.")
    else:
        print("Caption not available.")

