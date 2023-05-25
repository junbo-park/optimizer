from google.cloud import bigquery

import json
import os
import subprocess
import tempfile

from prebid_optimizer.utils import upload_blob

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


SCHEMA = [
    {
        "name": "bundleID",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "run_timestamp",
        "type": "TIMESTAMP",
        "mode": "NULLABLE"
    },
    {
        "name": "start_timestamp",
        "type": "TIMESTAMP",
        "mode": "NULLABLE"
    },
    {
        "name": "end_timestamp",
        "type": "TIMESTAMP",
        "mode": "NULLABLE"
    },
    {
        "name": "actions",
        "type": "RECORD",
        "mode": "REPEATED",
        "fields": [
            {
                "name": "config",
                "type": "RECORD",
                "mode": "NULLABLE",
                "fields": [
                    {
                        "name": "bidderTimeout",
                        "type": "INT64",
                        "mode": "NULLABLE"
                    }
                ]
            },
            {
                "name": "prob_to_win",
                "type": "FLOAT",
                "mode": "NULLABLE"
            },
            {
                "name": "num_trials",
                "type": "INT64",
                "mode": "NULLABLE"
            },
            {
                "name": "num_wins",
                "type": "INT64",
                "mode": "NULLABLE"
            },
            {
                "name": "log_pubrev_mean",
                "type": "FLOAT",
                "mode": "NULLABLE"
            },
            {
                "name": "log_pubrev_std",
                "type": "FLOAT",
                "mode": "NULLABLE"
            }
        ]
    }
]


def exportJSON(results, gcs_bucket, config_id):
    # FIXME: Have a more systematic way to do this
    distributions = {"actions": []}
    for entry in results["actions"]:
        result = {}
        result["config"] = entry["config"]
        result["prob_to_win"] = entry["prob_to_win"]

        distributions["actions"].append(result)

    print(json.dumps(distributions, indent=2))

    distributions_str = json.dumps(distributions)

    # use config_id as blob_path
    blob_path = config_id
    _create_and_upload_file_to_gcs("distributions.json", gcs_bucket, blob_path, distributions_str)


def _create_and_upload_file_to_gcs(file_name, gcs_bucket, blob_path, data):
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, file_name)
        with open(filepath, "w") as js:
            js.write(data)

        blob_full_path = os.path.join(blob_path, file_name)
        upload_blob(gcs_bucket, filepath, blob_full_path)


def exportBQTable(results, bundleID, run_timestamp, start_timestamp, 
                  end_timestamp, bq_table_id):
    # Add fields
    results["bundleID"] = bundleID
    results["run_timestamp"] = run_timestamp.strftime(DATETIME_FORMAT)
    results["start_timestamp"] = start_timestamp.strftime(DATETIME_FORMAT)
    results["end_timestamp"] = end_timestamp.strftime(DATETIME_FORMAT)

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition="WRITE_APPEND"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.json")
        with open(filepath, "w") as f:
            json.dump(results, f)

        with open(filepath, "rb") as f:
            load_job = client.load_table_from_file(f, bq_table_id, 
                                                   job_config=job_config)

    load_job.result()  # Waits for the job to complete.
