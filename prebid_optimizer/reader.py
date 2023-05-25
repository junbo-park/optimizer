from datetime import timedelta

from google.cloud import bigquery
from google.cloud import bigquery_storage
import pandas as pd


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

CONFIG_SCHEMA = {
    "bidderTimeout": "INT64"
}

SQL_TEMPLATE = """
WITH 
adunit_table AS (
    SELECT
        receiptTimeMillis,
        -- auction hour, measured from start_time (starts from 1)
        TIMESTAMP_DIFF(receiptTimeMillis, TIMESTAMP("{start_time}"), HOUR) as auction_hour,
        {parse_optimizerConfig}
        adUnits
    FROM `{source_table}`
    WHERE 
        receiptTimeMillis >= timestamp("{start_time}")
        AND receiptTimeMillis < timestamp("{end_time}")
        AND configID = "{configID}"
        AND optimizerConfig IS NOT NULL
        AND testCode = "ds_optimizer"
        -- TODO: remove after page refresh is implemented
        -- Ignoring sessions that lasted longer then 30 minutes (1800 secs)
        -- Ignoring sessions without sessionSeconds
        AND json_extract_scalar(optimizerConfig, "$.sessionSeconds") IS NOT NULL
        AND IFNULL(cast(json_extract_scalar(optimizerConfig, "$.sessionSeconds") AS INT64), 10000) < 3600
),
flattened_table AS (
    SELECT
        receiptTimeMillis,
        auction_hour,
        {config_fields},
        adUnits.code as adunit_code,
        IF(bidResponses.winner = true, microCPMUSD, 0) as cpm,
    FROM
        adunit_table adrequest, 
        adrequest.adunits,
        adUnits.bidRequests
    LEFT JOIN bidRequests.bidResponses
),
win_cpm_table AS (
    SELECT 
        receiptTimeMillis,
        auction_hour,
        adunit_code,
        IF(SUM(cpm) = 0, 0, 1) as win,
        SUM(cpm) as pubrev,
        {config_fields}
    FROM flattened_table
    GROUP BY 1,2,3, {config_fields}
)
SELECT
    auction_hour,
    {config_fields},
    win,
    pubrev
FROM win_cpm_table
"""


def get_hour_window(start_timestamp, end_timestamp):
    return  (end_timestamp - start_timestamp).seconds // 3600 \
                + (end_timestamp - start_timestamp).days * 24


class TSReader:
    def __init__(self, config_id, source_table, configs_to_optimize,
                 gcp_project=None, verbose=False):
        self.client = bigquery.Client(project=gcp_project)
        self.storage_client = bigquery_storage.BigQueryReadClient()
        self.config_id = config_id
        self.configs_to_optimize = configs_to_optimize
        self.source_table = source_table
        self.verbose = verbose

    def _read_from_BigQuery(self, sql_query):
        """ Use the sql_query to read data from BigQuery """
        df = (
            self.client.query(sql_query)
            .result()
            .to_dataframe(bqstorage_client=self.storage_client)
        )        
        return df

    def get_data(self, start_timestamp, end_timestamp, use_weighted_training):
        configs = self.configs_to_optimize.keys()
        configID = self.config_id

        parse_optimizerConfig = ""
        parse_template = 'cast(json_extract_scalar(optimizerConfig, "$.{field_name}.n") as {field_type}) as {field_name}, \n'
        for field_name in configs:
            field_type = CONFIG_SCHEMA.get(field_name, "STRING")
            parse_optimizerConfig += parse_template.format(field_name=field_name, field_type=field_type)
        
        config_fields = ", ".join(configs)

        params = {
            "configID": configID,
            "parse_optimizerConfig": parse_optimizerConfig,
            "config_fields": config_fields,
            "source_table": self.source_table
        }
        
        start_time_str = start_timestamp.strftime(DATETIME_FORMAT)
        end_time_str = end_timestamp.strftime(DATETIME_FORMAT)
        hour_window = get_hour_window(start_timestamp ,end_timestamp)

        print(start_time_str, end_time_str, hour_window)

        random_idx_clause = f"{hour_window} / auction_hour * RAND()" \
                            if use_weighted_training else "0"

        params.update({
            "start_time": start_time_str,
            "end_time": end_time_str,
            "random_idx_clause": random_idx_clause,
        })

        sql = SQL_TEMPLATE.format(**params)
        df = self._read_from_BigQuery(sql)

        return df