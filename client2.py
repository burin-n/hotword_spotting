import multiprocessing as mp
import time
import random
from src.HotWordSpotting import HotWordSpotting
from src.RecordAudio2 import RecordAudio
from src.ConnectStorage import download_references
import librosa
from datetime import datetime
import json
import pika
import pickle
import sys


def consume(record_buffer, start, end):
  if(start < 0 or end < start):
    print('!', start, end)
    data = record_buffer[start:] + record_buffer[:end]  
    print(len(data))
  else:
    data = record_buffer[start:end]

  return librosa.util.buf_to_float(b''.join(data))


def worker_handler(task_q, record_buffer, result_q, work):
  while(True):
    if(task_q.empty()):
      task = task_q.get()
      print(task)
      # consume data from circular list
      data = consume(record_buffer, task['index_start'], task['index_end'])
      result, dists = work(data, return_dist=True)
      result_packet = task.copy()
      result_packet['time_end_dtw'] = datetime.now().__str__()
      result_packet['results'] = result
      result_packet['dists'] = dists.tolist()
      result_packet['data'] = consume(record_buffer, task['index_start_5sec'], task['index_end']).tolist()
      result_q.put(result_packet)


def task_gen_handler(task_q, record_buffer, sf):
  recorder = RecordAudio(sf)
  recorder(task_q, record_buffer)


def singal_gen_handler(result_q, user_id, sf, server_config):
  if( 'pwd' in server_config):
    credentials = pika.PlainCredentials(server_config['user'], server_config['pwd'])
  else:
    credentials = pika.ConnectionParameters._DEFAULT
  parameters = pika.ConnectionParameters(server_config['host'],
                                        credentials=credentials)
  connection = pika.BlockingConnection(parameters)                                       
  channel = connection.channel()
  channel.queue_declare(queue=server_config['queue_name'])
  
  while(True):
    if(not result_q.empty()):
      result = result_q.get()
      print("{} {} {} {} {}".format(
        datetime.now().time(),
        result['time_end_record'], result['time_end_dtw'],
        result['results'], result['dists'],
      ))
      if(len(result['results']) > 0):
        packet = {
          'user_id' : user_id,
          'timestamp' : result['time_end_record'],
          'sound_data' : result['data'],
          'sampling_rate' : sf,
          'score' : min(result['dists']),
        }
        channel.basic_publish(exchange='', routing_key='hotword_spotting_result', body=json.dumps(packet),
          properties=pika.BasicProperties(delivery_mode = 2, # make message persistent
                      ))
  connection.close()


if __name__ == '__main__':
  mp.set_start_method('spawn')
  import argparse
  parser = argparse.ArgumentParser(description='Client for hotword detection service')
  parser.add_argument('user_id', help="cuYY-XXXXX : user_id should match the name of the container storing his references")
  parser.add_argument('--sf', type=int, default=8000, help='sampling frequency of to be recorded sound. This should match the sampling frequency of references')
  parser.add_argument('--nprocs', type=int, default=2, help='number of worker processes. This speed up the runtime when there are many references. (default=2)')
  parser.add_argument('--thresh', type=int, default=190, help='threshold for hotword spotting. A lower threshold would yeild more false positive.')
  parser.add_argument('--nfeats', type=int, default=6, help='number of mfcc features used in comparing between references sound and hypothesys sound')
  parser.add_argument('--nfft', type=int, default=2048, help='number of samples used for calculating fft')
  parser.add_argument('--max_buffer', type=int, default=50, help='size of the circular buffer that is used for storing recorded speech.')
  parser.add_argument('--tmp', type=str, default="tmp", help='location of downloaded references')
  args = parser.parse_args()
  print(args)


  with open('.env-test.json') as f:
    config = json.load(f)
    
  local_references_path = f"{args.tmp}/references/{args.user_id}"
  download_references(config['azure']['references_connection_str'], args.user_id, local_references_path)
  manager = mp.Manager()
  record_buffer = manager.list([-1 for _ in range(args.max_buffer)])
  task_q = manager.Queue() 
  result_q = manager.Queue()
  record_p = mp.Process(target=task_gen_handler, args=(task_q, record_buffer, args.sf))
  record_p.start()
  
  # n_fft = 1024
  # nfeat 5
  # fpr    tpr    threshold
  # 0.0486 0.6667 179.3669
  # 0.1111 0.6667 191.8449
  # n_fft = 2048
  # nfeat 6
  # fpr    tpr    threshold
  # 0.0486 0.8333 206.7914
  # 0.1042 0.8333 220.8565
  # no mfcc0
  # nfeat 5
  # 0.0208 0.8333 478.6751
  # 0.5903 0.8333 700.6847

  hotword_spotting = HotWordSpotting(folder=local_references_path, threshold=args.thresh, n_feats=args.nfeats, n_fft=args.nfft, sf=args.sf) 
  worker_p = [mp.Process(target=worker_handler, args=(task_q, record_buffer, result_q, hotword_spotting)) \
    for _ in range(args.nprocs)]
  for p in worker_p:
    p.start()
    
  signal_p = mp.Process(target=singal_gen_handler, args=(result_q, args.user_id, args.sf, config['rabbitmq']))
  signal_p.start()

  record_p.join()
  for p in worker_p:
    p.join()
  singal_p.join()
  manager.close()