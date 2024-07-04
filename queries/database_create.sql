USE [PSV]
GO
/****** Object:  Table [dbo].[measurement]    Script Date: 3-7-2024 11:01:43 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[measurement](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[player_id] [int] NOT NULL,
	[shimmer_id] [int] NULL,
	[event] [nchar](10) NOT NULL,
	[note] [ntext] NULL,
	[datetime] [datetime] NOT NULL,
 CONSTRAINT [PK_measurement] PRIMARY KEY CLUSTERED
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[player]    Script Date: 3-7-2024 11:01:43 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[player](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[name] [nchar](50) NOT NULL,
 CONSTRAINT [PK_player] PRIMARY KEY CLUSTERED
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UNQIUE_player] UNIQUE NONCLUSTERED
(
	[name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[sensor_data]    Script Date: 3-7-2024 11:01:43 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[sensor_data](
	[datetime] [datetime] NOT NULL,
	[shimmer_id] [int] NOT NULL,
	[data_timestamp] [int] NOT NULL,
	[gsr_raw] [int] NOT NULL,
	[ppg_raw] [int] NOT NULL,
 CONSTRAINT [PK_sensor_data] PRIMARY KEY CLUSTERED
(
	[datetime] ASC,
	[shimmer_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[shimmer]    Script Date: 3-7-2024 11:01:43 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[shimmer](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[name] [nchar](50) NOT NULL,
	[port] [nvarchar](5) NULL,
	[battery_perc] [float] NULL,
 CONSTRAINT [PK_shimmer] PRIMARY KEY CLUSTERED
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [IX_shimmer] UNIQUE NONCLUSTERED
(
	[name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
ALTER TABLE [dbo].[measurement] ADD  CONSTRAINT [DF_measurement_datetime]  DEFAULT (getdate()) FOR [datetime]
GO
ALTER TABLE [dbo].[sensor_data] ADD  CONSTRAINT [DF_sensor_data_datetime]  DEFAULT (getdate()) FOR [datetime]
GO
ALTER TABLE [dbo].[measurement]  WITH CHECK ADD  CONSTRAINT [FK_measurement_player] FOREIGN KEY([player_id])
REFERENCES [dbo].[player] ([id])
GO
ALTER TABLE [dbo].[measurement] CHECK CONSTRAINT [FK_measurement_player]
GO
ALTER TABLE [dbo].[measurement]  WITH CHECK ADD  CONSTRAINT [FK_measurement_shimmer] FOREIGN KEY([shimmer_id])
REFERENCES [dbo].[shimmer] ([id])
GO
ALTER TABLE [dbo].[measurement] CHECK CONSTRAINT [FK_measurement_shimmer]
GO
ALTER TABLE [dbo].[sensor_data]  WITH CHECK ADD  CONSTRAINT [FK_sensor_data_shimmer] FOREIGN KEY([shimmer_id])
REFERENCES [dbo].[shimmer] ([id])
GO
ALTER TABLE [dbo].[sensor_data] CHECK CONSTRAINT [FK_sensor_data_shimmer]
GO
