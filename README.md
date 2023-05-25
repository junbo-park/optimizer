# Prebid Optimizer

Create a script that will
1. Ingest historical data from BigQuery
2. Calculate the random array of pubrev per hour for each "action"
3. Using the calculated pubrev random arrays, calculate the probability of each action to be selected
4. Export the probability array to `output.json` and `distributions.json`

To use the repo, create a virtualenv and install packages in `requirements.txt`

## Usage
- To do a dry run of optimizer config generator, run `make test.optimizer`
- To do a dry run of AB-n analysis, run `make test.abn`
- To build a docker container locally, run `make build`
- To open a shell inside the docker container after building, run `make devshell`

## CLI

**cli.py** contains the commands that will be run in production. Run `python cli.py` to see a list of available commands. The command line is set up by [python-fire](https://github.com/google/python-fire/blob/master/docs/guide.md).


### Example: Running Config Optimizer

`python cli.py optimizer --config_ids='["abc-123","def-123"]' --hour_window=6 --bucket_size=20000 --env=devint --is_dev` 
