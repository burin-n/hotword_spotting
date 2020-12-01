
folder=/Users/burin/workspace/hotword_data/data/test
base_out_folder=/Users/burin/workspace/hotword_data/data/test_8k

for spk in "$folder"/*
do
    # echo $(echo "$spk" | cut -d "/" -f 6-6)
    # out_folder=$(echo "$spk" | cut -d "/" -f 6-6)_8k
    out_folder=${base_out_folder}/$(echo "$spk" | cut -d "/" -f 8-8)
    # echo $out_folder
    if [[ ! -d "$out_folder" ]]; then
        mkdir -p "$out_folder"
    fi

    for f in "$spk"/*
    do
        #echo "Processing $f file..."
        tgt="${out_folder}"/$(echo "$f" | cut -d "/" -f 9-)
        # echo $f
        # echo $tgt
        # take action on each file. $f store current file name
        # echo "sox $f -r 8k -b 16 $tgt"
        sox "$f" -r 8k -b 16 -c 1 "$tgt"
    done

done


# folder=/Users/burin/workspace/hotword_data/Patient_Recordings_[20_Records]
# base_out_folder=/Users/burin/workspace/hotword_data/Patient_Recordings_[20_Records]_8k

# for spk in "$folder"/*
# do
#     # echo $(echo "$spk" | cut -d "/" -f 6-6)
#     out_folder=$(echo "$spk" | cut -d "/" -f 6-6)_8k
#     out_folder=$(echo "$spk" | cut -d "/" -f -5)/${out_folder}/$(echo "$spk" | cut -d "/" -f 7-7)
#     if [[ ! -d "$out_folder" ]]; then
#         mkdir -p "$out_folder"
#     fi

#     for f in "$spk"/*
#     do
#         #echo "Processing $f file..."
#         tgt="${out_folder}"/$(echo "$f" | cut -d "/" -f 8-)
#         # echo $f
#         # echo $tgt
#         # take action on each file. $f store current file name
#         # echo "sox $f -r 8k -b 16 $tgt"
#         sox "$f" -r 8k -b 16 -c 1 "$tgt"
#     done

# done
