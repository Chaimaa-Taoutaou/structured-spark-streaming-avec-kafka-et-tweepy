import requests
import streamlit as st
from streamlit_lottie import st_lottie
import sounddevice as sd
import speech_recognition as sr
import soundfile as sf
import tweepy
import time
from kafka import KafkaProducer
import json
import datetime
import config

st.set_page_config(page_title="Track", page_icon=":hourglass:", layout="wide")


api_key = config.api_key
api_key_secret = config.api_key_secret
access_token = config.access_token
access_token_secret = config.access_token_secret
bearer_token = config.bearer_token

producer = KafkaProducer(bootstrap_servers=['localhost:9092'])

def getClient():
	client = tweepy.Client(
		bearer_token = bearer_token,
		consumer_key = api_key,
		consumer_secret = api_key_secret,
		access_token = access_token,
		access_token_secret = access_token_secret
	)
	return client

client = getClient()	

def getTweet(client, id):
    try:
        tweet = client.get_tweet(id, expansions=['author_id'], user_fields=['username', 'description', 'location', 'public_metrics'], tweet_fields=["created_at", "lang", "conversation_id", "public_metrics"])
    except tweepy.errors.TooManyRequests:
        time.sleep(60)  # Sleep for 60 seconds before retrying
        tweet = client.get_tweet(id, expansions=['author_id'], user_fields=['username', 'description', 'location', 'public_metrics'], tweet_fields=["created_at", "lang", "conversation_id", "public_metrics"])
    
    return tweet

class MyStream(tweepy.StreamingClient):
    # This function gets called when the stream is working
    def on_connect(self):
        print("Connected")
    
    

    def on_tweet(self, tweet):
    	if tweet is not None and len(tweet)>0:
    		twt =  getTweet(client, tweet.id)
    		if twt is not None and twt.data is not None and twt.data.conversation_id is not None:
	    		twt = getTweet(client, twt.data.conversation_id)
	    		
	    		
	    		if 'users' in twt.includes:
	    			user = twt.includes["users"]
		    		for user in user:
		    			user = {
		    				'name': user.name,
		    				'username': user.username,
		    				'location': user.location,
		    				'description': user.description,
		    				'followers_count': user['public_metrics']['followers_count'],
		    				'following_count': user['public_metrics']['following_count'],
		    				'tweet_count': user['public_metrics']['tweet_count'],
		    				'listed_count': user['public_metrics']['listed_count']
						}
		    		tweet_data = {
		    			'created_at': twt.data.created_at.isoformat(),
		    			'text': twt.data.text,
		    			'retweet_count': twt[0]['public_metrics']['retweet_count'],
		    			'reply_count': twt[0]['public_metrics']['reply_count'],
		    			'like_count': twt[0]['public_metrics']['like_count'],
		    			'quote_count': twt[0]['public_metrics']['quote_count'],
		    			'impression_count': twt[0]['public_metrics']['impression_count'],
		    			'lang': twt.data.lang,
		    			'user_name': user['name'],
		    			'user_username': user['username'],
		    			'user_location': user['location'],
		    			'user_description': user['description'],
		    			'user_followers_count': user['followers_count'],
		    			'user_following_count': user['following_count'],
		    			'user_tweet_count': user['tweet_count'],
		    			'user_listed_count': user['listed_count']

		    		}
		    		
		    		#tweet_data['user'].append(user)
		    		#st.write(tweet_data)
		    		print(tweet_data)
		    		producer.send('taylor', json.dumps(tweet_data).encode('utf-8'))
   
def startStream():
	# Creating Stream object
	stream = MyStream(bearer_token=bearer_token)
	stream.add_rules(tweepy.StreamRule(prompt))
	# Starting stream
	stream.filter(tweet_fields=["referenced_tweets"])
	


# Fonction pour charger l'animation Lottie depuis l'URL
def load_lottie_animation(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

lottie_url = "https://assets10.lottiefiles.com/private_files/lf30_bz1uh69q.json"



# Initialize prompt in session state
if "prompt" not in st.session_state:
    st.session_state["prompt"] = ""

# Add custom CSS to modify the container width and margins
st.markdown(
    """
    <style>
    .reportview-container .main {
        max-width: 100%;
        padding-left: 0rem;
        padding-right: 0rem;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# About Us Section
with st.container():
    left_column, right_column = st.columns([1,1])
    with left_column:
        # Define the text
        text = "Sentiment Analyzer App: Unleash the Power of Your Voice"

        # Apply HTML formatting to change the color
        colored_text = f"<span style='color: #007dff;'>{text}</span>"

        # Render the colored text using markdown
        st.markdown(f"<h3>{colored_text}</h3>", unsafe_allow_html=True)

        st.write("##")
        # Define the text content
        text = """
        Have you ever wanted to effortlessly analyze the sentiment of a specific tag or hashtag on social media? 
        Imagine being able to express your thoughts and opinions using just your voice and instantly gaining 
        valuable insights. With our groundbreaking Sentiment Analyzer App, this futuristic concept becomes a reality.
        Now you can start recording.
        """

        # Apply CSS styling to justify the text
        justified_text = f"<p style='text-align: justify;'>{text}</p>"

        # Render the justified text using markdown
        st.markdown(justified_text, unsafe_allow_html=True)
        
        st.write('##')
        
        # Initialize prompt in session state
        if "prompt" not in st.session_state:
            st.session_state["prompt"] = ""

        if st.button("Start Recording"):
                # Start recording audio
                fs = 44100  # Sample rate
                duration = 4 # Duration in seconds
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)

                # Wait for the recording to finish
                sd.wait()

                # Save the recorded audio to a WAV file
                wav_file = "audio.wav"
                sf.write(wav_file, recording, fs)


                # Convert the audio to text using Google Speech-to-Text API
                # Start the transcription
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_file) as source:
                    audio = recognizer.record(source)

                # Wait for the transcription to finish
                try:
                    transcribed_text = recognizer.recognize_google(audio, language="en-US")
                except sr.UnknownValueError:
                    print("Speech recognition failed")
                except sr.RequestError as e:
                    print("An error occurred: {}".format(e))
                text = recognizer.recognize_google(audio)
                
                tag_ = "Tag to track : "
                col = f"<span style='color: #007dff;'>{tag_}</span>"
                st.markdown(f"<h3>{col}</h3>", unsafe_allow_html=True)             
 		
                st.write(text)
                st.session_state["prompt"] = text  # Update the prompt value in session state


        if st.button("Start Scraping"):
            # Retrieve the prompt from session state
            prompt = st.session_state["prompt"]  
            if prompt:
            	
            	startStream()
                
    with right_column:
            # Charger l'animation Lottie
            animation_json = load_lottie_animation(lottie_url)

            # Afficher l'animation Lottie à l'aide de st_lottie
            if animation_json is not None:
                st_lottie(animation_json, height=300)
            else:
                st.error("Échec du chargement de l'animation Lottie.")        
