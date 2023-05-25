from datetime import datetime, timedelta
import json

from prebid_optimizer.optimizer import TSOptimizer
from prebid_optimizer.exporter import exportBQTable
from prebid_optimizer.exporter import exportJSON


def round_to_hour(dt_obj):
    return dt_obj.replace(microsecond=0, second=0, minute=0)


def runOptimizer(env, config_id, bucket_size, source_table, 
        configs_to_optimize, run_timestamp, hour_window, data_delay_hour,
        model_type, is_dev=False):

    # TODO: parameterize min_probability
    min_probability = 0.025
    optimizer = TSOptimizer(config_id, bucket_size, source_table,
                            configs_to_optimize, min_probability, model_type,
                            is_dev=is_dev)

    # Straighten out timestamps
    cleaned_run_timestamp = round_to_hour(run_timestamp)
    end_timestamp = cleaned_run_timestamp - timedelta(hours=data_delay_hour)
    start_timestamp = end_timestamp - timedelta(hours=hour_window)

    results = optimizer.generate_distributions(start_timestamp, end_timestamp)

    table_id = f"ox-datascience-{env}.prebid.prebid_output"
    exportBQTable(results, config_id, run_timestamp, start_timestamp,
                  end_timestamp, table_id)

    new_gcs_bucket = f"ox-{env}-prebid-optimizer-data"
    exportJSON(results, new_gcs_bucket, config_id)
