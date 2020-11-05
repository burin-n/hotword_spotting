import pyaudio
import librosa
import numpy as np
import wave

class ReadAudio():
  
  def __init__(self):
    self.chunk = 1000  # Record in chunks of 1000 samples
    self.sample_format = pyaudio.paInt16  # 16 bits per sample
    self.channels = 1
    self.fs = 8000  # Record at 44100 samples per second
    self.seconds = 1.2
    self.overlap = 0.2 # in seconds
    self.overlap_size = int(self.fs / self.chunk * self.overlap)


  def __call__(self, output_q, from_file, ret_format='float'):
    if(ret_format == 'float'):
      converter = librosa.util.buf_to_float 
    elif(ret_format == 'int'):
      converter = lambda x : np.frombuffer(x, dtype=np.uint16)
    elif(ret_format == 'byte'):
      converter = lambda x : x
    else:
      raise NotImplementedError()

    print('Streaming...')
    f = wave.open(from_file, 'rb')

    frames = []
    # Store data in chunks for 1 seconds
    for i in range(0, int(self.fs / self.chunk * self.seconds)):
      data = f.readframes(self.chunk)
      frames.append(data)
    frames_np = converter(b''.join(frames))
    
    terminate = False

    while (not terminate):
      # put streamed audio to output_q
      output_q.put(frames_np)
      # Initialize array to store frames
      frames = frames[-self.overlap_size:]
      # Store data in chunks for 1 seconds
      for i in range(0, int(self.fs / self.chunk * (self.seconds-self.overlap))):
        data = f.readframes(self.chunk)
        if(data == b''):
          terminate = True
        else:
          frames.append(data)
      frames_np = converter(b''.join(frames))
    
    f.close()


if __name__ == '__main__':

  from queue import Queue
  from HotWordSpotting import HotWordSpotting
  recorder = ReadAudio()
  
  n_feats = 13
  spotter = HotWordSpotting(folder='data/references/spk099/', threshold=15000,  n_feats=n_feats)
  # spotter = HotWordSpotting(folder='data_8k/references/spk5/', threshold=15000,  n_feats=n_feats)
  
  quries = [
    'data/queries/spk009/099-help-1.wav',
  ]

  print(f"=== n_feats: {n_feats}")
  for query in quries:
    q = Queue()
    print(query)
    recorder(q, from_file=query, ret_format='float')
    
    while(not q.empty()):
      frame = q.get()
      found, dist = spotter(frame, return_dist=True) 
      print(found, dist)
    
print()

  # ref = "data/queries/spk009/099-help-1.wav"
  # sig, rate = librosa.load(ref, sr=8000)

  # frames = []
  # with wave.open(ref , 'rb') as f:
  #     data = f.readframes(1000)
  #     while(data != b''):
  #       frames.append(data)
  #       data = f.readframes(1000)
  
  # converter = lambda x : np.frombuffer(x, dtype=np.uint16)
  # converter = librosa.util.buf_to_float 
  # frames_np = converter(b''.join(frames))
  # print('end')