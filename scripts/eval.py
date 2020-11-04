from queue import Queue
from src.HotWordSpotting import HotWordSpotting
from src.ReadAudio import ReadAudio
import os
import pandas as pd

nfeat = []
q_l = []
seg_l = []
r_l = []
d_l = []
len_r = []
lab_l = []


recorder = ReadAudio()

for n_feats in range(1,14): #[1,2,3,4,5,6,7,8,9,10,11,12,13]:

  data_dir = 'data/references'
  # for spk in sorted(os.listdir(data_dir)):
  for spk in ["spk099", "spk100", "spk101", "spk102"]:
    if(spk == '.DS_Store'): continue

    spotter = HotWordSpotting(folder=f'{data_dir}/{spk}', threshold=275,  n_feats=n_feats)

    ref_path = spotter.ref_path
    ref_len = [r.shape[1] for r in spotter.ref_lists ]

    queries = []
    for f in sorted(os.listdir(f"data/queries/{spk}")):
        if(f == '.DS_Store'): continue
        queries.append( os.path.join(f"data/queries/{spk}/{f}") )


    for query in queries:
      q = Queue()
      recorder(q, from_file=query, ret_format='float')
      
      seg=0
      while(not q.empty()):
        frame = q.get()
        found, dist = spotter(frame, return_dist=True) 
        pos = []
        for i, ref in enumerate(ref_path):
          if('help' in ref):
            pos = 1
          else:
            pos = 0
        
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
  'seg_id' : seg,
  'dist' : d_l,
  'ref_len' : len_r,
  'label' : lab_l
}).to_csv('score.csv', index=False)

