import requests
import boto3
import pymysql
import openai
from openai import OpenAI
from dotenv import load_dotenv
import os
import time

# key 관리
load_dotenv()
client = OpenAI()
SKYBOX_API_KEY = os.getenv("SKYBOX_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

BASE_URL = 'https://backend.blockadelabs.com/api/v1/skybox'
S3_URL = 'https://classik-bucket.s3.ap-northeast-2.amazonaws.com'
RESULT_FOLDER = 'assets'
BUCKET_NAME = 'classik-bucket'

# 결과 폴더가 없으면 생성
if not os.path.exists(RESULT_FOLDER):
    os.makedirs(RESULT_FOLDER)


# S3연결하기 
def s3_connection():
    try:
        s3 = boto3.client(
            service_name="s3",
            region_name="ap-northeast-2", # 자신이 설정한 bucket region
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
    except Exception as e:
        print(e)
    else:
        print("s3 bucket connected!")
        return s3

s3 = s3_connection()

# DB 연결
classik = pymysql.connect(host='127.0.0.1', user='root', password='0516', db='classik', charset='utf8')
cursor = classik.cursor()

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

def s3_put_object(s3, bucket, filepath, video_id):
    """
    s3 bucket에 지정 파일 업로드
    :param s3: 연결된 s3 객체(boto3 client)
    :param bucket: 버킷명
    :param filepath: 파일 위치
    :param access_key: 저장 파일명
    :return: 성공 시 True, 실패 시 False 반환
    """
    try:
        s3.upload_file(
            Filename=filepath,
            Bucket=bucket,
            Key=video_id,
            ExtraArgs={"ContentType": "image/jpg"},
        )
    except Exception as e:
        print(e)
        return False
    return True



def handle_upload_img(filename, video_id): # f = 파일명
    data = open('assets/'+filename+'.jpg', 'rb')
    # '로컬의 해당파일경로'+ 파일명 + 확장자
    s3.upload_file(
        Key=video_id, Body=data, ContentType='image/jpg')



def download_file(url, filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"Downloaded {filename}")
        return filename
    else:
        print("Failed to download the file.")
        return None



def generate_skybox(title, prompt):
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
            status = result["request"].get('status')
            time.sleep(3)
        
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
                        return skybox_id
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



def update_vr_image_url(video_id, vr_image_url):
    try:
        sql = "UPDATE track SET vr_image_url = %s WHERE video_id = %s"
        cursor.execute(sql, (vr_image_url, video_id))
        classik.commit()
        print(f"Updated vr_image_url for track ID {video_id}")
    except Exception as e:
        print("Failed to update database:", e)



if __name__ == '__main__':
    # track 테이블의 title을 가져와 Skybox 생성 및 저장
    cursor.execute("SELECT track_id, video_id, title FROM track")
    tracks = cursor.fetchall()
    
    for track_id, video_id, title in tracks:
        prompt = make_prompt(title)
        print(prompt)
        filename = generate_skybox(title, prompt)
        
        if filename:
            if s3_put_object(s3, BUCKET_NAME, f'./assets/{filename}.jpg', video_id):
                vr_image_url = f"{S3_URL}/{video_id}"
                print(vr_image_url)
                update_vr_image_url(video_id, vr_image_url)

            else:
                print("Failed to upload image to S3 for track ID:", track_id)
        print(track_id, " done!")
    print("end !~~")
