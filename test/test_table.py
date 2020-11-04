from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity
import json

with open('.env.json') as f:
    config = json.load(f)

table_service = TableService(connection_string=config['azure']["hypothesis_connection_str"])
table_service.create_table('tasktable')
task = {'PartitionKey': 'tasksSeattle', 'RowKey': '001',
        'description': 'Take out the trash', 'priority': 200}
table_service.insert_entity('tasktable', task)