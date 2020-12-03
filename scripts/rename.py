import os

tgt = '/Users/burin/workspace/hotword_data/data/test'
# for spk in os.listdir(tgt):
for spk in [f"spk{str(num).zfill(3)}" for num in range(103,119)]:
    if(not os.path.exists(os.path.join(tgt, spk))):
        continue
    for file in os.listdir(os.path.join(tgt, spk)):
        if(file != ".DS_Store"):
            old_path = os.path.join(tgt,spk,file)
            new_path = os.path.join(tgt,spk,f"{spk[-3:]}-{file}")
            os.rename(old_path, new_path)
            print(old_path)
            print(new_path)
