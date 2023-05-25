from datetime import datetime

import numpy as np

from prebid_optimizer import reader


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

reader = reader.TSReader(
    config_id="d385ba19-47da-48e9-ab1b-cdfb4149118b",
    source_table="ox-datascience-devint.prebid.auctions_raw_sample",
    configs_to_optimize={"bidderTimeout": [600, 800, 1000, 1500]},
    verbose=True
)

start_timestamp = datetime.strptime("2021-09-16 00:00:00", 
                                    DATETIME_FORMAT)
end_timestamp = datetime.strptime("2021-09-16 04:00:00", 
                                    DATETIME_FORMAT)

DF = reader.get_data(start_timestamp, end_timestamp, 
                        use_weighted_training=False)

WEIGHTED_DF = reader.get_data(start_timestamp, end_timestamp, 
                                use_weighted_training=True)

def test_get_data():
    assert len(DF) == 107859, f"Wrong number of data points: {len(DF)}"
