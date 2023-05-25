DECLARE _start_time TIMESTAMP;
DECLARE _end_time TIMESTAMP;
DECLARE _configID STRING;
SET _start_time = "2021-10-27 00:00:00";
SET _end_time = "2021-10-28 00:00:00";
SET _configID = "d385ba19-47da-48e9-ab1b-cdfb4149118b";

WITH 
adunit_table AS (
  SELECT
    CAST(JSON_EXTRACT_SCALAR(optimizerConfig, "$.bidderTimeout.n") as INT64) as bidderTimeout, 
    adUnits
  FROM `ox-datascience-devint.prebid.auctions_raw_lainey_gossip`
  WHERE 
    receiptTimeMillis >= _start_time
    AND receiptTimeMillis < _end_time
    AND configID = _configID
    AND optimizerConfig is not null
    AND testCode = "ds_optimizer"
),
flattened_table AS (
  SELECT
    bidderTimeout,
    IFNULL (bidResponses.latency, -1) as latency,
    IFNULL(microCPMUSD, -1) as bid_value,
    IFNULL(bidResponses.winner, FALSE) as win
  FROM
    adunit_table src, src.adUnits, adUnits.bidRequests
  LEFT JOIN bidRequests.bidResponses
  WHERE bidderTimeout IN UNNEST([800, 1000, 1500, 2000, 2500])
)
SELECT
    bidderTimeout,
    bid_value,
    latency,
    win
FROM flattened_table
WHERE bidderTimeout is not null