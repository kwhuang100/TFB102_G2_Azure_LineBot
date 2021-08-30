#!/usr/bin/env python
# coding: utf-8

# In[1]:


from os import getcwd
from flask import Flask, request, render_template
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import requests
from bs4 import BeautifulSoup as Soup
import azure.cognitiveservices.speech as speechsdk


# In[5]:


userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
headers = {
    'User-Agent':userAgent
}
app = Flask(__name__, 
            static_url_path='/tfb102', 
            static_folder='./tfb102')

@app.route('/', methods=['GET','POST'])
def First():
    outStr = '''
    <html>
    <form id="myform" method="POST" action="" enctype="multipart/form-data">
    請上傳圖片:<input type="file" id="profile_pic" name="profile_pic" accept=".jpg, .jpeg, .png"><br>
    <input type="submit">
    </form>
    </html>
    '''
    if request.method == "POST":
        img = request.files.get('profile_pic')
        file_path = getcwd()+ '\\' +img.filename
        img.save(file_path)
        # Set API key.
        subscription_key = ''
        # Set endpoint.
        endpoint = ''
        # Call API
        computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))

        # call API with path
        remote_image_path_objects = getcwd() + f'\\{img.filename}'
        remote_image_path = open(remote_image_path_objects, "rb")

        # Call API with content type (landmarks) and URL
        detect_domain_results_landmarks = computervision_client.analyze_image_by_domain_in_stream("landmarks", remote_image_path)

        print("detecting...")
        if len(detect_domain_results_landmarks.result["landmarks"]) == 0:
            print("No landmarks detected.")
        else:
            for landmark in detect_domain_results_landmarks.result["landmarks"]:
                land = landmark["name"]
                print(land)
                url = f'https://en.wikipedia.org/wiki/{land}'
                res = requests.get(url=url, headers=headers)
                soup = Soup(res.text, 'html.parser')
                text = soup.select('#mw-content-text > div.mw-parser-output > p:nth-child(7)')[0].text
                if text:
                    # Replace with your own subscription key and region identifier from here: https://aka.ms/speech/sdkregion
                    speech_key, service_region = "605553ffd4c9486a81cec468cf6e8905", "southcentralus"
                    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

                    # Creates an audio configuration that points to an audio file.
                    # Replace with your own audio filename.
                    audio_filename = f"{land}.mp3"
                    audio_output = speechsdk.audio.AudioOutputConfig(filename=audio_filename)

                    # Creates a synthesizer with the given settings
                    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_output)

                    # Synthesizes the text to speech.
                    # Replace with your own text.
                    result = speech_synthesizer.speak_text_async(text).get()
                    # Checks result.
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        print("Speech synthesized to speaker for text [{}]".format(text))
                    elif result.reason == speechsdk.ResultReason.Canceled:
                        cancellation_details = result.cancellation_details
                        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
                        if cancellation_details.reason == speechsdk.CancellationReason.Error:
                            if cancellation_details.error_details:
                                print("Error details: {}".format(cancellation_details.error_details))
                        print("Did you update the subscription info?")
                        
        outStr += f'<audio src="{land}.mp3" autoplay controls></audio>'
        outStr += f'<h1> This is {land}!</h1>'
        outStr += f'<img src= "./tfb102/{img.filename}" height="600" weight="600">' # 展示圖片

    return outStr


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

