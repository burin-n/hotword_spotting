import pika
import json

with open('.env.json') as f:
    config = json.load(f)

credentials = pika.PlainCredentials(config['rabbitmq']['user'], config['rabbitmq']['pwd'])
parameters = pika.ConnectionParameters(config['rabbitmq']['host'],
                                    credentials=credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.queue_declare(queue=config['rabbitmq']['queue_name'])