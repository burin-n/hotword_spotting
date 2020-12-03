import pika, sys, os
import json
from datetime import datetime
import numpy as np
from scipy.io.wavfile import write


def main(host):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    # define name of the message queue
    channel.queue_declare(queue='hotword_spotting_result')
    # process data
    def callback(ch, method, properties, body):
        body_dict = json.loads(body.decode())
        print(body_dict.keys())
        
        print(" [{}] Received {} {} {} {}".format(body_dict['user_id'], body_dict['timestamp'], body_dict['sampling_rate'],
            body_dict['score'], np.asarray(body_dict['sound_data']).shape))
        write('out_2.wav', body_dict['sampling_rate'], np.asarray(body_dict['sound_data']))
    channel.basic_consume(queue='hotword_spotting_result', on_message_callback=callback, auto_ack=True)
    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == '__main__':
    try:
        main(host='localhost')
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)