USE UMTP_RB;

-- 실리콘 Mac Studio mac_fair_prices 시드
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
-- 대상: M1 Max/Ultra, M2 Max/Ultra, M4 Max, M3 Ultra.
-- screen_inch=0은 내장 화면이 없음을 뜻한다. 외부 디스플레이 가격은 포함하지 않는다.
-- Mac Studio의 M3 Max/M4 Ultra 모델을 임의로 만들지 않는다.
-- M5 Max/Ultra는 Apple 현행 사양 페이지에 있으나 이번 중고나라 검색에서
-- 본체 판매 표본을 확보하지 못해 이 파일의 가격 행에서 제외했다.
-- M3 Ultra RAM은 확인된 96/256/512GB만 포함. 512GB는 과거 출고 옵션 포함.
-- M4 Max 48/64/128GB는 40코어 GPU 모델, M2 Max 96GB는 38코어 GPU 모델에 해당.
--
-- 주요 표본(단위 원; RAM/SSD GB):
-- S01 M1 Max 32/512: 1700000,1900000 -> 1800000
-- https://web.joongna.com/product/225029615
-- https://web.joongna.com/product/229902692
-- S02 M1 Max 64/1024: 3400000 -> 3200000(L, 단일 고호가를 소폭 보정)
-- https://web.joongna.com/product/231120116
-- S03 M1 Ultra 128/2048: 7800000 -> 7800000(L, 단일 표본 잠정 기준)
-- https://web.joongna.com/product/230367694
-- S04 M2 Max 32/512: 2200000; 64/1024: 2350000
-- https://web.joongna.com/product/232478746
-- https://web.joongna.com/product/228516907
-- S05 M2 Ultra 192/8192: 18000000 -> 18000000(L, 단일 고호가 잠정 기준)
-- https://web.joongna.com/product/231627689
-- S06 M4 Max 36/1024: 3450000,3550000 -> 3500000
-- https://web.joongna.com/product/232077123
-- https://web.joongna.com/product/232482572
-- S07 M4 Max 48/1024: 4900000; 64/1024: 5500000,5600000,5800000
-- https://web.joongna.com/product/231926909
-- https://web.joongna.com/product/231886520
-- https://web.joongna.com/product/232514970
-- https://web.joongna.com/product/231823957
-- S08 M4 Max 128/1024: 7100000(AppleCare+),8200000 -> 기본 중고 7500000
-- https://web.joongna.com/product/232321444
-- https://web.joongna.com/product/231886583
-- S09 M3 Ultra 96/1024 미개봉+AppleCare+ 8500000 -> 중고 8000000 추정
-- https://web.joongna.com/product/231707043
-- S10 M3 Ultra 256/1024: 현재 목록 13000000(과거 검색 캐시 15000000)
-- https://web.joongna.com/product/232216893
-- S11 M3 Ultra 512/2048: 25000000(AppleCare+) -> 기본 중고 24500000 추정
-- https://web.joongna.com/product/232363964
--
-- 옵션 추정 가정(시장에서 직접 관측된 순수 옵션 프리미엄이 아님):
-- M1 Max SSD 512 기준 +0/+15/+40/+80/+150만원(512/1TB/2TB/4TB/8TB).
-- M1 Max RAM64 기준가는 S02에서 1TB 차액 15만원을 빼 305만원.
-- M1 Ultra 128/1TB 740만원(2TB 780만원에서 -40만원),64/1TB 450만원 가정.
-- M1 Ultra SSD 1TB 기준 +0/+40/+100/+200만원.
-- M2 Max 32/1TB 220만원,64/1TB 235만원,96/1TB 360만원 가정.
-- M2 Max 32/512는 220만원 단일 표본에서 옵션 역전을 완화해 205만원으로 보정.
-- M2 Max SSD 1TB 기준 -15/0/+30/+80/+160만원.
-- M2 Ultra 192/1TB 1400만원(8TB 표본에서 -400만원),128/1TB 1000만원,
-- 64/1TB 600만원 가정. SSD 1TB 기준 +0/+60/+160/+400만원.
-- M2 Ultra 전체는 단일 고호가에서 크게 외삽한 저신뢰 초기값이다.
-- M4 Max SSD 1TB 기준 -20/0/+40/+100/+200만원.
-- M3 Ultra SSD 1TB 기준 +0/+50/+130/+280/+550만원.
-- M3 Ultra 512/1TB 2400만원(2TB 보정가에서 -50만원).
-- 단일 Ultra 호가를 대표 시세로 확정할 수 없으며, L/E 행은 추가 표본 확보 시 우선 갱신.
-- 세대 간 가격 역전은 실제 표본 편차를 반영하므로 성능 순위로 가격을 정렬하지 않았다.
-- 사양: https://support.apple.com/ko-kr/111900
-- https://support.apple.com/ko-kr/111835
-- https://support.apple.com/en-us/122211
-- https://www.apple.com/newsroom/2025/03/apple-reveals-m3-ultra-taking-apple-silicon-to-a-new-extreme/
-- 신형 확인: https://www.apple.com/kr/mac-studio/specs/

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
-- Mac Studio M1 Max
('Mac Studio', 'M1 Max', 0, 32, 512, 1800000), -- O: S01
('Mac Studio', 'M1 Max', 0, 32, 1024, 1950000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 32, 2048, 2200000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 32, 4096, 2600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 32, 8192, 3300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 64, 512, 3050000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 64, 1024, 3200000), -- O/L: S02 보정
('Mac Studio', 'M1 Max', 0, 64, 2048, 3450000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 64, 4096, 3850000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Max', 0, 64, 8192, 4550000), -- E: 옵션 차액 가정으로 추정

-- Mac Studio M1 Ultra - 전체 저신뢰
('Mac Studio', 'M1 Ultra', 0, 64, 1024, 4500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Ultra', 0, 64, 2048, 4900000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Ultra', 0, 64, 4096, 5500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Ultra', 0, 64, 8192, 6500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Ultra', 0, 128, 1024, 7400000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Ultra', 0, 128, 2048, 7800000), -- O/L: S03 단일 호가
('Mac Studio', 'M1 Ultra', 0, 128, 4096, 8400000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M1 Ultra', 0, 128, 8192, 9400000), -- E: 옵션 차액 가정으로 추정

-- Mac Studio M2 Max
('Mac Studio', 'M2 Max', 0, 32, 512, 2050000), -- O/L: S04 옵션 관계 보정
('Mac Studio', 'M2 Max', 0, 32, 1024, 2200000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 32, 2048, 2500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 32, 4096, 3000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 32, 8192, 3800000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 64, 512, 2200000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 64, 1024, 2350000), -- O/L: S04
('Mac Studio', 'M2 Max', 0, 64, 2048, 2650000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 64, 4096, 3150000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 64, 8192, 3950000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 96, 512, 3450000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 96, 1024, 3600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 96, 2048, 3900000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 96, 4096, 4400000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Max', 0, 96, 8192, 5200000), -- E: 옵션 차액 가정으로 추정

-- Mac Studio M2 Ultra - 전체 저신뢰, 단일 고호가로부터 외삽
('Mac Studio', 'M2 Ultra', 0, 64, 1024, 6000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 64, 2048, 6600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 64, 4096, 7600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 64, 8192, 10000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 128, 1024, 10000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 128, 2048, 10600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 128, 4096, 11600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 128, 8192, 14000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 192, 1024, 14000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 192, 2048, 14600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 192, 4096, 15600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M2 Ultra', 0, 192, 8192, 18000000), -- O/L: S05 단일 고호가

-- Mac Studio M4 Max
('Mac Studio', 'M4 Max', 0, 36, 512, 3300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 36, 1024, 3500000), -- O: S06
('Mac Studio', 'M4 Max', 0, 36, 2048, 3900000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 36, 4096, 4500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 36, 8192, 5500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 48, 512, 4700000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 48, 1024, 4900000), -- O/L: S07
('Mac Studio', 'M4 Max', 0, 48, 2048, 5300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 48, 4096, 5900000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 48, 8192, 6900000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 64, 512, 5400000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 64, 1024, 5600000), -- O: S07
('Mac Studio', 'M4 Max', 0, 64, 2048, 6000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 64, 4096, 6600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 64, 8192, 7600000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 128, 512, 7300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 128, 1024, 7500000), -- O/L: S08 보증 보정
('Mac Studio', 'M4 Max', 0, 128, 2048, 7900000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 128, 4096, 8500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M4 Max', 0, 128, 8192, 9500000), -- E: 옵션 차액 가정으로 추정

-- Mac Studio M3 Ultra - 전체 저신뢰
('Mac Studio', 'M3 Ultra', 0, 96, 1024, 8000000), -- O/L: S09 미개봉/보증 보정
('Mac Studio', 'M3 Ultra', 0, 96, 2048, 8500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 96, 4096, 9300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 96, 8192, 10800000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 96, 16384, 13500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 256, 1024, 13000000), -- O/L: S10 단일 호가
('Mac Studio', 'M3 Ultra', 0, 256, 2048, 13500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 256, 4096, 14300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 256, 8192, 15800000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 256, 16384, 18500000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 512, 1024, 24000000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 512, 2048, 24500000), -- O/L: S11 보증 보정
('Mac Studio', 'M3 Ultra', 0, 512, 4096, 25300000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 512, 8192, 26800000), -- E: 옵션 차액 가정으로 추정
('Mac Studio', 'M3 Ultra', 0, 512, 16384, 29500000) -- E: 옵션 차액 가정으로 추정

ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw);
