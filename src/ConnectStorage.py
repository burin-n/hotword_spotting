import os, uuid
import sys
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
import shutil


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
        