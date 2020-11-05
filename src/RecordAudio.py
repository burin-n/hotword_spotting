import pyaudio
import librosa
import numpy as np
from datetime import datetime

class RecordAudio():
  
  def __init__(self):
    self.chunk = 1000  # Record in chunks of 1000 samples
    self.sample_format = pyaudio.paInt16  # 16 bits per sample
    self.channels = 1
    self.fs = 8000  # Record at 44100 samples per second
    self.seconds = 1.2
    self.overlap = 0.2 # in seconds
    self.overlap_size = int(self.fs / self.chunk * self.overlap)
    self.p = pyaudio.PyAudio()  # Create an interface to PortAudio


  def __call__(self, output_q, terminate=False, ret_format='float'):
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
                    input_device_index=0)
    frames = []
    # Store data in chunks for 1 seconds
    for i in range(0, int(self.fs / self.chunk * self.seconds)):
      data = self.stream.read(self.chunk)
      frames.append(data)
    time_end = datetime.now().__str__()

    frames_np = converter(b''.join(frames))
    if(terminate):
      packet = {
        'time_end': time_end,
        'data': frames_np 
      }
      output_q.put(packet)
      return
  
    while (True):
      # put streamed audio to output_q
      packet = {
        'time_end_record': time_end,
        'data': frames_np 
      }
      output_q.put(packet)
      #Initialize array to store frames
      frames = frames[-self.overlap_size:]
      # Store data in chunks for 1 seconds
      for i in range(0, int(self.fs / self.chunk * (self.seconds-self.overlap))):
        data = self.stream.read(self.chunk)
        frames.append(data)
      time_end = datetime.now().__str__()
      frames_np = converter(b''.join(frames))
      

    # Stop and close the stream 
    self.stream.stop_stream()
    self.stream.close()
    # Terminate the PortAudio interface
    self.p.terminate()
    print('Finished recording')


if __name__ == '__main__':
  
  from queue import Queue
  q = Queue()
  recorder = RecordAudio()
  recorder(q, terminate=True, ret_format='int')
  
  frames = []
  while(not q.empty()):
    packet = q.get()
    frames.append(packet['data'])
  import wave
  waveFile = wave.open('help_3.wav', 'wb')
  waveFile.setnchannels(recorder.channels)
  waveFile.setsampwidth(recorder.p.get_sample_size(recorder.sample_format))
  waveFile.setframerate(recorder.fs)
  waveFile.writeframes(b''.join(frames))
  waveFile.close()
