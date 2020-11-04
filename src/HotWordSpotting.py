import numpy as np
import librosa
from dtw import *
import wave
import pandas as pd
import time
import os

class HotWordSpotting():

  def __init__(self, index_file_path=None, folder=None, threshold=4500, sf=8000, n_feats=13, n_fft=2048, no_mfcc0=False):
    r"""Index_file contains `path,trancsript` in csv format
    """
    self.sf = sf
    self.n_feats = n_feats
    self.threshold = threshold
    self.n_fft = n_fft
    self.no_mfcc0 = no_mfcc0

    if(index_file_path != None):
      index_df = pd.read_csv(index_file_path)
      self.transcript = index_df['transcript'].to_list()
      self.ref_lists = self.load_references(index_df['path'].to_list())
    elif(folder != None):
      self.ref_path = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f != '.DS_Store']
      self.ref_lists = self.load_references(self.ref_path)
      print(self.ref_path)    
    else:
      raise NotImplementedError()
  


  def load_references(self, ref_paths):
    ref_lists = []
    for ref in ref_paths:
      sig, rate = librosa.load(ref, sr=self.sf)
      feats = librosa.feature.mfcc(sig, rate, n_mfcc=self.n_feats, n_fft=1024)
      ref_lists.append(feats)
    return ref_lists


  def spotting(self, x, return_dist=False):
    # X : query matrix [n_feats, n_timesteps]
    dists = []
    for i, ref in enumerate(self.ref_lists):
      dist = self.multi_dim_dtw(x, ref)
      dists.append(dist)
    dists = np.array(dists)
    is_found = dists <= self.threshold
    if(return_dist):
      return is_found, dists
    else:
      return is_found


  def multi_dim_dtw(self, query, ref):
    sum_distance = 0
    for i in range(query.shape[0]):
      sum_distance += dtw(query[i], ref[i], step_pattern=symmetric2, \
        distance_only=True).distance / ref[i].shape[0]
    return sum_distance 


  def __call__(self, x, return_dist=False):
    """
      X : query vector [n_timesteps,]
    """
    x = librosa.feature.mfcc(x, self.sf,  n_mfcc=self.n_feats, n_fft=self.n_fft)
    if(self.no_mfcc0):
      x = x[1:]
  
    if(return_dist):
      is_found, dists = self.spotting(x, return_dist=return_dist)
    else:
      is_found = self.spotting(x)
    found = []
    for i, e in enumerate(is_found):
      if(e): found.append(i+1)

    if(return_dist):
      return found, dists
    else:
      return found


if __name__ == '__main__':
  # for n_feats in [1, 2, 3, 4, 5, 13, 15, 20]:
  for n_feats in [13]:
  # n_feats = 13
    spotter = HotWordSpotting(folder='data/references/spk000', threshold=5000, n_feats=n_feats)
    # spotter = HotWordSpotting(folder='data_8k/references/spk5/', threshold=5000)

    quries = [
      # 'data/query/spk1/help_3.wav',
      # 'data/query/spk1/help_4.wav',
      # 'data/query/spk1/hi_0.wav'
      'data_8k/query/spk5/22-help-1.wav',
      'data_8k/query/spk5/22-help-ouch-1.wav',
      'data_8k/references/spk5/22-help-2.wav',
      'data_8k/references/spk5/22-help-ouch-2.wav',
    ]
    print(f"=== n_feats: {n_feats}")
    for q in quries:
      rec, rate = librosa.load(q, sf=8000)
      print(q)
      found, dist = spotter(rec, return_dist=True) 
      print(found, dist)
    print()