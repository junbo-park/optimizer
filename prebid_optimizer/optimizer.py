import json

import numpy as np
import pandas as pd
from scipy.stats import beta
from scipy.stats import gamma
from scipy.stats import norm

from prebid_optimizer.reader import TSReader
from prebid_optimizer.models import BetaLogNormalModel
from prebid_optimizer.models import GammaModel


def count_occurence(n, arr):
    return np.where(arr == n, 1, 0).sum()


def get_config_combos(configs_to_optimize):
    prev = []
    for key in sorted(configs_to_optimize):
        config_key, config_vals = key, configs_to_optimize[key]
        curr = []
        if not prev:
            for val in config_vals:
                curr.append({config_key: val})
        else:
            for combo in prev:
                for val in config_vals:
                    new_combo = combo.copy()
                    new_combo[config_key] = val
                    curr.append(new_combo)
        prev = curr

    config_combos = prev
    return config_combos    


class TSOptimizer:
    def __init__(self, config_id, bucket_size, source_table, 
                 configs_to_optimize, min_probability, model_type, 
                 use_weighted_training=True, is_dev=False):

        self.set_reader(config_id, source_table, configs_to_optimize)
        self.config_combos = get_config_combos(configs_to_optimize)
        self._set_model_type(model_type, is_dev)

        self.bucket_size = bucket_size
        self.config_id = config_id
        self.is_dev = is_dev
        self.use_weighted_training = use_weighted_training

        self.not_enough_data = False
        self.min_wins = 5

        self.num_actions = len(self.config_combos)
        # Set the minimum probability for each action (it will at least be X%)
        norm_factor = 1 / (1 - self.num_actions * min_probability)
        self.boost = norm_factor * self.bucket_size * min_probability

    def set_reader(self, config_id, source_table, configs_to_optimize):
        self.reader = TSReader(config_id, source_table, configs_to_optimize)

    def _set_model_type(self, model_type, is_dev):
        print(f"Setting model type to {model_type}..")
        if model_type == "default" or model_type == "beta_lognormal":
            model = BetaLogNormalModel(verbose=is_dev)
        elif model_type == "gamma":
            model = GammaModel(alpha0=0.08, verbose=is_dev)
        else:
            raise ValueError(f"{model_type} is not a valid model type")
        
        self.model = model

    def _check_enough_data(self, df):
        num_wins = len(df[df["win"] == 1])
        if len(df) == 0 or num_wins < self.num_actions * self.min_wins:
            return False
        
        return True

    def _get_data(self, start_timestamp, end_timestamp):
        df = self.reader.get_data(start_timestamp, end_timestamp, 
                                 self.use_weighted_training)
        enough_data = self._check_enough_data(df)
        if not enough_data:
            self.not_enough_data = True
            return

        if self.is_dev:
            print("Num rows", df.shape[0])
            print(df.head())

        num_hours = df["auction_hour"].nunique()
        self.hours = [hr for hr in range(num_hours)]
        
        return df

    def _filter_dataset(self, raw_df, config_combo):
        print(config_combo)
        keys = []
        for key, val in config_combo.items():
            df = raw_df[raw_df[key] == val]
            keys.append(key)

        return df

    def _get_basic_stats(self, df):
        num_trials = len(df)
        num_wins = len(df[df["win"] == 1])

        wins = df[df["win"] == 1]
        if len(wins) > self.min_wins:
            log_pubrev = np.log(wins["pubrev"] + 1)
            log_pubrev_mean = log_pubrev.mean()
            log_pubrev_std = log_pubrev.std()
        else:
            log_pubrev_mean, log_pubrev_std = 0, 0

        return num_trials, num_wins, log_pubrev_mean, log_pubrev_std

    def _get_default_distributions(self):
        num_actions = len(self.config_combos)

        results = {"actions": []}
        for i in range(num_actions):
            results["actions"].append(
                {
                    "config": self.config_combos[i],
                    "prob_to_win": 1 / num_actions,
                    "num_trials": None,
                    "num_wins": None,
                    "log_pubrev_mean": None,
                    "log_pubrev_std": None
                }
            )

        if self.is_dev:
            with open(".output/output.json", "w") as f:
                json.dump(results, f, indent=2)

        return results

    def generate_distributions(self, start_timestamp, end_timestamp):
        df = self._get_data(start_timestamp, end_timestamp)

        if self.not_enough_data:
            print("Not enough data")
            return self._get_default_distributions()

        num_actions = len(self.config_combos)
        rv_arrays = np.zeros((num_actions, self.bucket_size))
        num_trials_arr = []
        num_wins_arr = []
        log_pubrev_mean_arr = []
        log_pubrev_std_arr = []
            
        # Calculate global means
        global_means = []
        for hour in self.hours:
            hourly_mean = df[df["auction_hour"] == hour]["pubrev"].mean()
            global_means.append(hourly_mean)

        # Get reward distribution for each hour
        for action_idx, config_combo in enumerate(self.config_combos):
            sub_df = self._filter_dataset(df, config_combo)
            rvs = []
            for hour in self.hours:
                hourly_data = sub_df[sub_df["auction_hour"] == hour]
                num_hourly_data = len(df[df["auction_hour"] == hour])
                global_hourly_mean = global_means[hour]
                rv = self.model.get_reward_distribution(hourly_data, 
                                                        num_hourly_data,
                                                        global_hourly_mean)
                rvs.extend(rv)

            
            rv_arrays[action_idx, :] = np.random.choice(rvs, self.bucket_size)

            # Store basic summary statistics for latest hourly data
            latest_hourly_data = sub_df[sub_df["auction_hour"] == self.hours[-1]]
            num_trials, num_wins, log_pubrev_mean, log_pubrev_std \
                = self._get_basic_stats(latest_hourly_data)
            num_trials_arr.append(num_trials)
            num_wins_arr.append(num_wins)
            log_pubrev_mean_arr.append(log_pubrev_mean)
            log_pubrev_std_arr.append(log_pubrev_std)

        # Calculate the index of the winners for each iteration
        winners = np.argmax(rv_arrays, axis=0)
        results = {"actions": []}
        for i in range(num_actions):            
            prob_to_win = (count_occurence(i, winners) + self.boost) \
                            / (self.bucket_size + num_actions * self.boost)
            prob_to_win = float(np.round(prob_to_win, 4))

            results["actions"].append(
                {
                    "config": self.config_combos[i],
                    "prob_to_win": prob_to_win,
                    "num_trials": num_trials_arr[i],
                    "num_wins": num_wins_arr[i],
                    "log_pubrev_mean": log_pubrev_mean_arr[i],
                    "log_pubrev_std": log_pubrev_std_arr[i]
                }
            )
        
        if self.is_dev:
            with open(".output/output.json", "w") as f:
                json.dump(results, f, indent=2)

        return results