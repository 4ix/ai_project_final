# %%
import os, time, random, datetime, textwrap
import openai
import cv2
import requests
import urllib.request
import pandas as pd
import numpy as np

from dotenv import load_dotenv
from googletrans import Translator
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

korean, english, logs, prompts, file_name = '', '', '', '', []

model = "gpt-3.5-turbo"

# %%
def setName(query): # 기본 설정 셋팅 함수
    global logs, file_name
    logs = '기본 설정 시작'

    d = datetime.datetime.now()
    date_time = d.strftime("%x")
    file_name = date_time[-2:] + date_time[:2] + date_time[3:5] + '_'

    for _ in range(5):
        r = chr(random.randint(ord('a'), ord('z')))
        R = chr(random.randint(ord('A'), ord('Z')))
        file_name += (r, R)[random.randint(0, 1)]
        
    os.mkdir(file_name)

    logs += '<br>' + '기본 설정 완료'
    makeSubtitles(query, 5)
    return file_name
# %%
def makeSubtitles(query, option): # 한글 자막 생성 함수
    global logs, subtitles
    PROMPTS = os.getenv("PROMPTS")
    logs += '<br>' + '한글 자막 생성 시작'
    
    messages = [{"role": "system", "content": "You are a professional journalist."}]
    input_text = f'주제를 소개하는 짧은 영상을 제작하기 위한 스크립트를 작성해야 합니다.주제: {query}'
    for p in PROMPTS:
        input_text += p   
    messages.append({"role": "user", "content": input_text})

    response = openai.ChatCompletion.create(model = model, messages = messages)
    korean = response['choices'][0]['message']['content']
    response = response['choices'][0]['message']['content']

    subtitles = response.split('\n')
    subtitles = [line.strip('\"').strip() for line in subtitles if len(line) != 0] # 0인 경우 없앰
    for k in subtitles:
        print(k)
    logs += '<br>' + '한글 자막 생성 완료'

    translateEnglish(korean)
    return subtitles
# %%
def translateEnglish(query): # 영어 번역
    global logs, english
    logs += '<br>' + '영어 번역 시작'

    translator = Translator()
    translated = translator.translate(query, dest='en', src='auto').text
    
    english = translated.split('.')
    english = [e for e in english if len(e) > 5] # 생성된 자막에서 넘버링(1., 2. 등을 제거)
    for e in english:
        print(e)
    logs += '<br>' + '영어 번역 완료'

    tts(file_name)
    return english

# %%
def tts(file_name):
    global logs
    logs += '<br>' + '음성 파일 생성 시작'

    for i in range(len(subtitles)):
        tts = gTTS(text = subtitles[i], lang='ko')
        sSaveFile = file_name + '/' + f'{i}_sound.mp3'
        tts.save(sSaveFile)
    logs += '<br>' + '음성 파일 생성 완료'
    dalle(file_name)
    return True
# %%
def dalle(file_name):
    global logs
    for i in range(len(english)):
        logs += '<br>' + f'이미지 생성 시작 {i+1}/{len(english)}'

        response = openai.Image.create(prompt = f'book illustration, {english[i]}', n=1, size='512x512')
        image_url = response['data'][0]['url']
        res = requests.get(image_url)

        resp = urllib.request.urlopen(image_url)
        image = np.asarray(bytearray(resp.read()), dtype='uint8')
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        cv2.imwrite(file_name + '/' + f'{i}_image.png', image)
    logs += '<br>' + '이미지 생성 완료'
    addSubtitle(file_name)
    return True

# %%
def addSubtitle(file_name):
    global width, height, logs
    logs += '<br>' + '자막 입히기 시작'

    offset = (400, 110) # 생성된 이미지 위치
    sub_offset = (0, 568) # 자막 배경 위치
    text_offset = [300, 620] # 자막 위치

    font = ImageFont.truetype('NanumBarunGothic.ttf', size=40)
    for i in range(len(subtitles)):
        base = Image.open('images/base.jpg')
        image = Image.open(file_name + '/' + f'{i}_image.png')

        base.paste(image, box=(offset[0],offset[1],offset[0]+512,offset[1]+512))

        draw = ImageDraw.Draw(base, 'RGBA')

        lines = textwrap.wrap(subtitles[i], width=30)

        draw.rectangle((sub_offset[0],sub_offset[1],sub_offset[0]+1280,sub_offset[1]+200), width=1, fill=(0,0,0,100))

        for line in lines:
            width, height = font.getsize(line)
            print(line)
            if len(lines) == 1:
                draw.text((text_offset[0], text_offset[1]), line, font=font, fill=(255,255,255))
            elif len(lines) == 2:
                draw.text((text_offset[0], text_offset[1]-15), line, font=font, fill=(255,255,255))
            else:
                draw.text((text_offset[0], text_offset[1]-35), line, font=font, fill=(255,255,255))
            text_offset[1] += height
        
        base.save(file_name + '/' + f'{i}_sub.png')

        text_offset = [300, 620] # 자막 위치 초기화

    logs += '<br>' + '자막 입히기 완료'
    makeMovie(file_name)
    return True

# %%
def makeMovie(file_name):
    global logs, final_video_path
    video_list = []
    logs += '<br>' + '거의 다 됐습니다...'
    for i in range(len(subtitles)):
        audio_clip = AudioFileClip('./' + file_name + '/' + f'{i}_sound.mp3')
        image_clip = ImageClip('./' + file_name + '/' + f'{i}_sub.png')
        video_clip = image_clip.set_audio(audio_clip)
        video_clip.duration = audio_clip.duration
        video_clip.fps = 24
        video_clip.write_videofile(file_name + '/' + f'{i}_movie.mp4', codec="libx264")
        video_list.append(file_name + '/' + f'{i}_movie.mp4')

    video_clips = []
    for video in video_list:
        video_clip = VideoFileClip(video)
        video_clips.append(video_clip)
    final_video_clip = concatenate_videoclips(video_clips)
    final_video_path = file_name + '/' + f'{file_name}.mp4'

    final_video_clip.write_videofile(final_video_path)
    logs += '<br>' + '영상 생성 완료!'
    return True