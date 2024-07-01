import os
import re
import json
import time
import requests
import mimetypes
from dotenv import load_dotenv

from requests.auth import HTTPBasicAuth
from requests_toolbelt.multipart.encoder import MultipartEncoder

from openai import OpenAI, AzureOpenAI, APIStatusError
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion

from constants import MODELS

load_dotenv()
# Replace these values with your WordPress site and credentials
WORDPRESS_URL = 'https://vedvaani.in/wp-json/wp/v2'
USERNAME = 'user'
PASSWORD = os.getenv('WP_APPLICATION_PASSWORD')

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# openai_client = AzureOpenAI(
#     api_version="2024-03-01-preview",
#     api_key=os.getenv("AZURE_API_KEY"),
#     azure_endpoint=os.getenv("AZURE_API_ENDPOINT")
# )


def record_token_usage(model: str, usage: CompletionUsage):
    with open('token_usage.csv', 'a') as file:
        file.write(f'{model},{usage.completion_tokens},{usage.prompt_tokens},{usage.total_tokens}\n')


def upload_image_to_wordpress(image_path, alt_text, caption, description):
    # Check if the file exists
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"The file {image_path} does not exist.")

    # Get the file name and mime type
    file_name = os.path.basename(image_path)
    mime_type, _ = mimetypes.guess_type(image_path)

    if mime_type not in ['image/jpeg', 'image/png', 'image/jpg']:
        raise ValueError("Only JPEG and PNG files are supported.")

    # Prepare the data for the request
    with open(image_path, 'rb') as file:
        file_content = file.read()

    data = MultipartEncoder(
        fields={
            'file': (file_name, file_content, mime_type),
            'title': file_name,
        }
    )

    # Set up the headers
    headers = {
        'Content-Type': data.content_type,
    }

    # Make the request to the WordPress REST API
    try:
        print("Attempting to upload image...")
        response = requests.post(
            f"{WORDPRESS_URL}/media",
            data=data,
            headers=headers,
            auth=(USERNAME, PASSWORD)
        )

        print(f"Upload response status code: {response.status_code}")
        print(f"Upload response content: {response.text}")
        time.sleep(5)

        # Check if the upload was successful
        if response.status_code == 201:
            uploaded_image = response.json()
            print("Image uploaded successfully. Updating metadata...")

            # Update the image with additional metadata
            metadata = {
                'alt_text': alt_text,
                'caption': caption,
                'description': description
            }
            update_response = requests.post(
                f"{WORDPRESS_URL}/media/{uploaded_image['id']}",
                json=metadata,
                headers={'Content-Type': 'application/json'},
                auth=(USERNAME, PASSWORD)
            )

            print(f"Metadata update response status code: {update_response.status_code}")
            print(f"Metadata update response content: {update_response.text}")

            if update_response.status_code == 200:
                print("Metadata updated successfully.")
                return uploaded_image['id']
            else:
                print("Metadata update failed, but image was uploaded.")
                return uploaded_image['id']
        else:
            print(f"Upload failed with status code {response.status_code}")
            print(f"Response content: {response.text}")
            raise Exception(f"Upload failed with status code {response.status_code}")
    except requests.RequestException as e:
        print(f"Error during request: {e}")
        raise


