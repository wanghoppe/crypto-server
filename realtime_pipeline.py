import pika
from tensorflow.keras.models import load_model
import numpy as np
import pandas as pd
import json
import requests
import datetime
import time
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.preprocessing import MaxAbsScaler

def price_to_return(df, target_col):
    # get price change
    s_test = df[target_col]
    log_return = np.log(s_test/s_test.shift())
    df['price change'] = log_return

    # feature extraction from OHLC
    # '''high/open'''
    df['high/open'] = np.log(df['high']/df['open'])
    # '''low/open'''
    df['low/open'] = np.log(df['low']/df['open'])
    # '''close/high'''
    df['close/high'] = np.log(df['close']/df['high'])
    # '''close/low'''
    df['close/low'] = np.log(df['close']/df['low'])
    df = df.drop(['close','high','low','open','volumefrom'],axis=1)
    df.rename(columns = {'volumeto':'volumn'},inplace=True)
    df = df.dropna()
    return df

def get_ticker_sentiment(df,news):
    holder = []
    for i in range(df.shape[0]):
        to_t = df.time[i]
        from_t = to_t - 86400
        news_interval = news[(news['published_on'] >= from_t) & (news['published_on'] <= to_t)]
        score = news_interval.mean()[-4:]
        score['time'] = to_t
        holder.append(score)
    score_df = pd.concat(holder,axis=1).T
    score_df['time'] = score_df['time'].apply(int)
    complete_df = pd.merge(df, score_df, on = 'time')
    return complete_df

def get_ticker_social(df,coin_social):
    coin_social = coin_social.pct_change()
    coin_social = coin_social.add(1)
    coin_social = np.log(coin_social)
    coin_social = coin_social.reset_index()
    complete_df = pd.merge(df,coin_social,on='time', how = 'inner')
    return complete_df

def time_series_to_supervised(df,sequence_length):
    
    '''for real time pipeline, we don't need label, i.e. actual y, so when we do indexing
    , we use "index+1 : index + sequence"
    '''
    temp = df.values
    temp = temp.tolist()
        
    result = []
    for index in range(len(temp) - sequence_length +1):
        result.append(temp[index +1: index + sequence_length])
    data = np.array(result)

    # get x and y
    x = data
        
    return x

def data_preparation(coin, coinID, time_period, time_frequency, agg, apiKey, cat, lang, ticker_num, sequence_length):
    

    def get_news_data_spec(cat, timestamp, apiKey, lang):
        news_url = "https://min-api.cryptocompare.com/data/v2/news/?categories={}&lang={}&lTs={}&api_key={}".format(cat, lang, timestamp ,apiKey)        
        r = requests.get(news_url)
        ipdata = r.json()
        return ipdata

    # get current time
    timestamp = int(time.time())
    
    prediction_length = ticker_num + sequence_length -1
    
    # APIs
    price_url = "https://min-api.cryptocompare.com/data/{}?fsym={}&tsym=USD&limit={}&toTs={}&api_key={}".format(time_period, coin, prediction_length, timestamp,apiKey)
    
    social_url = "https://min-api.cryptocompare.com/data/social/coin/histo/{}?coinId={}&aggregate={}&limit={}&toTs={}&api_key={}"\
        .format(time_frequency, coinID, agg, prediction_length, timestamp ,apiKey)
    

    # get data
    price = requests.get(price_url).json()
    social = requests.get(social_url).json()
    
    # deal with price
    price_df = pd.DataFrame(price['Data'])
    price_benchmark = price_df['close'][sequence_length-1]
    timestamp_benchmark = price_df['time'][sequence_length-1:]
    price_df['date/hour'] = pd.to_datetime(price_df['time'], unit='s') 
    price_df.set_index('date/hour', inplace=True)
    return_df = price_to_return(price_df,'close')
    
    # deal with news
    news_ts = timestamp
    from_t = news_ts - (prediction_length * 3600) - 86400
    holder = []
    while news_ts > from_t:
        news_data = get_news_data_spec(cat, news_ts, apiKey, lang)
        news_df = pd.DataFrame(news_data['Data'])
        holder.append(news_df)
        news_ts = news_df['published_on'].min()        
    df = pd.concat(holder, axis = 0)
    df = df[df['published_on']>from_t]
    df['time'] = df['published_on'].apply(lambda x: datetime.datetime.fromtimestamp(x).strftime("%Y-%m-%d"))
    news = df.set_index('time')
    # get news sentiment
    news['news_content'] = news['title'] + news['body']
    news['vader_polarity'] = news['news_content'].apply(lambda x: sia.polarity_scores(x))
    news['vader_compound'] = news['vader_polarity'].apply(lambda x: x['compound'])
    news['vader_neg'] = news['vader_polarity'].apply(lambda x: x['neg'])
    news['vader_neu'] = news['vader_polarity'].apply(lambda x: x['neu'])
    news['vader_pos'] = news['vader_polarity'].apply(lambda x: x['pos'])
    news = news[['id','published_on','vader_compound','vader_neg','vader_neu','vader_pos']]
    return_news_df = get_ticker_sentiment(return_df, news)
    
    # deal with social
    social_df = pd.DataFrame(social['Data'])
    social_df.set_index('time',inplace = True)
    coin_complete = get_ticker_social(return_news_df,social_df)
    
    # complete df
    coin_complete['time'] = pd.to_datetime(coin_complete['time'], unit='s')
    coin_complete['time'] = coin_complete['time'].dt.strftime('%Y-%m-%d %r')
    coin_complete.set_index('time', inplace=True)
    
    return price_benchmark, timestamp_benchmark, coin_complete

