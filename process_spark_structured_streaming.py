from pyspark.sql import functions as F
from pyspark.sql.functions import explode
from pyspark.sql.functions import split
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.ml.feature import Tokenizer, RegexTokenizer
import re
from textblob import TextBlob
from pyspark.sql.types import *
from deep_translator import GoogleTranslator 
import emoji
import time
from threading import Thread
from flask import Flask, render_template_string,render_template
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf

spark = SparkSession.builder \
    .appName("KafkaStructuredStreaming") \
    .getOrCreate()

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "taylor") \
    .load()



tweet_data_schema = StructType([
    StructField("created_at", StringType(), nullable=True),
    StructField("text", StringType(), nullable=True),
    StructField("retweet_count", StringType(), nullable=True),
    StructField("reply_count", StringType(), nullable=True),
    StructField("like_count", StringType(), nullable=True),
    StructField("quote_count", StringType(), nullable=True),
    StructField("impression_count", StringType(), nullable=True),
    StructField("lang", StringType(), nullable=True),
    StructField("user_name", StringType(), nullable=True),
    StructField("user_username", StringType(), nullable=True),
    StructField("user_location", StringType(), nullable=True),
    StructField("user_description", StringType(), nullable=True),
    StructField("user_followers_count", StringType(), nullable=True),
    StructField("user_following_count", StringType(), nullable=True),
    StructField("user_tweet_count", StringType(), nullable=True),
    StructField("user_listed_count", StringType(), nullable=True)
])

# Conversion de la colonne "value" en structure de données
df.printSchema()

df = df.selectExpr("CAST(value AS STRING)", "timestamp")

df = df\
        .select(from_json(col("value"), tweet_data_schema).alias("value_json"), "timestamp")

df = df.select("value_json.*")

# function for cleaning
def cleanTweet(tweet: str) -> str:


	
    # remove users
    tweet = re.sub('(RT\s@[A-Za-z]+[A-Za-z0-9-_]+)', '', str(tweet))
    tweet = re.sub('(@[A-Za-z]+[A-Za-z0-9-_]+)', '', str(tweet))
    
    # remove links
    tweet = re.sub(r'http\S+', '', str(tweet))
    tweet = re.sub(r'bit.ly/\S+', '', str(tweet))
    tweet = tweet.strip('[link]')

    # remove puntuation
    my_punctuation = '!"$%&\'()*+,-./:;<=>?[\\]^_`{|}~•@â'
    tweet = re.sub('[' + my_punctuation + ']+', ' ', str(tweet))
 
    # remove number
    tweet = re.sub('([0-9]+)', '', str(tweet))

    # remove hashtag
    tweet = re.sub('(#[A-Za-z]+[A-Za-z0-9-_]+)', '', str(tweet))
    
    # Remove emojis
    tweet = emoji.demojize(tweet)
    tweet = re.sub('(:[a-zA-Z_]+:)', '', tweet)
    
    # Traduction des tweets en anglais
    
    try:
        tweet = GoogleTranslator(source='auto', target='en').translate(tweet) 
    
    except Exception as e:
        print(f'Error translating tweet: {tweet}')
        print(e)
        return tweet
        

    return tweet




clean_tweets = F.udf(cleanTweet, StringType())

raw_tweets = df.withColumn('processed_text', clean_tweets(col("text")))

# Create a function to get the subjectifvity
def getSubjectivity(tweet: str) -> float:
    return TextBlob(tweet).sentiment.subjectivity


# Create a function to get the polarity
def getPolarity(tweet: str) -> float:
    return TextBlob(tweet).sentiment.polarity


def getSentiment(polarityValue: int) -> str:
    if polarityValue < 0:
        return 'Negative'
    elif polarityValue == 0:
        return 'Neutral'
    else:
        return 'Positive'
        
subjectivity = F.udf(getSubjectivity, FloatType())
polarity = F.udf(getPolarity, FloatType())
sentiment = F.udf(getSentiment, StringType())

subjectivity_tweets = raw_tweets.withColumn('subjectivity', subjectivity(col("processed_text")))
polarity_tweets = subjectivity_tweets.withColumn("polarity", polarity(col("processed_text")))
sentiment_tweets = polarity_tweets.withColumn("sentiment", sentiment(col("polarity")))


# Start the streaming query
query = sentiment_tweets.writeStream.outputMode("append").format("memory").queryName("sentiment_query").start()



# Create a flask app
app = Flask(__name__)

# Define the route for the streamlit_interface
@app.route("/")
def streamlit_interface():
    sentiment_df = spark.sql("SELECT * FROM sentiment_query")
    pandas_df = sentiment_df.toPandas()
    print(pandas_df)
    return render_template("index.html", data=pandas_df)



# Start the Flask app in a separate thread
def start_flask_app():
    app.run(port=5000)

# Start the Flask app thread
flask_thread = Thread(target=start_flask_app)
flask_thread.start()



# Wait for the query to terminate
query.awaitTermination()