def create_blog_post(title, content, meta_description, slug, focus_keyphrase, seo_title,
                     featured_media_id=None, status='publish'):
    # Endpoint for creating a new post
    endpoint = f'{WORDPRESS_URL}/posts'

    # Data for the new post
    data = {
        'title': title,
        'content': content,
        'status': status,
        'slug': slug,
        'yoast_meta': {
            'yoast_wpseo_metadesc': meta_description,
            'yoast_wpseo_focuskw': focus_keyphrase,
            'yoast_wpseo_title': seo_title
        }
    }

    if featured_media_id:
        data['featured_media'] = featured_media_id

    # Print the data being sent (excluding sensitive information)
    print("Sending the following data:")
    print(json.dumps({k: v for k, v in data.items() if k != 'yoast_meta'}, indent=2))
    print("Meta data keys:", list(data['yoast_meta'].keys()))

    # Make the request to create the post
    try:
        response = requests.post(
            endpoint,
            json=data,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            headers={'Content-Type': 'application/json'},
            timeout=30  # Set a timeout of 30 seconds
        )

        # Force the response to be read
        response.raise_for_status()

        # Check if the request was successful
        if response.status_code == 201:
            print('Post created successfully!')
            post = response.json()
            print(f"Post ID: {post['id']}")
            print(f"Post URL: {post['link']}")
            return post
        else:
            print('Failed to create post')
            print('Status Code:', response.status_code)
            print('Response:', response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if hasattr(e, 'response'):
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None


def generate_title_and_blog(focus_keywords: str):
    messages = [
        {
            'role': 'system',
            'content': f'Generate an SEO Optimised Blog Title using focus keywords: {focus_keywords}. '
                       'Output only Title and nothing else.'
        }
    ]
    try:
        response: ChatCompletion = openai_client.chat.completions.create(
            model=MODELS.AZURE_GPT_4_OMNI,
            messages=messages,
            max_tokens=500,
            temperature=0.5,
            n=1
        )
        record_token_usage(MODELS.AZURE_GPT_4_OMNI, response.usage)
        messages.append(response.choices[0].message)
        blog_title = response.choices[0].message.content.replace('"', '').replace("'", '')
        print(blog_title)
        messages.append({
            'role': 'system',
            'content': 'Generate a 15 word meta description of a blog based on the focus keywords and the Blog Title.'
                       'Output only Meta Description and nothing else.'
        })
        response: ChatCompletion = openai_client.chat.completions.create(
            model=MODELS.AZURE_GPT_4_OMNI,
            messages=messages,
            max_tokens=500,
            temperature=0.5,
            n=1
        )
        record_token_usage(MODELS.AZURE_GPT_4_OMNI, response.usage)
        messages.append(response.choices[0].message)
        blog_description = response.choices[0].message.content.replace('"', '').replace("'", '')
        print(blog_description)
        messages.append({
            'role': 'system',
            'content': 'Generate a 1000 word SEO optimised blog based on the focus keywords, Blog Title and '
                       'the Meta Description.'
                       ' Output only Blog content and nothing else. Along with the required h2, p tags etc.'
                       ' Do not use # at all'
        })
        response: ChatCompletion = openai_client.chat.completions.create(
            model=MODELS.AZURE_GPT_4_OMNI,
            messages=messages,
            max_tokens=3000,
            temperature=0.5,
            n=1
        )
        record_token_usage(MODELS.AZURE_GPT_4_OMNI, response.usage)
        messages.append(response.choices[0].message)
        blog_content = response.choices[0].message.content.replace('"', '').replace("'", '')
        print(blog_content)
        return blog_title, blog_content, blog_description
    except APIStatusError as e:
        print(f"APIStatusError: {e}")
        return "OpenAI API Error", "OpenAI API Error", "OpenAI API Error"


def add_outbound_links():
    outbound_content = """\n<p>To know detailed horoscope, consider talking to our&nbsp;<a 
    href="https://play.google.com/store/apps/details?id=com.vedvaani.app">AI Astrology app VedVaani. The first chat 
    free (5 messages)! Limited time offer.</a></p>"""
    outbound_content = outbound_content + """\n<p><strong><a href="https://vedvaani.in">VedVaani</a>is the Highest 
    Rated AI Astrology App On<a href="https://play.google.com/store/apps/details?id=com.vedvaani.app" 
    target="_blank" rel="noreferrer noopener">Play Store</a>&nbsp;and <a 
    href="https://apps.apple.com/in/app/vedvaani-astro-kundli-tarot/id6476832303">App Store</a> with a rating of 4.7+ 
    ✨</strong>.</p>"""
    return outbound_content


def get_posts(number: int = 2):
    # Endpoint to get posts
    endpoint = f'{WORDPRESS_URL}/posts'

    # Parameters to fetch only the last two posts
    params = {
        'per_page': number,
        'order': 'desc',
        'orderby': 'date'
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors

        posts = response.json()
        return posts

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def add_internal_links():
    recent_posts = get_posts()
    internal_link_content = "<p>Read more on VedVaani </p>"
    for post in recent_posts:
        title = post['title']['rendered']
        link = post['link']
        internal_link_content = internal_link_content + f'<p><a href="{link}">{title}</a></p>'
    return internal_link_content


def download_image(url, destination):
    try:
        print("Downloading image from %s", url)
        response = requests.get(url)
        if response.status_code == 200:
            with open(destination, 'wb') as f:
                f.write(response.content)
            print("Image downloaded successfully")
        else:
            print("Failed to download image. Status code: %d", response.status_code)
    except Exception as e:
        print("An error occurred while downloading the image: %s", str(e))


def generate_photos(image_prompt: str):
    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1792x1024",
        quality="standard",
        style="natural",
        n=1,
    )

    image_url = response.data[0].url
    file_name = re.sub(r'\s+', '_', image_prompt)
    file_name = file_name + ".png"
    download_image(image_url, file_name)
    return file_name


if __name__ == '__main__':
    # Define the title, content, and meta description of the post
    focus_keywords = input("Input Focus Keywords")
    post_title, post_content, meta_description = generate_title_and_blog(focus_keywords=focus_keywords)
    post_content = post_content + add_outbound_links()
    post_content = post_content + add_internal_links()

    # Path to the featured media file
    featured_media_path = generate_photos(image_prompt=focus_keywords)

    # Upload the media and get the media ID
    featured_media_id = upload_image_to_wordpress(featured_media_path, alt_text=focus_keywords,
                                                  caption=focus_keywords, description=focus_keywords)
    print(featured_media_id)

    # Create the blog post
    create_blog_post(post_title, post_content, meta_description=meta_description,
                     slug=re.sub(r'\s+', '-', post_title),
                     focus_keyphrase=focus_keywords,
                     seo_title=post_title,)

