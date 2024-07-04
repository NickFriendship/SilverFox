WITH DataWithPreviousTime AS (
    SELECT *,
           LAG(datetime) OVER (ORDER BY datetime) AS PreviousTime
    FROM [dbo].[sensor_data]
),
DataWithStreamId AS (
    SELECT *,
           SUM(CASE WHEN DATEDIFF(SECOND, PreviousTime, datetime) <= 1 THEN 0 ELSE 1 END) OVER (ORDER BY datetime) AS StreamId
    FROM DataWithPreviousTime
),
StreamDetails AS (
    SELECT StreamId,
           MIN(datetime) AS StreamStart,
           MAX(datetime) AS StreamEnd
    FROM DataWithStreamId
    GROUP BY StreamId
),
StartGameStreams AS (
    SELECT
        s.StreamId,
        s.StreamStart,
        s.StreamEnd,
        sd.player_id,
        sd.shimmer_id,
        sd.note
    FROM StreamDetails s
    JOIN [dbo].[sensor_data] sd ON s.StreamStart = sd.datetime
    WHERE sd.note = 'start_game'
)
INSERT INTO [dbo].[sensor_data] (datetime, player_id, shimmer_id, note)
SELECT
    s.StreamEnd AS datetime,
    s.player_id,
    s.shimmer_id,
    'stop_game' AS note
FROM StartGameStreams s;