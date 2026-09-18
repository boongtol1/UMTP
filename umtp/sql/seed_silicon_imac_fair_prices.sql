USE UMTP_RB;

-- 실리콘 iMac mac_fair_prices 시드
-- 조사일: 2026-09-18 (한국). 중고나라 공개 검색 목록 및 일부 상세 판매글 기준.
-- 가격은 거래 완료 금액이 아니라 판매 호가를 참고한 초기 기준값이다.
-- 전수조사/검증된 실거래 중앙값이 아니다. 게시글 가격과 판매 상태는 변할 수 있다.
-- 구함/매입/교환전용/사기경고/파손/부품/주변기기/사양불명 매물은 기준 표본에서 제외.
-- 오래된 검색 캐시와 현재 목록의 가격이 다르면 현재 목록을 우선했다.
-- O: 동일 RAM/SSD 판매 표본을 참고해 정한 기준가(호가 그대로라는 뜻은 아님).
-- E: 직접 표본이 없어 아래 옵션 차액 가정으로 보간/외삽한 추정가.
-- L: 표본이 1개이거나 옵션/상태 보정 영향이 큰 저신뢰 기준가.
-- DB 구조를 유지하기 위해 근거/신뢰도/조회일은 SQL 주석에만 기록한다.
-- CPU/GPU 코어 수, 색상, 보증, 상태 차이는 키에 없어 별도 구분하지 않는다.
-- RAM은 동일 칩에서 출고 가능했던 옵션의 합집합이다. 1TB는 기존 파일처럼 1024GB.
-- 아래 INSERT는 기존 동일 사양의 fair_price_krw만 갱신하며 다른 제품 행을 삭제하지 않는다.
-- 대상: 24형 iMac M1(2021), M3(2023), M4(2024). Intel 모델 제외.
-- screen_inch=24. 기본 키보드/마우스/전원 포함, 정상 작동 중고 기준.
-- 2포트/4포트, GPU 등급, VESA/스탠드, 나노 텍스처는 별도 키가 없어 통합.
-- 2TB 등 상위 옵션은 4포트 모델에서 가능한 조합을 포함한다.
--
-- 주요 표본(단위 원; RAM/SSD GB):
-- I01 M1 8/256: 650000,700000,720000,700000 -> 기준 700000
-- https://web.joongna.com/product/231752680
-- https://web.joongna.com/product/231783439
-- https://web.joongna.com/product/230862085
-- https://web.joongna.com/product/229586904
-- I02 M1 16/256: 890000 -> 기준 850000(L, 근접 옵션과 평활화)
-- https://web.joongna.com/product/232399661
-- I03 M1 16/512: 930000,950000,1000000 -> 기준 950000
-- https://web.joongna.com/product/232504190
-- https://web.joongna.com/product/232476185
-- https://web.joongna.com/product/232466341
-- I04 M1 8/512: 850000,900000 -> 기준 850000(L, 오래된 표본)
-- https://web.joongna.com/product/190141193
-- https://web.joongna.com/product/227165854
-- I05 M1 16/1024: 1070000 -> 기준 1070000(L, 오래된 표본)
-- https://web.joongna.com/product/220566673
-- I06 M3 8/256: 1300000,900000,900000,1550000,1000000 -> 중앙값 1000000
-- https://web.joongna.com/product/232503857
-- https://web.joongna.com/product/232436282
-- https://web.joongna.com/product/232434571
-- https://web.joongna.com/product/223253503
-- https://web.joongna.com/product/231709425
-- I07 M3 8/512: 1350000 (검색 캐시); 16/512: 1630000(현재 목록)
-- https://web.joongna.com/search/아이맥%20m3
-- https://web.joongna.com/product/220562839
-- I08 M4 16/256: 1500000; 16/512: 2150000,2450000
-- https://web.joongna.com/product/231455075
-- https://web.joongna.com/product/232323418
-- https://web.joongna.com/product/230948488
-- I09 M4 32/1024: 2700000(나노 텍스처),3000000(AppleCare+) -> 기본 중고 2650000 추정
-- https://web.joongna.com/product/232153700
-- https://web.joongna.com/product/232164159
--
-- 옵션 가정: M1 512->1TB +12만원, 1->2TB +18만원.
-- M3 RAM 8->16 +25만원,16->24 +20만원; SSD 256->512 +35만원,
-- 512->1TB +15만원,1->2TB +25만원. 16/512는 163만원 표본을 160만원으로 반올림.
-- M4 16/512는 최신 215만원 호가를 우선한 저신뢰 기준. 256->512 차액에는
-- 8/10코어 및 포트 차이와 표본 편향도 섞이므로 순수 SSD 프리미엄으로 해석하지 않는다.
-- M4 RAM 16->24 +20만원,24->32 +20만원; SSD 512->1TB +15만원,1->2TB +25만원.
-- M4 32/1024는 부가 옵션 보정 후 265만원, 그 밖의 조합은 이 표와의 연속성을 보정.
-- 사양 참고: https://www.apple.com/kr/imac/specs/
-- https://www.apple.com/kr/newsroom/2023/10/apple-supercharges-24-inch-imac-with-new-m3-chip/

