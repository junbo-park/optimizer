"""
Contains models that can be used by the optimizer. Currently, there are two types:
- BetaLogNormalModel: model win-rate and pubrev per win separately and combine results
- GammaModel: model pubrev per request
"""

import os
import sys

import numpy as np
from scipy.special import gamma as gamma_func
from scipy.stats import beta
from scipy.stats import gamma
from scipy.stats import norm

import scipy.integrate as integrate
import scipy.optimize as optimize


def check_num_wins(df, min_num_wins):
    num_wins = len(df[df["pubrev"] > 0])
    return num_wins > min_num_wins


class BetaLogNormalModel(object):
    """ Uses Beta distribution and Normal distribution to model
    conjugate priors of the win-rate and log of publisher revenue
    """
    def __init__(self, verbose=False):
        self.verbose = verbose
        
        self.epsilon = 1e-2
        self.min_num_wins = 5
    
    def _get_beta_posterior_params(self, df):
        a, b = 2, 2
        
        num_wins = (df["pubrev"] > 0).sum()
        num_requests = len(df)
        
        a = a + num_wins
        b = b + (num_requests - num_wins)

        return a, b
    
    def _get_lognormal_posterior_params(self, df):
        mu, v, a, b = 0, 0, 0, 0
        
        wins = df[df["pubrev"] > 0]
        log_pubrev = np.log(wins["pubrev"] + 1)
        
        mu0 = np.log(1e5)
        v0 = 2
        a0 = v0 // 2
        b0 = 1
        
        num_wins = len(wins)
        log_pubrev_mean = log_pubrev.mean()
        log_pubrev_std = log_pubrev.std()
        
        mu = (v0 * mu0 + num_wins * log_pubrev_mean) / (v0 + num_wins)
        v = v0 + num_wins
        a = a0 + num_wins // 2
        b = b0 + 0.5 * num_wins * log_pubrev_std ** 2 \
                + (num_wins * v0) / (num_wins + v0) * ((log_pubrev_mean - mu0) ** 2/ 2)        
        
        return mu, v, a, b

    def _get_beta_means(self, hyperparams, N):
        a = hyperparams["beta_a"]
        b = hyperparams["beta_b"]

        win_mean = a / (a + b)
        win_std  = np.sqrt(a / (a + b) ** 2)

        if self.verbose:
            print(f"num_wins: {a}, num_requests: {a+b}")
            print(f"expected win rate mean: {win_mean:.4f}")
            print(f"expected win rate std: {win_std:.4f}")

        means = beta.rvs(a, b, size=N)
        return means
    
    def _get_lognormal_means(self, hyperparams, N):
        mu = hyperparams["mu"]
        v = hyperparams["v"]
        a = hyperparams["a"]
        b = hyperparams["b"]

        T = gamma.rvs(a, scale=1/b, size=N)
        X = norm.rvs(loc=mu, scale=np.sqrt(1 / (v * T)))

        if self.verbose:
            print(f"expected log pubrev mean: {X.mean():.3f}")
            print(f"expected log pubrev std error of mean: {np.sqrt(1/(v * T.mean())):.3f}")
            print(f"expected pubrev mean: {np.exp(X.mean() + 1 / (2 * T.mean())) / 1e6:.3f}")

        means = np.exp(X + 1 / (2 * T))
        return means, (X, T)
    
    def get_posterior_hyperparams(self, df):
        beta_a, beta_b = self._get_beta_posterior_params(df)
        mu, v, a, b = self._get_lognormal_posterior_params(df)
    
        hyperparams = {"beta_a": beta_a,  "beta_b": beta_b,  "mu": mu,  "v": v,  "a": a,  "b": b}        
        return hyperparams
    
    def get_posterior_means(self, hyperparams, N):
        beta_means = self._get_beta_means(hyperparams, N)
        try:
            lognormal_means, _ = self._get_lognormal_means(hyperparams, N)
        except:
            raise ValueError(f"Hyper-parameter: {hyperparams}")
        
        return beta_means, lognormal_means
    
    def get_reward_distribution(self, df, N, global_mean):
        # Check number of wins
        enough_wins = check_num_wins(df, self.min_num_wins)
        # If not return array of small, positive random numbers
        if not enough_wins:
            print(f"Not enough wins (< {self.min_num_wins}), returning small, random reward array")
            return self.epsilon * np.random.random(N) - global_mean
        # Get hyperparameters
        hyperparams = self.get_posterior_hyperparams(df)
        # Get means
        beta_means, lognormal_means = self.get_posterior_means(hyperparams, N)
        # Combine means
        means = beta_means * lognormal_means
        # Get deviation from means
        delta_means = means - global_mean

        return delta_means


