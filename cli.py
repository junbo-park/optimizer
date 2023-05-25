from datetime import datetime, timedelta
import time
import fire

from prebid_optimizer import runOptimizer

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def run_optimizer(env, config_ids, bucket_size, source_table, hour_window, 
                  data_delay_hour, model_type, run_timestamp_str=None, 
                  is_dev=False):
  """
  Runs the prebid optimizer on each of the provided config_ids, using the current time as the starting point for data.
  Writes the result to a GCS bucket.

  Args:
      env (string): The environment to run this in (devint|qa|prod). Will be used to construct the GCS bucket path and BQ tables.
      config_ids (list(string)): A list of config ids for which the optimizer should be run.
      hour_window (int): How many hours of data to use.
      data_delay_hour (int): How many hours are data upload delayed.
      bucket_size (int): The size of the buckets to use for the optimizer.
      source_table (string): The source table to use for BigQuery (fully qualified table name).
      is_dev (bool, optional): If true, turns on additional debugging and local mode testing functionality. Defaults to False.
      run_timestamp_str (str, optional): If not null, optimizer will be "run" at given timestamp.
  """

  # TODO - eventually we will load this externally
  CONFIGS_TO_OPTIMIZE = {
    "default": {
      "bidderTimeout": [1000, 1500, 2000], 
    },
  }

  for config_id in config_ids:
    configs_to_optimize = CONFIGS_TO_OPTIMIZE.get(config_id) or CONFIGS_TO_OPTIMIZE.get('default')
    
    if run_timestamp_str:
      run_timestamp = datetime.strptime(run_timestamp_str, DATETIME_FORMAT)
    else:
      # Offset the time by the data upload delay
      run_timestamp = datetime.utcnow()

    print(f"Processing Config Id: {config_id}")
    start_time = time.perf_counter()
    runOptimizer(
      env, 
      config_id,
      bucket_size,
      source_table,
      configs_to_optimize,
      run_timestamp,
      hour_window,
      data_delay_hour,
      model_type,
      is_dev=is_dev,
    )

    end_time = time.perf_counter()
    print(f"Finished processing Config Id: {config_id} in {end_time - start_time:0.4f} seconds")


if __name__ == '__main__':
  fire.Fire({
    'optimizer': run_optimizer
  })
