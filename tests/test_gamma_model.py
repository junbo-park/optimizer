import numpy as np
import pandas as pd

from prebid_optimizer import models


SAMPLE_DF = pd.DataFrame({
    "pubrev": [0] * 1000 + [1e5 + 2e3 * x for x in np.logspace(0, 2, 100)]
})

N = 10000
ALPHA0 = 0.08
MODEL = models.GammaModel(alpha0=ALPHA0)
HYPERPARAMS = MODEL.get_posterior_hyperparams(SAMPLE_DF)


def abs_diff(a, b, precision=4):
    return np.round(np.abs(a - b), precision)


def test_get_posterior_hyperparams():
    hyperparams = HYPERPARAMS

    assert abs_diff(hyperparams["a"], 108) < 1
    assert abs_diff(hyperparams["b"], 0.0673) < 1e-3
    assert abs_diff(hyperparams["alpha"], 0.0969) < 1e-3


def test_get_reward_distribution():
    n_trials = 10
    means = np.zeros(n_trials)
    stds = np.zeros(n_trials)

    for i in range(n_trials):
        # no global_mean
        rewards = MODEL.get_reward_distribution(SAMPLE_DF, N, 0)

        means[i] = rewards.mean()
        stds[i] = rewards.std()

    assert abs_diff(means.mean(), 0.01338, precision=5) < 0.00100 , \
        f"means.mean() = {means.mean()}"
    assert abs_diff(stds.mean(), 0.00130) < 0.00010, \
        f"std.mean() = {stds.mean()}"
