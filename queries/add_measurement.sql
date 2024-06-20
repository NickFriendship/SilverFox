-- Declare the variables
DECLARE @start_datetime datetime, @end_datetime datetime;

-- Declare the CTEs before the SELECT statement
WITH DataWithPreviousTime AS (
    SELECT *,
           LAG(datetime) OVER (ORDER BY datetime) AS PreviousTime
    FROM [PSV].[dbo].[sensor_data]
),
DataWithStreamId AS (
    SELECT *,
           SUM(CASE WHEN DATEDIFF(SECOND, PreviousTime, datetime) <= 1 THEN 0 ELSE 1 END) OVER (ORDER BY datetime) AS StreamId
    FROM DataWithPreviousTime
),
StreamData AS (
    SELECT StreamId,
           MIN(datetime) AS StreamStart,
           MAX(datetime) AS StreamEnd
    FROM DataWithStreamId
    WHERE StreamId = 125
    GROUP BY StreamId
)
-- Now you can use the CTE in the SELECT statement
SELECT @start_datetime = StreamStart, @end_datetime = StreamEnd
FROM StreamData;

-- Insert the new measurements into the measurement table
INSERT INTO [PSV].[dbo].[measurement] (shimmer_id, player_id, datetime, event)
VALUES (3, 3, @start_datetime, 'fake_start'),
       (3, 3, @end_datetime, 'fake_end');