import sys, os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from queue import Queue
from src.HotWordSpotting import HotWordSpotting
from src.ReadAudio import ReadAudio
import pandas as pd

nfeat = []
q_l = []
seg_l = []
r_l = []
d_l = []
len_r = []
lab_l = []


recorder = ReadAudio()
hop_length = None
win_length = 0.5
nfft=4096
use_energy = False
norm = 'cmnperspk'

for n_feats in [5,6,7,8,9,10,11,12,13, 20]:
# for n_feats in [5, 9, 13, 20]:

  # query_dir = '/Users/burin/workspace/hotword_data/data/test_8k'
  query_dir = '/Users/burin/workspace/hotword_data/tuning/help' 
  references = []
  references += ['/Users/burin/workspace/hotword_data/tuning/others'] 
  # references += ["/Users/burin/workspace/hotword_data/Patient_Recordings_[20_Records]_8k"]

  spotter1 = HotWordSpotting(test_folder=references, 
      threshold=275, n_feats=n_feats, n_fft=nfft, hop_length=hop_length, win_length=win_length, norm=norm, use_energy=use_energy)    


  # for spk in [f"spk{str(num).zfill(3)}" for num in range(99,120)]:
  for spk in ['fair', 'hawan', 'mix', 'ta', 'krit', 'oong', 'top', 'ake']:

    if(not os.path.exists(f"{query_dir}/{spk}")):
      continue

    print(spk)
    queries = []
    for f in sorted(os.listdir(f"{query_dir}/{spk}")):
        if(f == '.DS_Store'): continue
        queries.append( os.path.join(f"{query_dir}/{spk}/{f}") )
    if(len(queries) == 0):
      continue

    spotter2 = HotWordSpotting(folder=f"{query_dir}/{spk}", 
      threshold=275, n_feats=n_feats, n_fft=nfft, hop_length=hop_length, win_length=win_length, norm=norm, use_energy=use_energy)


    ref_path = spotter1.ref_path
    ref_len = [r.shape[1] for r in spotter1.ref_lists]

    for query in queries:
      q = Queue()
      recorder(q, from_file=query, ret_format='float')
      
      seg = 0
      pos = 0
      while(not q.empty()):
        frame = q.get()
        found, dist, _ = spotter1(frame, return_dist=True) 
        for i, ref in enumerate(ref_path):
          nfeat.append(n_feats)
          q_l.append(query)
          seg_l.append(seg)
          r_l.append(ref)
          d_l.append(dist[i])
          len_r.append(ref_len[i])
          lab_l.append(pos)
          seg+=1

    
    ref_path = spotter2.ref_path
    ref_len = [r.shape[1] for r in spotter2.ref_lists ]   
    
    for query in queries:
      q = Queue()
      # print(query)
      recorder(q, from_file=query, ret_format='float')
      seg=0
      pos=1
      while(not q.empty()):
        frame = q.get()
        found, dist, _ = spotter2(frame, return_dist=True) 
        for i, ref in enumerate(ref_path):
          nfeat.append(n_feats)
          q_l.append(query)
          seg_l.append(seg)
          r_l.append(ref)
          d_l.append(dist[i])
          len_r.append(ref_len[i])
          lab_l.append(pos)
          seg+=1


pd.DataFrame({
  'nmfcc' : nfeat,
  'query' : q_l,
  'ref' : r_l,
  'seg_id' : seg_l,
  'dist' : d_l,
  'ref_len' : len_r,
  'label' : lab_l
}).to_csv('tune_cmnperspk_500ms_noc0.csv', index=False)

