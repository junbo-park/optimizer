WITH 
adunit_table AS (
  SELECT
    receiptTimeMillis,
    -- auction hour, measured from start_time (starts from 1)
    TIMESTAMP_DIFF(receiptTimeMillis, TIMESTAMP("{start_time}"), HOUR) as auction_hour,
    CAST(JSON_EXTRACT_SCALAR(optimizerConfig, "$.bidderTimeout.n") as INT64) as bidderTimeout,
    adUnits
  FROM `ox-datascience-devint.prebid.auctions_raw_lainey_gossip`
  WHERE 
    receiptTimeMillis >= timestamp("{start_time}")
    AND receiptTimeMillis < timestamp("{end_time}")
    AND configID = "d385ba19-47da-48e9-ab1b-cdfb4149118b"
    AND optimizerConfig IS NOT NULL
    AND testCode = "ds_optimizer"
    -- TODO: remove after page refresh is implemented
    -- Ignoring sessions that lasted longer then 30 minutes (1800 secs)
    -- Ignoring sessions without sessionSeconds
    AND json_extract_scalar(optimizerConfig, "$.sessionSeconds") IS NOT NULL
    AND IFNULL(cast(json_extract_scalar(optimizerConfig, "$.sessionSeconds") AS INT64), 10000) < 3600
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
SELECT
  auction_hour,
  bidderTimeout,
  win,
  pubrev
FROM win_cpm_table