def pipeline(coin_complete, sequence_length, model):
    
    coin_complete = coin_complete.replace([np.inf, -np.inf], np.nan)
    coin_complete = coin_complete.fillna(0)
    
    # scale data
    max_abs_scaler = MaxAbsScaler()
    temp = max_abs_scaler.fit_transform(coin_complete)
    temp = pd.DataFrame(temp,columns=coin_complete.columns)
    coin_complete = temp.set_index(coin_complete.index)
    
    x = time_series_to_supervised(coin_complete, sequence_length)
    
    y_predict = model.predict(x)
    
    # inverse scaler
    y_predict_inverse = y_predict * max_abs_scaler.scale_[1]
    
    return y_predict, y_predict_inverse

def denormalized_to_actual_price(y_predict_inverse, price_benchmark, timestamp_benchmark):
    
    # log return to simple return
    predict_simple = np.exp(y_predict_inverse)
    #actual_simple = np.exp(y_actual_inverse)
    
    # get real price
    predict_simple = np.insert(predict_simple, 0, price_benchmark)
    predict_price = predict_simple.cumprod()[1:]
    #actual_simple = np.insert(actual_simple, 0, price_benchmark)
    #actual_price = actual_simple.cumprod()[1:]
    
    # get timestamp
    timestamp_benchmark = timestamp_benchmark[1:]
    timestamp_benchmark = timestamp_benchmark + 3600
    
    # zip
    predict_price = list(zip(timestamp_benchmark, predict_price))
    #actual_price = list(zip(timestamp_benchmark, actual_price))
    
    return predict_price

if __name__ == '__main__':

    # credentials
    cred = pika.credentials.PlainCredentials('hwa125', '960923')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='ec2-3-19-67-238.us-east-2.compute.amazonaws.com', credentials=cred))
    channel = connection.channel()

    channel.queue_declare(queue='predict-24')

    # load model
    #nltk.download('vader_lexicon')
    sia = SentimentIntensityAnalyzer()
    coin_model = load_model('coin_model_1.h5')

    # # parameters
    sequence_length = 50
    ticker_num = 24
    coin = 'BTC'
    coinID = '1182'
    timeperiod = 'histohour'
    timefrequency = 'hour'
    agg = 1
    apiKey = 'bf7c04a024b244dea99e95798fa8e102b7c9738c0933795253c2c8f39f2d160c'
    cat = 'BTC'
    lang = 'EN'

    while True:

        print ('start to get coin data')
        # get coin data
        price_benchmark, timestamp_benchmark, coin_complete = data_preparation(
            coin, coinID, timeperiod, timefrequency, agg, apiKey, cat, lang, ticker_num, sequence_length)
        
        print ('start to get prediction price')
        # get prediction
        y_predict, y_predict_inverse = pipeline(coin_complete, sequence_length, coin_model)

        print ('start to transform return to actual coin price')
        # denormalize
        predict_price = denormalized_to_actual_price(y_predict_inverse, price_benchmark, timestamp_benchmark)
        print (predict_price)
        predict_price = [[i[0]*1000, float(i[1])] for i in predict_price]

        print ('--------------publish---------------')
        # publish data
        channel.basic_publish(exchange='', routing_key='predict-24', body=json.dumps(predict_price))
        
        # sleep
        latest_ts = timestamp_benchmark[ticker_num+sequence_length-1]
        print ('latest timestamp is', latest_ts)
        ts_now = time.time()
        print ('current timestamp is', ts_now)
        wait_second = 3600 - (ts_now - latest_ts)
        print ('wait second is', wait_second)
        time.sleep(wait_second + 120)

