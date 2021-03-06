import pyaudio
import librosa
import numpy as np
from datetime import datetime

class RecordAudio():
  
  def __init__(self, fs=8000, seconds=2, overlap=0.5, chuck=1000):
    self.chunk = chuck  # Record in chunks of 1000 samples
    self.sample_format = pyaudio.paInt16  # 16 bits per sample
    self.channels = 1
    self.fs = fs  # Record at 44100 samples per second
    self.seconds = seconds
    self.overlap = overlap # in seconds
    self.overlap_size = int(self.fs / self.chunk * self.overlap)
    self.p = pyaudio.PyAudio()  # Create an interface to PortAudio


  def __call__(self, output_q, buffer_list, is_terminate=[], terminate=False, ret_format='float'):
    if(ret_format == 'float'):
      converter = librosa.util.buf_to_float 
    elif(ret_format == 'int'):
      converter = lambda x : np.frombuffer(x, dtype=np.uint16)
    elif(ret_format == 'byte'):
      converter = lambda x : x
    else:
      raise NotImplementedError()

    print('Recoding...')
    self.stream = self.p.open(format=self.sample_format,
                    channels=self.channels,
                    rate=self.fs,
                    frames_per_buffer=self.chunk,
                    input=True,
                    input_device_index=None,
                    )
    
    
    index_start = 0
    index_start_5secs = 0
    index_end = index_start
    maximum_buffer = len(buffer_list)

    # Store data in chunks for 1 seconds
    for i in range(0, int(self.fs / self.chunk * self.seconds)):
      data = self.stream.read(self.chunk)
      buffer_list[index_end] = data
      index_end += 1
      

    index_start_5sec = index_end - int(self.fs / self.chunk * 5)
    # found init data, revert to start index
    if(index_start_5sec < 0 and buffer_list[index_start_5sec] == -1):
      index_start_5sec = 0

    time_end = datetime.now().__str__()
    if(terminate):
      packet = {
        'time_end_record': time_end,
        'index_start_5sec' : index_start_5sec,
        'index_start' : index_start,
        'index_end' : index_end,
        'sampling_rate' : self.fs
      }
      output_q.put(packet)
      return
  
    while (True):
      if(is_terminate[0] == 1):
        break
      # push task_q every 1 seconds chuck
      print('recoding..', datetime.now())
      index_start_5sec = index_end - int(self.fs / self.chunk * 5)
      # found init data, revert to start index
      if(index_start_5sec < 0 and buffer_list[index_start_5sec] == -1):
        index_start_5sec = 0

      packet = {
        'time_end_record': time_end,
        'index_start_5sec' : index_start_5sec,
        'index_start' : index_start,
        'index_end' : index_end,
        'sampling_rate' : self.fs
      }
      output_q.put(packet)


      index_start = ( index_start + int(self.fs / self.chunk * (self.seconds-self.overlap)) ) % maximum_buffer
      # Store data in chunks for 1 seconds
      for i in range(0, int(self.fs / self.chunk * (self.seconds-self.overlap))):
        data = self.stream.read(self.chunk)
        buffer_list[index_end] = data
        index_end = (index_end + 1) % maximum_buffer

      time_end = datetime.now().__str__()
      
    # Stop and close the stream 
    self.stream.stop_stream()
    self.stream.close()
    # Terminate the PortAudio interface
    self.p.terminate()
    print('recording exit')


def consume(record_buffer, start, end):
  if(start < 0 or end < start):
    print('!', start, end)
    data = record_buffer[start:] + record_buffer[:end]  
    print(len(data))
  else:
    data = record_buffer[start:end]

  return librosa.util.buf_to_float(b''.join(data))



if __name__ == '__main__':
  from queue import Queue
  import soundfile as sf
  maximum_buffer = 100
  

  tgt_folder = 'tune_data'

  for i in range(1,4):
    print('ช่วยด้วย', i)
    task_q = Queue()
    record_buffer = [-1 for _ in range(maximum_buffer)]
    recorder = RecordAudio(8000, seconds=2)
    recorder(task_q, record_buffer, terminate=True)
    
    while(not task_q.empty()):
      task = task_q.get()
      data = consume(record_buffer, task['index_start'], task['index_end'])
      sf.write(f'{tgt_folder}/help-{i}.wav', data, 8000, 'PCM_16')
    
  # words = ['น่ารัก', 'ฟุตบอล', 'ปวดหัว', 'พุทรา', 'รถไฟ', 'น้ำตก', 'เด็กชาย', 'รถยนต์', 'ดอกไม้', 'ยศศักดิ์', 'นกยูง', 'เอาใจ', 
  # 'จอดป้าย', 'ช้อนส้อม', 'ลูกเต๋า', 'ยุแหย่', 'พี่น้อง', 'เล็กน้อย', 'ชกมวย', 'พระพุทธ', 'วุ่นวาย', 'ปกครอง', 'ฝนตก', 'นักเรียน', 'มดแดง', 
  # 'งานบ้าน', 'เสื้อผ้า', 'พัดลม', 'เคราะห์ร้าย', 'พ่อแม่', 'ม้านั่ง', 'ไฟฟ้า', 'เท่ากัน', 'มะม่วง', 'นกแก้ว', 'กระต่าย']

  # for i in range(1,37):
  #   print(i, words[i-1])
  #   task_q = Queue()
  #   record_buffer = [-1 for _ in range(maximum_buffer)]
  #   recorder = RecordAudio(8000, seconds=2)
  #   recorder(task_q, record_buffer, terminate=True)
    
  #   while(not task_q.empty()):
  #     task = task_q.get()
  #     data = consume(record_buffer, task['index_start'], task['index_end'])
  #     sf.write(f'{tgt_folder}/test-{i}.wav', data, 8000, 'PCM_16')
    

