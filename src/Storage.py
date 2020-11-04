import os
import sys
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
import shutil
from scipy.io.wavfile import write
import numpy as np

def download_references(connection_str, container_name="cu63-test", local_path=None):
    # Create the BlobServiceClient object which will be used to create a container client
    blob_service_client = BlobServiceClient.from_connection_string(connection_str)
    container_client = blob_service_client.get_container_client(container_name)
    if(local_path == None):
        local_path = f"downloaded_data/references/{container_name}"
    if(not os.path.exists(local_path)):
        os.makedirs(local_path)
    else:
        shutil.rmtree(local_path)
        os.makedirs(local_path)

    print(f'download referece from {container_name}...') 
    blob_list = container_client.list_blobs()
    for blob in blob_list:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob.name) 
        with open(f"{local_path}/{blob.name}", "wb") as download_file:
            download_file.write(blob_client.download_blob().readall()) 
        

class Storage():
    def __init__(self, container_name, ref_connection_str, hyp_connection_str=None, tmp_dir='tmp'):
        self.container_name = container_name
        self.ref_connection_str = ref_connection_str
        self.hyp_connection_str = hyp_connection_str
        self.tmp_dir = tmp_dir
        self.backup_blob_service_client = BlobServiceClient.from_connection_string(self.hyp_connection_str) 
        try:
            backup_container_client = self.backup_blob_service_client.create_container(self.container_name)
        except:
            pass
        self.backup_tmp = f"{tmp_dir}/hypotheses/{self.container_name}"

        if(not os.path.exists(self.backup_tmp)):
            os.makedirs(self.backup_tmp)
        else:
            shutil.rmtree(self.backup_tmp)
            os.makedirs(self.backup_tmp)

    def download_references(self):
        # Create the BlobServiceClient object which will be used to create a container client
        blob_service_client = BlobServiceClient.from_connection_string(self.ref_connection_str)
        container_client = blob_service_client.get_container_client(self.container_name)

        local_path = f"{self.tmp_dir}/references/{self.container_name}"
        if(not os.path.exists(local_path)):
            os.makedirs(local_path)
        else:
            shutil.rmtree(local_path)
            os.makedirs(local_path)

        print(f'download refereces from {self.container_name}...') 
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            blob_client = blob_service_client.get_blob_client(container=self.container_name, blob=blob.name)
            with open(f"{local_path}/{blob.name}", "wb") as download_file:
                download_file.write(blob_client.download_blob().readall()) 
        

    def backup(self, result):
        # Create a file in local data directory to upload and download
        # hyp_ref_score_timestamp_
        time = result['time_end_record'].replace(" ", "T")
        dists = '_'.join(["{:.3f}".format(x) for x in result['dists']])
        local_file_name = f"hyp_{time}_{dists}.wav"
        upload_file_path = os.path.join(self.backup_tmp, local_file_name)
        print(upload_file_path)
        write(upload_file_path, result['sampling_rate'], np.asarray(result['data']))
        # Create a blob client using the local file name as the name for the blob
        blob_client = self.backup_blob_service_client.get_blob_client(container=self.container_name, blob=local_file_name)
        # Upload the created file
        with open(upload_file_path, "rb") as data:
            blob_client.upload_blob(data)
        
        os.remove(upload_file_path) 

