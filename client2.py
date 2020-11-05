import multiprocessing as mp
import time
import random
from src.HotWordSpotting import HotWordSpotting
from src.RecordAudio2 import RecordAudio
from src.Storage import Storage
import librosa
from datetime import datetime
import json
import pika
import pickle
import sys
import signal

def consume(record_buffer, start, end):
  if(start < 0 or end < start):
    # print('!', start, end)
    data = record_buffer[start:] + record_buffer[:end]  
    # print(len(data))
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
      result, dists, ref_name = work(data, return_dist=True)
      result_packet = task.copy()
      result_packet['time_end_dtw'] = datetime.now().__str__()
      result_packet['results'] = result
      result_packet['dists'] = dists.tolist()
      result_packet['data'] = consume(record_buffer, task['index_start_5sec'], task['index_end']).tolist()
      result_packet['ref_name'] = ref_name
      result_q.put(result_packet)


def task_gen_handler(task_q, record_buffer, sf):
  recorder = RecordAudio(sf)
  recorder(task_q, record_buffer)


def singal_gen_handler(result_q, user_id, qserver_config, backup_q=None):
  if( 'pwd' in qserver_config):
    credentials = pika.PlainCredentials(qserver_config['user'], qserver_config['pwd'])
  else:
    credentials = pika.ConnectionParameters._DEFAULT
  parameters = pika.ConnectionParameters(qserver_config['host'],
                                        credentials=credentials)
  connection = pika.BlockingConnection(parameters)                            
  channel = connection.channel()
  channel.queue_declare(queue=qserver_config['queue_name'])
  
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
          'sampling_rate' : result['sampling_rate'],
          'score' : min(result['dists']),
        }
        channel.basic_publish(exchange='', routing_key=qserver_config['queue_name'], body=json.dumps(packet),
          properties=pika.BasicProperties(delivery_mode = 2, # make message persistent
                      ))
        if(backup_q != None):
          backup_q.put(result)
          
  connection.close()


def backup_handler(backup_q, storage):
  while(True):
    if(not backup_q.empty()):
      result = backup_q.get()
      storage.backup(result)



def signal_handler(sig, frame):
  print('terminating threads')
  # closing
  record_p.join()
  for p in worker_p:
    p.join()
  signal_p.join()
  if(backup_q != None):
    backup_p.join()
  # manager.close()
  sys.exit(0)


if __name__ == '__main__':
  mp.set_start_method('spawn')
  import argparse
  parser = argparse.ArgumentParser(description='Client for hotword detection service')
  parser.add_argument('user_id', help="cuYY-XXXXX : user_id should match the name of the container storing his references")
  parser.add_argument('--sf', type=int, default=8000, help='sampling frequency of to be recorded sound. This should match the sampling frequency of references')
  parser.add_argument('--nprocs', type=int, default=2, help='number of worker processes. This speed up the runtime when there are many references. (default=2)')
  parser.add_argument('--thresh', type=int, default=120, help='threshold for hotword spotting. A lower threshold would yeild more false positive.')
  parser.add_argument('--nfeats', type=int, default=5, help='number of mfcc features used in comparing between references sound and hypothesys sound')
  parser.add_argument('--nfft', type=int, default=1024, help='number of samples used for calculating fft')
  parser.add_argument('--cmn', type=bool, default=True, help='apply speaker-based ceptral mean normalization')
  parser.add_argument('--max_buffer', type=int, default=50, help='size of the circular buffer that is used for storing recorded speech.')
  parser.add_argument('--tmp', type=str, default="tmp", help='location of downloaded references')
  args = parser.parse_args()
  print(args)


  with open('.env-test.json') as f:
    config = json.load(f)
    
  storage = Storage(args.user_id, config['azure']['references_connection_str'], config['azure'].get('hypothesis_connection_str', None), tmp_dir=args.tmp)
  storage.download_references()

  manager = mp.Manager()
  record_buffer = manager.list([-1 for _ in range(args.max_buffer)])
  task_q = manager.Queue() 
  result_q = manager.Queue()
  if(config['azure'].get('hypothesis_connection_str', None) != None):
    backup_q = manager.Queue()
  else:
    backup_q = None

  record_p = mp.Process(target=task_gen_handler, args=(task_q, record_buffer, args.sf))
  record_p.start()
  
  # cmn nftt=2048
  # nfeat=5
  # fpr    tpr    threshold
  # 0.0208 0.3333 148.6144
  # 0.0347 0.8333 164.4070
  # nfeat 13
  # fpr___ tpr___ threshold
  # 0.0278 0.5000 248.4595
  # 0.0486 1.0000 259.5595

  # cmn nfft=1024
  # nfeat=5
  # fpr___ tpr___ threshold
  # 0.0208 0.1667 156.5786
  # 0.0486 0.1667 170.4910
  # nfeat 13
  # fpr___ tpr___ threshold
  # 0.0208 0.3333 255.0371
  # 0.1250 0.3333 289.3839
  local_references_path = f"{args.tmp}/references/{args.user_id}"

  if(backup_q != None):
    backup_p = mp.Process(target=backup_handler, args=(backup_q, storage))
    backup_p.start()

  hotword_spotting = HotWordSpotting(folder=local_references_path, threshold=args.thresh, n_feats=args.nfeats, n_fft=args.nfft, sf=args.sf, cmn=args.cmn)
  worker_p = [mp.Process(target=worker_handler, args=(task_q, record_buffer, result_q, hotword_spotting)) \
    for _ in range(args.nprocs)]
  for p in worker_p:
    p.start()
  
  signal_p = mp.Process(target=singal_gen_handler, args=(result_q, args.user_id, config['rabbitmq'], backup_q))
  signal_p.start()

  
  signal.signal(signal.SIGINT, signal_handler)
  signal.pause()


  # # closing
  # record_p.join()
  # for p in worker_p:
  #   p.join()
  # signal_p.join()
  # backup_p.join()
  # manager.close()