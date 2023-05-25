from datetime import datetime
from pprint import pprint
import numpy as np

from prebid_optimizer import optimizer


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def abs_diff(a, b, precision=4):
    return np.round(np.abs(a - b), precision)

   
def test_get_config_combos():
    dummy_config = {"a":[1, 2], "b": [3, 4]}

    combos = optimizer.get_config_combos(dummy_config)
    correct_combos = [
        {'a': 1, 'b': 3}, {'a': 1, 'b': 4},
        {'a': 2, 'b': 3}, {'a': 2, 'b': 4},
    ]

    assert combos == correct_combos, \
        f"Incorrect config combinations: {combos}"


def test_empty_dataset():        
    _optimizer = optimizer.TSOptimizer(
            config_id="dummy", 
            bucket_size=10000, 
            source_table="ox-datascience-devint.prebid.auctions_raw_sample",
            configs_to_optimize={"a":[1,2]},
            min_probability=0.01,
            model_type="default",
            use_weighted_training=False
        )
    
    start_timestamp = datetime.strptime("2021-06-05 00:00:00", 
                                        DATETIME_FORMAT)
    end_timestamp = datetime.strptime("2021-06-06 00:00:00", 
                                        DATETIME_FORMAT)
    
    _optimizer.generate_distributions(start_timestamp, end_timestamp)

    assert _optimizer.not_enough_data


def test_generate_distributions():
    _optimizer = optimizer.TSOptimizer(
            config_id="d385ba19-47da-48e9-ab1b-cdfb4149118b", # LaineyGossip
            bucket_size=100000, 
            source_table="ox-datascience-devint.prebid.auctions_raw_sample",
            configs_to_optimize={"bidderTimeout": [600, 800, 1000, 1500]},
            min_probability=0.01,
            model_type="beta_lognormal",
            use_weighted_training=False
        )
    
    start_timestamp = datetime.strptime("2021-09-16 00:00:00", 
                                        DATETIME_FORMAT)
    end_timestamp = datetime.strptime("2021-09-17 00:00:00", 
                                        DATETIME_FORMAT)
    
    results = _optimizer.generate_distributions(start_timestamp, 
                                                end_timestamp)

    assert len(results["actions"]) == 4, "Incorrect number of actions"

    probs_to_win = [x["prob_to_win"] for x in results["actions"]]

    assert      (abs_diff(probs_to_win[0], 0.11) < 0.02) \
            and (abs_diff(probs_to_win[1], 0.16) < 0.02) \
            and (abs_diff(probs_to_win[2], 0.31) < 0.02) \
            and (abs_diff(probs_to_win[3], 0.42) < 0.02), \
            f"probs_to_win: {probs_to_win}"
