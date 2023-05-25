from datetime import datetime

from prebid_optimizer import runOptimizer


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def test_dry_run():
    """ Dry run the optimizer on a sample dataset """
    runOptimizer(
        env="devint", 
        config_id="d385ba19-47da-48e9-ab1b-cdfb4149118b",
        bucket_size=10000,
        source_table="ox-datascience-devint.prebid.auctions_raw_sample",
        configs_to_optimize={"bidderTimeout": [600, 800, 1000, 1500]},
        run_timestamp=datetime.strptime("2021-09-16 08:12:32", 
                                        DATETIME_FORMAT),
        hour_window=3,
        data_delay_hour=2,
        model_type="default"
    )