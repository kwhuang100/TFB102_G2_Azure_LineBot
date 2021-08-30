#!/usr/bin/env python
# coding: utf-8

# ---

# # Func define version

# ## import module

# In[ ]:


from re import sub
from os import getcwd
from requests import get
from bs4 import BeautifulSoup as Soup
from flask import Flask, request, abort
# import linebot related
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, ImageMessage, TextSendMessage,
    AudioSendMessage, StickerSendMessage,TemplateSendMessage,
    ButtonsTemplate, URITemplateAction
)
# import Azure module
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import azure.cognitiveservices.speech as speechsdk


# ## Azure Image function
# ### change your "subscription_key", "endpoint"

# In[ ]:


def Azure_image(file_path):
    global result_type
    #Azure
    # Set API key.
    subscription_key = ''
    # Set endpoint.
    endpoint = ''
    # Call API
    computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))
    # call API with path
    remote_image_path_objects = file_path
    remote_image_path1 = open(remote_image_path_objects, "rb")
    remote_image_path2 = open(remote_image_path_objects, "rb")

    # Call API with content type (landmarks, celebrities)
    while True:
        landmark_detect = computervision_client.analyze_image_by_domain_in_stream("landmarks", remote_image_path1)
        if len(landmark_detect.result["landmarks"]) != 0:
            for landmark in landmark_detect.result["landmarks"]:
                result_name = landmark["name"]
                result_type = 'landmark'
            break
        
        cele_detect = computervision_client.analyze_image_by_domain_in_stream("celebrities", remote_image_path2)
        if len(cele_detect.result["celebrities"]) != 0:
            for celeb in cele_detect.result["celebrities"]:
                result_name = celeb["name"]
                result_type = "celebrity"
            break

        result_name = None
        break
    return result_name

# Azure_image(file_path)


# ## wiki craw function

# In[ ]:


def wiki_craw(result_name_to_text):
    global url
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
    headers = {
        'User-Agent':userAgent
    }
    url = f'https://en.wikipedia.org/wiki/{result_name_to_text}'
    res = get(url=url, headers=headers)
    soup = Soup(res.text, 'html.parser')
    text_=''
    for x in soup.select('p')[:5]:
        text_ += x.text.replace('\n','')
        if len(text_.split())>100:
            break
    text = sub('\[\d*]',' ',text_)
    text = sub('\(.*Chinese: .*;+',' ',text)
    return text

# wiki_craw(result_name_to_text)


# ## Azure Speech function
# ### change your "speech_key", "service_region"

# In[ ]:


def Azure_Speech(text,audio_file):
    # Replace with your own subscription key and region identifier from here: https://aka.ms/speech/sdkregion
    speech_key, service_region = "", ""
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

    # Creates an audio configuration that points to an audio file.
    # Replace with your own audio filename.
    audio_filename = getcwd()+ '\\tmp\\' + audio_file
    audio_output = speechsdk.audio.AudioOutputConfig(filename=audio_filename)

    # Creates a synthesizer with the given settings
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_output)
    result = speech_synthesizer.speak_text_async(text).get()

# Azure_Speech(text,result_name_to_text)


# ---

# ## main function

# ### before running it, change your "ngrok_url", "line_bot_api", "handler" and create a folder "tmp"

# In[ ]:


# change your own ngrok url
ngrok_url = ''

# create flask server
app = Flask(__name__, 
            static_url_path= '//tmp', 
            static_folder='./tmp')
# your linebot message API - Channel access token (from LINE Developer)
line_bot_api = LineBotApi('')
# your linebot message API - Channel secret
handler = WebhookHandler('')

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        print('receive msg')
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

# handle msg
@handler.add(MessageEvent)
def handle_message(event):
    if event.message.type=='image':
        
        # save image
        message_content = line_bot_api.get_message_content(event.message.id)
        image_file_name = f'{event.message.id}.jpg'
        file_path = getcwd()+'\\tmp\\'+ image_file_name
        with open(file_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        
        # Azure detect image
        result_name = Azure_image(file_path)
        if result_name:
            
            # wiki craw
            result_name_to_text = result_name.replace(' ','_')
            wiki_text = wiki_craw(result_name_to_text)
            if wiki_text:
                
                # Azure Speech text
                audio_file = f"{result_name_to_text}.wav"
                Azure_Speech(wiki_text,audio_file)

                if result_type == 'celebrity':
                    other_url = 'https://www.youtube.com/results?search_query={}'.format(result_name.replace(' ','+'))
                    other_label = 'youtube.com'
                elif result_type == 'landmark':
                    other_url = 'https://www.tripadvisor.com.tw/Search?q={}'.format(result_name_to_text)
                    other_label = 'tripadvisor.com.'
                    
                audio_url = ngrok_url + r'/tmp/'+ audio_file
                image_url = ngrok_url + r'/tmp/'+ image_file_name
                
            line_bot_api.reply_message(event.reply_token,
                                       [TemplateSendMessage(
                                            alt_text='please check message on your phone.',
                                            template=ButtonsTemplate(
                                                thumbnail_image_url = image_url,
                                                title = result_name,
                                                text = f"Taiwan's {result_type}",
                                                   actions=[
                                                    URITemplateAction(
                                                    label='Wiki.com',
                                                    uri=url),
                                                   URITemplateAction(
                                                   label=other_label,
                                                   uri=other_url)])),
                                       AudioSendMessage(original_content_url=audio_url,
                                                       duration=120000)])
        
        else:
            line_bot_api.reply_message(event.reply_token,
                                       [TextSendMessage(text = 'Beats me, please change another photo related to Taiwan landmark or celebrities, We will try our best to share you the story.'),
                                      StickerSendMessage(package_id='8522',sticker_id='16581274')])
            
        
    else:
        welcome_text = '''Welcome to 映像說臺灣!\nPlease upload a photo related to Taiwan landmark or celebrities, we will share you the story. Wish you could enjoy a handy and interactive tourguide with us.'''
        line_bot_api.reply_message(event.reply_token,[TextSendMessage(text = welcome_text),
                                                     StickerSendMessage(package_id='446',sticker_id='1988')])
    

# run app
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=12345)


# In[ ]:




