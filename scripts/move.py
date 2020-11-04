import os
folder="data_8k"
q_folder="data/queries"
r_folder="data/references"

for spk in os.listdir(folder):
    if(spk == ".DS_Store"):
        continue

    qout = f"{q_folder}/{spk}"
    rout = f"{r_folder}/{spk}"
    
    if(not os.path.exists(qout)):
        os.makedirs(qout)
    if(not os.path.exists(rout)):
        os.makedirs(rout) 

    for f in os.listdir(f"{folder}/{spk}"):
        if('help-' in f or 'ouch-' in f):
            if (f[-5:] == '1.wav'):
                os.rename(os.path.join(folder, spk, f), os.path.join(qout, f))
            else:
                os.rename(os.path.join(folder, spk, f), os.path.join(rout, f))


# for spk in os.listdir(folder):
#     if(spk == ".DS_Store"): continue
#     for f in os.listdir(f"{folder}/{spk}"):
#             toks = f.split('-')
#             if(len(toks[0]) == 4):
#                 toks[0] = toks[0][1:]
#             elif(len(toks[0]) == 2):
#                 toks[0] = "0" + toks[0]
            
#             if(len(toks) > 3):
#                 toks = toks[:1] + toks[2:]
            
#             print(os.path.join(folder, spk, '-'.join(toks)))
#             os.rename(os.path.join(folder, spk, f), os.path.join(folder, spk, '-'.join(toks)))
