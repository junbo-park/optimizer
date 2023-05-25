import numpy as np
import pandas as pd

from prebid_optimizer import models


SAMPLE_DF = pd.DataFrame({
    "pubrev": [0] * 1000 + [1e5 + 2e3 * x for x in np.logspace(0, 2, 100)]
})

N = 10000
MODEL = models.BetaLogNormalModel()
HYPERPARAMS = MODEL.get_posterior_hyperparams(SAMPLE_DF)


def abs_diff(a, b, precision=4):
    return np.round(np.abs(a - b), precision)


def test_get_posterior_hyperparams():
    hyperparams = HYPERPARAMS

    assert hyperparams["beta_a"] == 2 + 100
    assert hyperparams["beta_b"] == 2 + 1000
    assert abs_diff(hyperparams["mu"], 11.8171) < 0.001, \
        f'hyperparams["mu"] = {np.round(hyperparams["mu"], 4)}'
    assert hyperparams["v"] == 2 + 100
    assert hyperparams["a"] == (2 + 100) // 2
    assert abs_diff(hyperparams["b"], 5.8167) < 0.001, \
        f'hyperparams["b"] = {np.round(hyperparams["b"], 4)}'


def test_get_beta_means():
    hyperparams = HYPERPARAMS
    beta_means = MODEL._get_beta_means(hyperparams, N)
    
    assert abs_diff(beta_means.mean(), 0.0924) < 0.001
    assert abs_diff(beta_means.std(), 0.0086) < 0.001


def test_get_lognormal_means():
    hyperparams = HYPERPARAMS
    lognormal_means, _ = MODEL._get_lognormal_means(hyperparams, N)

    assert abs_diff(lognormal_means.mean(), 143670) < 500, \
        f"lognormal_means.mean() = {np.round(lognormal_means.mean(), 4)}"
    assert abs_diff(lognormal_means.std(), 5000) < 500, \
        f"lognormal_means.mean() = {np.round(lognormal_means.std(), 4)}"


def test_get_reward_distribution():
    n_trials = 100
    means = np.zeros(n_trials)
    stds = np.zeros(n_trials)

    for i in range(n_trials):
        # No global mean
        rewards = MODEL.get_reward_distribution(SAMPLE_DF, N, 0)

        means[i] = rewards.mean()
        stds[i] = rewards.std()

    assert abs_diff(means.mean(), 13281) < 1000, \
        f"means.mean() = {means.mean()}"
    assert abs_diff(means.std(), 14) < 10, \
        f"means.mean() = {means.std()}"
