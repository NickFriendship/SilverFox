WITH DataWithPreviousTime AS (
    SELECT *,
           LAG(datetime) OVER (ORDER BY datetime) AS PreviousTime
    FROM [PSV].[dbo].[sensor_data]
),
DataWithStreamId AS (
    SELECT *,
           SUM(CASE WHEN DATEDIFF(SECOND, PreviousTime, datetime) <= 1 THEN 0 ELSE 1 END) OVER (ORDER BY datetime) AS StreamId
    FROM DataWithPreviousTime
)
SELECT StreamId,
       MIN(datetime) AS StreamStart,
       MAX(datetime) AS StreamEnd,
       DATEDIFF(SECOND, MIN(datetime), MAX(datetime)) AS StreamDuration
FROM DataWithStreamId
GROUP BY StreamId
ORDER BY StreamStart DESC;