CREATE TABLE IF NOT EXISTS mac_fair_prices (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_type VARCHAR(100) NOT NULL,
  chip VARCHAR(50) NOT NULL,
  screen_inch INT NOT NULL,
  ram_gb INT NOT NULL,
  ssd_gb INT NOT NULL,
  fair_price_krw INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_mac_fair_price_spec (product_type, chip, screen_inch, ram_gb, ssd_gb)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO mac_fair_prices (
  product_type,
  chip,
  screen_inch,
  ram_gb,
  ssd_gb,
  fair_price_krw
)
VALUES
-- iMac M1
('iMac', 'M1', 24, 8, 256, 700000), -- O: I01
('iMac', 'M1', 24, 8, 512, 850000), -- O/L: I04
('iMac', 'M1', 24, 8, 1024, 970000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M1', 24, 8, 2048, 1150000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M1', 24, 16, 256, 850000), -- O/L: I02
('iMac', 'M1', 24, 16, 512, 950000), -- O: I03
('iMac', 'M1', 24, 16, 1024, 1070000), -- O/L: I05
('iMac', 'M1', 24, 16, 2048, 1250000), -- E: 옵션 차액 가정으로 추정

-- iMac M3
('iMac', 'M3', 24, 8, 256, 1000000), -- O: I06
('iMac', 'M3', 24, 8, 512, 1350000), -- O/L: I07 검색 캐시 표본
('iMac', 'M3', 24, 8, 1024, 1500000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 8, 2048, 1750000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 16, 256, 1250000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 16, 512, 1600000), -- O/L: I07
('iMac', 'M3', 24, 16, 1024, 1750000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 16, 2048, 2000000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 24, 256, 1450000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 24, 512, 1800000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 24, 1024, 1950000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M3', 24, 24, 2048, 2200000), -- E: 옵션 차액 가정으로 추정

-- iMac M4
('iMac', 'M4', 24, 16, 256, 1500000), -- O/L: I08
('iMac', 'M4', 24, 16, 512, 2150000), -- O/L: I08 최신 호가 우선
('iMac', 'M4', 24, 16, 1024, 2300000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 16, 2048, 2550000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 24, 256, 1700000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 24, 512, 2350000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 24, 1024, 2500000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 24, 2048, 2750000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 32, 256, 1900000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 32, 512, 2500000), -- E: 옵션 차액 가정으로 추정
('iMac', 'M4', 24, 32, 1024, 2650000), -- O/L: I09 보증/패널 옵션 보정
('iMac', 'M4', 24, 32, 2048, 2900000) -- E: 옵션 차액 가정으로 추정

ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw);