class GammaModel(object):
    """ Use a single model (conjugate prior) to model pubrev per request """
    def __init__(self, alpha0, verbose=False):
        self.alpha0 = alpha0
        self.verbose = verbose
        
        # Number of points to approximate the cdf
        self.cdf_resolution = 5000

        self.epsilon = 1e-2
        self.min_num_wins = 5
    
    def pubrev_to_cpmusd(self, s):
        return (s + 1) / 1e6

    def get_optimal_alpha(self, df, beta):
        a0 = 1
        b0 = 1
        c0 = 1

        n = len(df)
        cpm_usd = self.pubrev_to_cpmusd(df["pubrev"])
        prod_x = cpm_usd.prod()
        sum_log_x = np.log(cpm_usd).sum()

        b = b0 + n
        c = c0 + n

        np_log_a = np.log(a0) + sum_log_x

        exponent = lambda alpha: -1 * ((alpha - 1) * np_log_a \
                                       + alpha * c * np.log(beta) \
                                       - b * np.log(gamma_func(alpha)))

        return optimize.minimize(exponent, 0.05)["x"][0]            
    
    def get_posterior_hyperparams(self, df):
        a0, b0 = 2, 2
        alpha0 = self.alpha0
        
        if self.verbose:
            print("Starting alpha: ", alpha0)    

        n = len(df)
        cpm_usd = self.pubrev_to_cpmusd(df["pubrev"])
        sum_x = cpm_usd.sum()

        diff = np.inf
        tol = 1e-5
        prev_alpha = None
        num_iteration = 0

        curr_alpha = alpha0
        while diff > tol:
            a = curr_alpha * n + a0
            b = b0 / (1 + b0 * sum_x)

            optimal_beta = (a-1) * b
            curr_alpha = self.get_optimal_alpha(df, optimal_beta)
            if prev_alpha:
                diff = np.abs(prev_alpha - curr_alpha)

            prev_alpha = curr_alpha
            num_iteration +=1
        
        if self.verbose:
            print("Optimized alpha: ", curr_alpha)
            print("Num_iteration: ", num_iteration)
        
        hyperparams = {"a": a, "b": b, "alpha": curr_alpha}

        return hyperparams

    def get_pdf_func(self, hyperparams):
        a, b = hyperparams["a"], hyperparams["b"]

        exponent = lambda beta: (a - 1) * np.log(beta * np.e / (a-1)) - beta / b - a * np.log(b)
        pdf_func = lambda beta: np.exp(exponent(beta)) / np.sqrt(2 * np.pi * (a-1))

        beta_min = optimize.fsolve(lambda x: exponent(x) + 2, 1e-5)[0]
        beta_max = optimize.fsolve(lambda x: exponent(x) + 2, 1e5)[0]
        if self.verbose:
            print(f"beta_min: {beta_min:.3f}, beta_max: {beta_max:.3f}")

        return pdf_func, beta_min, beta_max

    def test_pdf(self, pdf_func, xmin, xmax):
        diff = np.abs(integrate.quad(pdf_func, xmin, xmax)[0] - 1)
        if diff > 5e-2:
            print(f"pdf does not integrate to 1: (diff={diff:.3f})")

    def get_cdf_array(self, beta_min, beta_max, pdf_func):
        n = self.cdf_resolution
        betas = np.linspace(beta_min, beta_max, n)
        dx = (beta_max - beta_min) / n

        pdf = np.array([pdf_func(x) for x in betas])
        cdf = pdf.cumsum() * dx  
    
        return betas, cdf
    
    def get_random_beta(self, betas, cdf):
        r = np.random.rand()
        idx = np.searchsorted(cdf, r)

        if idx == len(cdf):
            return betas[-1]

        return betas[idx]

    def get_random_betas(self, betas, cdf, N):
        random_betas = np.array([self.get_random_beta(betas, cdf) 
                                 for _ in range(N)])

        return random_betas

    def get_reward_distribution(self, df, N, global_mean):
        # Check number of wins
        enough_wins = check_num_wins(df, self.min_num_wins)

        # If not return array of small, positive random numbers
        if not enough_wins:
            print(f"Not enough wins (< {self.min_num_wins}), returning small, random reward array")
            return self.epsilon * np.random.random(N) - global_mean

        hyperparams = self.get_posterior_hyperparams(df)

        pdf_func, beta_min, beta_max = self.get_pdf_func(hyperparams)
        
        self.test_pdf(pdf_func, beta_min, beta_max)
                
        betas, cdf = self.get_cdf_array(beta_min, beta_max, pdf_func)
        
        random_betas = self.get_random_betas(betas, cdf, N)
        means = hyperparams["alpha"] / random_betas

        if self.verbose:        
            print(f"expected pubrev mean: {means.mean():.5f}")
            print(f"std of pubrev mean: {means.std():.5f}")
        
        delta_means = means - global_mean

        return delta_means