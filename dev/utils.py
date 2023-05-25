import os

from google.cloud import bigquery
from google.cloud import bigquery_storage
import pandas as pd

def get_bigquery_result(query, filepath=None, gcp_project=None):
    client = bigquery.Client(gcp_project)
    storage_client = bigquery_storage.BigQueryReadClient()
    
    if filepath and os.path.exists(filepath):
        print("Loaded from cached file..")
        return pd.read_csv(filepath)

    df = (
      client.query(query)
      .result()
      .to_dataframe(bqstorage_client=storage_client)
    )
  
    if filepath:
        safe_mkdir(filepath)
        df.to_csv(filepath, index=False)

    return df

def safe_mkdir(filepath):
    dirname = os.path.dirname(filepath)
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    
    return
