# folder=data/references/*
# base_out_folder=data_8k/references

# for spk in $folder ; do
#     out_folder=${base_out_folder}/$(echo $spk | cut -d "/" -f 3)
#     # echo ${out_folder}
#     if [[ ! -d $out_folder ]]; then
#         mkdir -p $out_folder
#     fi
#     for f in $spk/*
#         do
#             #echo "Processing $f file..."
#             tgt=${out_folder}/$(echo $f | cut -d "/" -f 4-)
#             # take action on each file. $f store current file name
#             # echo "sox $f -r 8k -b 16 $tgt"
#             sox $f -r 8k -b 16 $tgt
#         done
# done


folder="Patient Recordings/Patient-102-6333281"
base_out_folder="Patient Recordings/Patient-102-6333281_8k"

out_folder=${base_out_folder}

if [[ ! -d "$out_folder" ]]; then
    mkdir -p "$out_folder"
fi

for f in "$folder"/*
do
    #echo "Processing $f file..."
    tgt="${out_folder}"/$(echo "$f" | cut -d "/" -f 3-)
    # take action on each file. $f store current file name
    # echo "sox $f -r 8k -b 16 $tgt"
    sox "$f" -r 8k -b 16 -c 1 "$tgt"
done
