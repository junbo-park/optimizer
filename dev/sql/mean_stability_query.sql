DECLARE _start_time TIMESTAMP;
DECLARE _end_time TIMESTAMP;
DECLARE _configID STRING;
SET _start_time = "2021-10-13 14:00:00";
SET _end_time = "2021-10-20 14:00:00";
SET _configID = "d385ba19-47da-48e9-ab1b-cdfb4149118b";

WITH 
adunit_table AS (
  SELECT
    receiptTimeMillis,
    -- auction hour, measured from start_time (starts from 1)
    TIMESTAMP_DIFF(receiptTimeMillis, TIMESTAMP(_start_time), HOUR) as auction_hour,
    cast(json_extract_scalar(optimizerConfig, "$.bidderTimeout.n") as INT64) as bidderTimeout,
    adUnits
  
  -- Copy of a subset of `ox-prebid-data-prod.analytics.auctions_raw`
  FROM `ox-datascience-devint.prebid.auctions_raw_lainey_gossip_AB`
  WHERE 
    receiptTimeMillis >= timestamp(_start_time)
    AND receiptTimeMillis < timestamp(_end_time)
    AND configID = _configID
    AND optimizerConfig IS NOT NULL
    AND testCode = "ds_optimizer"
),
flattened_table AS (
  SELECT
    receiptTimeMillis,
    auction_hour,
    bidderTimeout,
    adUnits.code as adunit_code,
    IF(bidResponses.winner = true, microCPMUSD, 0) as cpm,
  FROM
    adunit_table adrequest, 
    adrequest.adunits,
    adUnits.bidRequests
  LEFT JOIN bidRequests.bidResponses
),
win_cpm_table AS (
  SELECT 
    receiptTimeMillis,
    auction_hour,
    adunit_code,
    IF(SUM(cpm) = 0, 0, 1) as win,
    SUM(cpm) as pubrev,
    bidderTimeout
  FROM flattened_table
  GROUP BY 1,2,3, bidderTimeout
)
SELECT auction_hour, bidderTimeout, win, pubrev
FROM win_cpm_table 
ORDER BY receiptTimeMillis