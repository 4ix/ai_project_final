# %%
import os, time, random, datetime, textwrap
import openai
import cv2
import requests
import urllib.request
import pandas as pd
import numpy as np

from dotenv import load_dotenv
from konlpy.tag import Kkma
from nltk.tokenize import sent_tokenize
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
    global logs, korean
    logs += '<br>' + '한글 자막 생성 시작'
    
    kkma = Kkma()

    messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": query}]
    messages.append({"role": "user", "content": f'반드시 내용은 {option} 문장으로 작성해 주세요. 각 문장의 길이는 최대 10단어 이내여야 합니다.'})

    response = openai.ChatCompletion.create(model = model, messages = messages)
    subtitles = response['choices'][0]['message']['content']

    korean = kkma.sentences(subtitles) # 문장별로 나누기
    logs += '<br>' + '한글 자막 생성 완료'

    translateEnglish(subtitles)
    return korean
# %%
def translateEnglish(query): # 영어 번역
    global logs, english
    logs += '<br>' + '영어 번역 시작'

    translator = Translator()
    translated = translator.translate(query, dest='en', src='auto').text
    
    english = sent_tokenize(translated) # 문장별로 나누기
    english = [e for e in english if len(e) > 5] # 생성된 자막에서 넘버링(1., 2. 등을 제거)
    for e in english:
        print(e)
    logs += '<br>' + '영어 번역 완료'

    # makePrompts(english)
    tts(file_name)
    return english
# %%
def makePrompts(query) : # 프롬프트 생성 함수.
    global logs, prompts
    for i in range(len(query)):
        logs += '<br>' + f'{query[i]} 프롬프트 생성 시작 {i+1}/{len(query)}'
        
        messages = [{"role": "system", "content": "You are an assistant who is good at creating prompts for image creation."},{"role": "assistant", "content": query[i]}]
        messages.append({"role": "user", "content": "Condense up to 4 outward description to focus on nouns and adjectives separated by ,"})

        response = openai.ChatCompletion.create(model=model, messages=messages)
        prompt = response['choices'][0]['message']['content']
        print(prompt)
        prompts.append(prompt)
        time.sleep(5)
        if len(prompts) >= len(query):
            logs += '<br>' + '프롬프트 생성 완료'
            break

    # makeCsv()
    return prompts

# %%
def tts(file_name):
    global logs
    logs += '<br>' + '음성 파일 생성 시작'

    for i in range(len(korean)):
        tts = gTTS(text = korean[i], lang='ko')
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

        response = openai.Image.create(prompt = english[i], n=1, size='512x512')
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

    x_text = 30
    y_text = 450

    font = ImageFont.truetype('NanumBarunGothic.ttf', size=27)
    font_color = 'rgb(255,255,255)'
    for i in range(len(korean)):

        image = Image.open(file_name + '/' + f'{i}_image.png')
        draw = ImageDraw.Draw(image, 'RGBA')

        lines = textwrap.wrap(korean[i], width=23)

        draw.rectangle((0,420,512,512), width=1, fill=(0,0,0,100))
        for line in lines:
            width, height = font.getsize(line)
            if len(lines) == 1:
                draw.text((x_text, y_text), line, font=font, fill=font_color)
            elif len(lines) == 2:
                draw.text((x_text, y_text-10), line, font=font, fill=font_color)
            else:
                draw.text((x_text, y_text-23), line, font=font, fill=font_color)
            y_text += height
        
        image.save(file_name + '/' + f'{i}_sub.png')

        x_text = 30
        y_text = 450
    logs += '<br>' + '자막 입히기 완료'
    makeMovie(file_name)
    return True

# %%
def makeMovie(file_name):
    global logs, final_video_path
    video_list = []
    logs += '<br>' + '최종 마무리 작업중입니다...'
    for i in range(len(korean)):
        audio_clip = AudioFileClip('./' + file_name + '/' + f'{i}_sound.mp3')
        image_clip = ImageClip('./' + file_name + '/' + f'{i}_sub.png')
        video_clip = image_clip.set_audio(audio_clip)
        video_clip.duration = audio_clip.duration
        video_clip.fps = 1
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