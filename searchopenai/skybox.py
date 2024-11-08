import requests
from dotenv import load_dotenv
import os
import time

load_dotenv()
SKYBOX_API_KEY = os.getenv("SKYBOX_API_KEY")
BASE_URL = 'https://backend.blockadelabs.com/api/v1/skybox'
RESULT_FOLDER = 'assets'

# 결과 폴더가 없으면 생성
if not os.path.exists(RESULT_FOLDER):
    os.makedirs(RESULT_FOLDER)
    
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
        skybox_id = result.get('obfuscated_id')
        status = result.get('status')
        print(f"Skybox requested with ID: {skybox_id}, Initial status: {status}")
        
        if not skybox_id:
            print("Failed to retrieve skybox ID.")
            return
        
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
    prompt = input("Enter prompt for skybox generation: ")
    generate_skybox(prompt)
