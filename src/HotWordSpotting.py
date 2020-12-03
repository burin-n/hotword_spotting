import numpy as np
import librosa
from dtw import *
import pandas as pd
import time
import os
import json

class HotWordSpotting():

  def __init__(self, index_file_path=None, folder=None, threshold=150, sf=8000, n_feats=5, n_fft=2048, use_energy=False, 
    norm="cmnperspk", sensitivity_scale_step = 20, test_folder = None, hop_length=0.01, win_length=0.025):
    r"""Index_file contains `path,trancsript` in csv format
    # norm : ['no', 'cmnperspk', 'cmnperutt']
    """
    self.sf = sf
    self.n_feats = n_feats
    self.threshold = threshold
    self.n_fft = n_fft
    if(hop_length != None):
      self.hop_length = int(hop_length * sf)
    else:
      self.hop_length = hop_length
    if(win_length != None):
      self.win_length = int(win_length * sf)
    else:
      self.win_length = win_length
    self.use_energy = use_energy
    self.norm = norm
    assert self.norm in ['no', 'cmnperspk', 'cmnperutt', 'movavg']

    if(index_file_path != None):
      index_df = pd.read_csv(index_file_path)
      self.transcript = index_df['transcript'].to_list()
      self.ref_lists = self.load_references(index_df['path'].to_list())

    elif(test_folder != None):
      self.ref_path = []
      if(type(test_folder) == str):
        test_folder = [test_folder]
      for tfolder in test_folder:
        self.ref_name = []
        for folder in os.listdir(tfolder):
          if(folder != ".DS_Store"):
            self.ref_name.extend([f"{folder}/{f}" for f in sorted(os.listdir(f"{tfolder}/{folder}")) if f.endswith('.wav')])
        self.ref_path.extend([os.path.join(tfolder, f) for f in self.ref_name])
      self.ref_lists = self.load_references(self.ref_path)
      print('size of ref', len(self.ref_path))

    elif(folder != None):
      self.ref_name = [f for f in sorted(os.listdir(folder)) if f.endswith('.wav')]
      self.ref_path = [os.path.join(folder, f) for f in self.ref_name]
      self.ref_lists = self.load_references(self.ref_path)
      # print(self.ref_path)
      
      sensitivity_file = 'environmental_sensitivity.json'
      if(sensitivity_file in os.listdir(folder)):
        #sens = json.load(open(sensitivity_file))
        with open(os.path.join(folder, sensitivity_file)) as f:
          sens = int(f.readlines()[0].split(':')[-1][:-1])
          scale = sens - 3
        self.threshold += scale * sensitivity_scale_step    

    else:
      raise NotImplementedError()

    print("######## threshold: {} n_feats:{} n_fft:{} hop_length:{} win_length:{} use_energy:{} norm:{}\n".format(
      self.threshold, self.n_feats, self.n_fft, self.hop_length, self.win_length, self.use_energy, self.norm))


  def normalize(self, x):
    if (self.norm == 'cmnperutt'):
      x -= x.mean(axis=1).reshape(-1,1)
    elif(self.norm == 'cmnperspk'):
      x -= self.spk_mean_stats
    return x


  def load_references(self, ref_paths):
    ref_lists = []

    if(self.norm == 'cmnperspk'):
      if(not self.use_energy):
        stats = np.zeros(shape=(self.n_feats-1,)) 
      else:
        stats = np.zeros(shape=(self.n_feats,)) 
      stats_len = 0
    
    for ref in ref_paths:
      sig, rate = librosa.load(ref, sr=self.sf)
      sig = sig[-self.sf*2:]
      feats = librosa.feature.mfcc(sig, rate, n_mfcc=self.n_feats, 
                      n_fft=self.n_fft, hop_length=self.hop_length, win_length=self.win_length)

      if(not self.use_energy):
        feats = feats[1:]

      if(self.norm == 'cmnperutt'):
        feats = self.normalize(feats)
      elif(self.norm == 'cmnperspk'):
        stats += feats.sum(axis=1)
        stats_len += feats.shape[1]

      ref_lists.append(feats)
        
    if(self.norm == 'cmnperspk'):
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
    x = librosa.feature.mfcc(x, self.sf,  n_mfcc=self.n_feats, win_length=self.win_length, hop_length=self.hop_length, n_fft=self.n_fft)
    #x = librosa.feature.mfcc(x, self.sf,  n_mfcc=self.n_feats, n_fft=self.n_fft)

    if(not self.use_energy):
      x = x[1:]
    x = self.normalize(x)

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
  spotter = HotWordSpotting(folder='tmp/references/test-0001/', threshold=160,  n_feats=20, sf=8000, norm="cmnperspk",
    n_fft=2048, hop_length=None, win_length=None)
  quries = [
    'tmp/references/test-0001/help-1.wav'
  ]
  for q in quries:
    rec, rate = librosa.load(q, sr=8000)
    found, dist, _ = spotter(rec, return_dist=True) 
    print(found, dist)
  time.sleep(3)
  print()