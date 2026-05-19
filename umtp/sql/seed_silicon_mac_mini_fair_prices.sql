INSERT INTO mac_fair_prices (
  product_type,
  chip,
  screen_inch,
  ram_gb,
  ssd_gb,
  fair_price_krw
)
VALUES
-- Mac mini M1
('Mac mini', 'M1', 0, 8, 256, 370000),
('Mac mini', 'M1', 0, 8, 512, 450000),
('Mac mini', 'M1', 0, 8, 1024, 560000),
('Mac mini', 'M1', 0, 8, 2048, 700000),
('Mac mini', 'M1', 0, 16, 256, 460000),
('Mac mini', 'M1', 0, 16, 512, 540000),
('Mac mini', 'M1', 0, 16, 1024, 660000),
('Mac mini', 'M1', 0, 16, 2048, 820000),

-- Mac mini M2
('Mac mini', 'M2', 0, 8, 256, 480000),
('Mac mini', 'M2', 0, 8, 512, 560000),
('Mac mini', 'M2', 0, 8, 1024, 700000),
('Mac mini', 'M2', 0, 8, 2048, 950000),
('Mac mini', 'M2', 0, 16, 256, 600000),
('Mac mini', 'M2', 0, 16, 512, 660000),
('Mac mini', 'M2', 0, 16, 1024, 820000),
('Mac mini', 'M2', 0, 16, 2048, 1050000),
('Mac mini', 'M2', 0, 24, 256, 720000),
('Mac mini', 'M2', 0, 24, 512, 800000),
('Mac mini', 'M2', 0, 24, 1024, 980000),
('Mac mini', 'M2', 0, 24, 2048, 1300000),

-- Mac mini M2 Pro
('Mac mini', 'M2 Pro', 0, 16, 512, 850000),
('Mac mini', 'M2 Pro', 0, 16, 1024, 1050000),
('Mac mini', 'M2 Pro', 0, 16, 2048, 1300000),
('Mac mini', 'M2 Pro', 0, 16, 4096, 1650000),
('Mac mini', 'M2 Pro', 0, 16, 8192, 2200000),
('Mac mini', 'M2 Pro', 0, 32, 512, 1100000),
('Mac mini', 'M2 Pro', 0, 32, 1024, 1300000),
('Mac mini', 'M2 Pro', 0, 32, 2048, 1600000),
('Mac mini', 'M2 Pro', 0, 32, 4096, 2000000),
('Mac mini', 'M2 Pro', 0, 32, 8192, 2600000),

-- Mac mini M4
('Mac mini', 'M4', 0, 16, 256, 800000),
('Mac mini', 'M4', 0, 16, 512, 1000000),
('Mac mini', 'M4', 0, 16, 1024, 1250000),
('Mac mini', 'M4', 0, 16, 2048, 1550000),
('Mac mini', 'M4', 0, 24, 256, 980000),
('Mac mini', 'M4', 0, 24, 512, 1150000),
('Mac mini', 'M4', 0, 24, 1024, 1400000),
('Mac mini', 'M4', 0, 24, 2048, 1700000),
('Mac mini', 'M4', 0, 32, 256, 1150000),
('Mac mini', 'M4', 0, 32, 512, 1320000),
('Mac mini', 'M4', 0, 32, 1024, 1580000),
('Mac mini', 'M4', 0, 32, 2048, 1900000),

-- Mac mini M4 Pro
('Mac mini', 'M4 Pro', 0, 24, 512, 1850000),
('Mac mini', 'M4 Pro', 0, 24, 1024, 2250000),
('Mac mini', 'M4 Pro', 0, 24, 2048, 2600000),
('Mac mini', 'M4 Pro', 0, 24, 4096, 3150000),
('Mac mini', 'M4 Pro', 0, 24, 8192, 3900000),
('Mac mini', 'M4 Pro', 0, 48, 512, 2450000),
('Mac mini', 'M4 Pro', 0, 48, 1024, 2850000),
('Mac mini', 'M4 Pro', 0, 48, 2048, 3250000),
('Mac mini', 'M4 Pro', 0, 48, 4096, 3800000),
('Mac mini', 'M4 Pro', 0, 48, 8192, 4600000),
('Mac mini', 'M4 Pro', 0, 64, 512, 2850000),
('Mac mini', 'M4 Pro', 0, 64, 1024, 3250000),
('Mac mini', 'M4 Pro', 0, 64, 2048, 3700000),
('Mac mini', 'M4 Pro', 0, 64, 4096, 4300000),
('Mac mini', 'M4 Pro', 0, 64, 8192, 5200000)
ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw);