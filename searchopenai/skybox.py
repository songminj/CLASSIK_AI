import requests
import openai
from openai import OpenAI
from dotenv import load_dotenv
import os
import time

load_dotenv()
client = OpenAI()
SKYBOX_API_KEY = os.getenv("SKYBOX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

BASE_URL = 'https://backend.blockadelabs.com/api/v1/skybox'
RESULT_FOLDER = 'assets'

# 결과 폴더가 없으면 생성
if not os.path.exists(RESULT_FOLDER):
    os.makedirs(RESULT_FOLDER)


def make_prompt(title):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a guide for creating video prompts that match classical music. "
                    "Use the following guidelines:\n\n"
                    "1. Keep it simple and experiment: Use 3-4 concise phrases to describe the scene, avoiding complexity that may override the style preset.\n"
                    "2. Scene details: Include key visual elements and mood without excessive stylistic details. Use the 'Advanced (No Style)' preset when needed.\n"
                    "3. Indoors vs outdoors: Specify 'indoors' or 'outdoors' at the beginning of the prompt if needed.\n"
                    "4. Sky-only views: For skyboxes, use the 'Sky' preset and focus on describing cloud types if relevant.\n"
                    "5. Camera POV: Set the view (e.g., 'aerial view,' 'ground view') at the start to control perspective.\n"
                    "6. Day and night scenes: Use words like 'nighttime' or 'daytime' to set the mood. Avoid using negatives like 'no daylight.'\n"
                    "7. Cleaner results: Use the negative prompt to exclude unwanted items like 'blurry,' and remix as needed for style adjustments.\n\n"
                    "Now, based on the provided title, create a prompt that visually captures the mood, setting, and atmosphere to match the essence of the music within 400 characters and in English."
                )
            },
            {
                "role": "user",
                "content": title
            }
        ],
        temperature=0.6,
        max_tokens=64,
        top_p=1
    )
    return response.choices[0].message.content


    
def download_file(url, filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"Downloaded {filename}")
    else:
        print("Failed to download the file.")



def generate_skybox(prompt):
    headers = {
        'x-api-key': SKYBOX_API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        'prompt': prompt
    }
    
    # Skybox 생성 요청
    response = requests.post(BASE_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        status = result.get('status')
        skybox_id = result.get('obfuscated_id')
        
        if not skybox_id:
            print("Failed to retrieve skybox ID.")
            return
        check_url = f'https://backend.blockadelabs.com/api/v1/imagine/requests/obfuscated-id/{skybox_id}'
        
        while status != 'complete':
            response = requests.get(check_url, headers=headers)
            result = response.json()
            # print(result)
            status = result["request"].get('status')
            # print(f"Skybox requested with ID: {skybox_id}, Initial status: {status}")
            time.sleep(6)
        
        print(f"Skybox requested with ID: {skybox_id}, Initial status: {status}")
        
        export_data = {
            'skybox_id': skybox_id,
            'type_id': 1   # jpg로 이미지 추출 
        }
        status_url = f"{BASE_URL}/export"
        
        # 상태 확인
        while True:
            status_response = requests.post(status_url, headers=headers, json=export_data)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status')
                
                if status == 'pending':
                    print("Skybox generation is still pending. Checking again in 5 seconds...")
                    time.sleep(5)  # 5초 대기 후 상태 재확인
                elif status == 'complete':
                    file_url = status_data.get('file_url')
                    if file_url:
                        filename = os.path.join(RESULT_FOLDER, f"{skybox_id}.jpg")
                        download_file(file_url, filename)
                    else:
                        print("File URL is not available.")
                    break
                elif status == 'error':
                    print("Error:", status_data.get('error_message', 'Unknown error'))
                    break
                else:
                    print(f"Unexpected status: {status}. Exiting.")
                    break
            else:
                print("Status request failed:", status_response.status_code, status_response.text)
                break
    else:
        print("Failed to create skybox:", response.status_code, response.text)

if __name__ == '__main__':
    title = input("Enter prompt for skybox generation: ")
    prompt = make_prompt(title)
    print(prompt)
    generate_skybox(prompt)
