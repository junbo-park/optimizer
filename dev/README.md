# Notebooks

The notebooks in the `/dev` folder can be run in docker environment by running
```
make build.dev
make docker.jupyter
```

## EDA notebooks
### eda
We do basic exploratory data analysis in this notebook.
### latency 
This notebook examines response time (time it takes for exchanges to submit 
bids).
### mean stability
This notebook examines examines how "cumulative" win-rate and average 
publisher revenue evolve over time and see how stable the mean is. 

## Model exploration notebooks
### gamma distribution
This jupyter notebook shows how we can fit a gamma distribution to our data. 
Gamma distribution has two hyper parameters (alpha, beta) while we could draw from
a bivariate posterior distribution, we instead fix alpha and draw beta. 

We justify that by showing that for our data, alpha is quite stable--the shape of 
the pubrev distributions are stable--while beta, which determines the rate, can vary
a lot depending on the input data.

### model fit
This notebook compares the actual data and the posterior distribution generated 
by the model. When we actually run the optimizer and do Thompson sampling, we 
make not one but many posterior distributions based on the data.

In this notebook, we take the most probable posterior distribution and plot it 
against the actual data. In a way, this is a method of sanity check. If the 
posterior distribution is way off, we know that it's wrong.

### time-based confounder
The issue with multi-armed bandits when we are dealing with a non-stationary
time series is that we can get a biased result based on our changing sampling
rates (see reference: https://www.unofficialgoogledatascience.com/2020/07/changing-assignment-weights-with-time.html).

To address this, we introduce a method to generate probability distribution
of average publisher revenue per hour and do a weighted average of the
distributions. 

## Simulation notebooks
### simulated thompson sampling
We simulate a Thomson sampling run by generating a fake dataset from binomial
distributions.