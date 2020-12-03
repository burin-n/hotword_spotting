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
import os


# we will check for this file to exit the program.
# the file will be deleted afterwards.
kill_file = 'terminate.log'


def detect_termination(is_terminate):
  if(os.path.exists(kill_file)):
    os.remove(kill_file)
    is_terminate[0] = 1


def consume(record_buffer, start, end):
  if(start < 0 or end < start):
    data = record_buffer[start:] + record_buffer[:end]  
  else:
    data = record_buffer[start:end]
  return librosa.util.buf_to_float(b''.join(data))


def worker_handler(task_q, record_buffer, result_q, work, is_terminate):
  
  i=0 # just a counter to slow down the process
  while(True):
    if(not task_q.empty()):
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

    i+=1
    if(i%100000 == 0):
      print(f'### worker {datetime.now()}')
      i=0
      detect_termination(is_terminate)
      if(is_terminate[0] == 1):
        break
  print('hotword worker exit')


def task_gen_handler(task_q, record_buffer, sf, is_terminate):
  recorder = RecordAudio(sf)
  recorder(task_q, record_buffer, is_terminate)
  print('task gen exit')


def singal_gen_handler(result_q, user_id, qserver_config, is_terminate, backup_q=None):
  if( 'pwd' in qserver_config):
    credentials = pika.PlainCredentials(qserver_config['user'], qserver_config['pwd'])
  else:
    credentials = pika.ConnectionParameters._DEFAULT
  parameters = pika.ConnectionParameters(qserver_config['host'],
                                        credentials=credentials)
  connection = pika.BlockingConnection(parameters)                            
  channel = connection.channel()
  channel.queue_declare(queue=qserver_config['queue_name'])

  logfile = open('worker.log', 'a')
  print('##############', file=logfile, flush=True)

  i = 0
  while(True):
    if(not result_q.empty()):
      i += 1
      if(i%100000 == 0):
        print(f'### siggen {datetime.now()}')
        if(is_terminate[0] == 1):
          break
        i=0

      result = result_q.get()
      log_string = "{} {} {} {} {}".format(
        datetime.now().time(),
        result['time_end_record'], result['time_end_dtw'],
        result['results'], result['dists'],
      )

      print(log_string, file=logfile, flush=True)
      print(log_string, flush=True)

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
  
    if(i%100000 == 0):
      if(is_terminate[0] == 1):
        break
    i += 1 
    
  print('sig gen exit!!!')


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
  # mp.set_start_method('spawn')
  import argparse
  parser = argparse.ArgumentParser(description='Client for hotword detection service')
  parser.add_argument('user_id', help="cuYY-XXXXX : user_id should match the name of the container storing his references")
  parser.add_argument('--sf', type=int, default=8000, help='sampling frequency of to be recorded sound. This should match the sampling frequency of references')
  parser.add_argument('--nprocs', type=int, default=1, help='number of worker processes. This speed up the runtime when there are many references. (default=2)')
  parser.add_argument('--thresh', type=int, default=100, help='threshold for hotword spotting. A lower threshold would yeild more false positive.')
  parser.add_argument('--nfeats', type=int, default=9, help='number of mfcc features used in comparing between references sound and hypothesys sound')
  parser.add_argument('--nfft', type=int, default=None, help='number of samples used for calculating fft')
  parser.add_argument('--win_length', type=int, default=0.5, help='window size for fft in ms')
  parser.add_argument('--hop_length', type=int, default=None, help='hop size for fft in ms')
  parser.add_argument('--norm', type=str, default='cmnperspk', help='apply speaker-based ceptral mean normalization')
  parser.add_argument('--use_energy', type=bool, default=False, help='use mfcc0 or not')
  parser.add_argument('--max_buffer', type=int, default=500, help='size of the circular buffer that is used for storing recorded speech. (500 ~ 1 min buffer for 8k audio)')
  parser.add_argument('--tmp', type=str, default="tmp", help='location of downloaded references')
  parser.add_argument('--env', type=str, default='env.json', help='localtion of environment file')
  args = parser.parse_args()
  print(args)

  # clean dump files
  if(os.path.exists('start.done')):
    os.remove('start.done')
  if(os.path.exists(kill_file)):
    os.remove(kill_file)

  with open('start.progress', 'w'):
    pass

  with open(args.env) as f:
    config = json.load(f)
  user_id = args.user_id.lower()
  storage = Storage(user_id, config['azure']['references_connection_str'], config['azure'].get('hypothesis_connection_str', None), tmp_dir=args.tmp)
  storage.download_references()

  manager = mp.Manager()
  record_buffer = manager.list([-1 for _ in range(args.max_buffer)])
  is_terminate = manager.list([0])
  task_q = manager.Queue() 
  result_q = manager.Queue()
  if(config['azure'].get('hypothesis_connection_str', None) != None):
    backup_q = manager.Queue()
  else:
    backup_q = None

  record_p = mp.Process(target=task_gen_handler, args=(task_q, record_buffer, args.sf, is_terminate))
  record_p.start()
  local_references_path = f"{args.tmp}/references/{user_id}"

  if(backup_q != None):
    backup_p = mp.Process(target=backup_handler, args=(backup_q, storage))
    backup_p.start()

  # automaticly fine the nfft that fits the win_length
  if(args.nfft == None):
    args.nfft = 2
    while(args.nfft < args.win_length * args.sf):
      args.nfft *= 2
    
  hotword_spotting = HotWordSpotting(folder=local_references_path, threshold=args.thresh, n_feats=args.nfeats, n_fft=args.nfft, sf=args.sf, norm=args.norm,\
                                win_length=args.win_length, hop_length=args.hop_length, use_energy=args.use_energy)
  
  worker_p = [mp.Process(target=worker_handler, args=(task_q, record_buffer, result_q, hotword_spotting, is_terminate)) \
    for _ in range(args.nprocs)]
  for p in worker_p:
    p.start()

  signal_p = mp.Process(target=singal_gen_handler, args=(result_q, user_id, config['rabbitmq'], is_terminate, backup_q))
  signal_p.start()
  

  # closing
  os.remove('start.progress')
  with open('start.done', 'w') as f:
    pass
  
  for p in worker_p:
    p.join()
  signal_p.join()
  # backup_p.join()
  record_p.join()