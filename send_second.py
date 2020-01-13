import pika
import json
import numpy as np
import time
import datetime as dt

cred = pika.credentials.PlainCredentials('hwa125', '960923')
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='ec2-3-19-67-238.us-east-2.compute.amazonaws.com', credentials=cred))
channel = connection.channel()

channel.queue_declare(queue='predict-second')


d = dt.datetime.now()
d2 = dt.datetime(d.year, d.month, d.day, d.hour, d.second)

first = int(d2.timestamp()- 30)*1000

lst_act = []
lst_pre = []
for i in range(30):
    lst_act.append([first + i*1000, None])
    lst_pre.append([first + 1000 + i*1000, None])

while True:

    lst_act.append([lst_act[-1][0] + 1000, np.random.rand()])
    lst_act.pop(0)

    lst_pre.append([lst_pre[-1][0] + 1000, np.random.rand()])
    lst_pre.pop(0)

    msg = {'act':lst_act, 'pre':lst_pre}
    channel.basic_publish(exchange='', routing_key='predict-second', body=json.dumps(msg))
    time.sleep(1)
    print(msg)
