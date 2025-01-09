import requests
import openai
import os
from dotenv import load_dotenv
import re
from bs4 import BeautifulSoup
from bs4 import Comment
import time

load_dotenv()

# Constants
base_url = os.getenv("WP_API_URL")
username = os.getenv("WP_USERNAME")
password = os.getenv("WP_PASSWORD")

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_TOKEN")


# Function to Get Original Post Content
def get_original_post(post_id):
    response = requests.get(
        f"{base_url}/posts/{post_id}?context=edit", auth=(username, password)
    )
    if response.status_code == 200:
        post = response.json()
        return post["title"]["raw"], post["content"]["raw"]
    else:
        raise Exception(f"Error retrieving post. Status code: {response.status_code}")


def translate_text(text, target_language):
    prompt = f"Translate the following English HTML content to {target_language}:\n\n{text}\n\nTranslated Content:"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that translates English HTML content to another language while retaining the structure.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message["content"]


def translate_text_with_retry(text, target_language, retries=3, delay=10):
    for i in range(retries):
        try:
            return translate_text(text, target_language)
        except openai.error.ServiceUnavailableError:
            if i < retries - 1:  # i is 0 indexed
                print(f"Error: Service unavailable. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise


def translate_content(content, target_language):
    blocks = content.split("\n\n")
    translated_blocks = []

    for block in blocks:
        if re.match(r"<!-- wp:paragraph(\s*\{.*\})? -->", block) or re.match(
            r"<!-- wp:heading(\s*\{.*\})? -->", block
        ):
            print(f"Translating block:\n{block}")
            translated_block = translate_text_with_retry(block, target_language)
            print(f"Translated block:\n{translated_block}")

            # Pause for user input
            # input("Press enter to continue to the next block...")

            translated_blocks.append(translated_block)
        else:
            # If the block is neither a paragraph nor a heading, append it as is.
            translated_blocks.append(block)
            print(f"Appended block:\n{block}")

    return "\n\n".join(translated_blocks)


# Function to Create a Translated Post
def create_translated_post(original_title, original_content, target_language):
    translated_title = translate_text_with_retry(
        original_title, target_language
    ).title()
    translated_content = translate_content(original_content, target_language)

    # Create the post payload
    post_data = {
        "title": translated_title,
        "content": translated_content,
        "status": "draft",  # Save as draft
    }

    # Make the request to create the post
    response = requests.post(
        f"{base_url}/posts", auth=(username, password), json=post_data
    )

    if response.status_code == 201:
        print(f"Post successfully created in {target_language}.")
    else:
        print(f"Error creating post. Status code: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    post_id = input("Enter the ID of the original post: ")
    target_language = input("Enter target language (e.g., 'fr' for French): ")

    original_title, original_content = get_original_post(post_id)
    create_translated_post(original_title, original_content, target_language)
