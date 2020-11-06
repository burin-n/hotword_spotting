import numpy as np
import librosa
from dtw import *
import pandas as pd
import time
import os

class HotWordSpotting():

  def __init__(self, index_file_path=None, folder=None, threshold=150, sf=8000, n_feats=5, n_fft=2048, no_mfcc0=False, cmn=True):
    r"""Index_file contains `path,trancsript` in csv format
    # cmn : apply ceptral mean normalization based on the global statistic of the speaker
    """
    self.sf = sf
    self.n_feats = n_feats
    self.threshold = threshold
    self.n_fft = n_fft
    self.no_mfcc0 = no_mfcc0
    self.cmn = cmn

    if(index_file_path != None):
      index_df = pd.read_csv(index_file_path)
      self.transcript = index_df['transcript'].to_list()
      self.ref_lists = self.load_references(index_df['path'].to_list())
    elif(folder != None):
      self.ref_name = [f for f in sorted(os.listdir(folder)) if f != '.DS_Store']
      self.ref_path = [os.path.join(folder, f) for f in self.ref_name]
      self.ref_lists = self.load_references(self.ref_path, self.cmn)
      print(self.ref_path)    
    else:
      raise NotImplementedError()
  

  def load_references(self, ref_paths, cmn=False):
    ref_lists = []
    if(cmn):
      stats = np.zeros(shape=(self.n_feats,)) 
      stats_len = 0
    
    for ref in ref_paths:
      sig, rate = librosa.load(ref, sr=self.sf)
      feats = librosa.feature.mfcc(sig, rate, n_mfcc=self.n_feats, n_fft=self.n_fft)
      ref_lists.append(feats)
      # print(feats.shape)
      if (cmn): 
        stats += feats.sum(axis=1)
        stats_len += feats.shape[1]
    
    if(cmn):
      self.spk_mean_stats = (stats/stats_len).reshape(-1,1)
      ref_lists = [feats-self.spk_mean_stats  for feats in ref_lists]
        
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
      parameters:
        X : query vector [n_timesteps,]
      returns:
        found, : int:[] indicate of matched references
        dists,    : folat:[1, .., len(ref)] distance for each of the reference
        self.ref_name :folat: [1, .., len(ref)] name of reference files
    """
    x = librosa.feature.mfcc(x, self.sf,  n_mfcc=self.n_feats, n_fft=self.n_fft)
    if(self.cmn):
      x -= self.spk_mean_stats

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
      return found, dists, self.ref_name
    else:
      return found
      

if __name__ == '__main__':
  spotter = HotWordSpotting(folder='tmp/references/cu63-test2', threshold=160, n_feats=5)
  quries = [
    'tmp/references/cu63-test2/help_1.wav'
  ]
  for q in quries:
    rec, rate = librosa.load(q, sr=8000)
    found, dist, _ = spotter(rec, return_dist=True) 
    print(found, dist)
  time.sleep(3)
  print()