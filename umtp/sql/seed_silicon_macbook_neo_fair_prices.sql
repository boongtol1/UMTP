USE UMTP_RB;

-- MacBook Neo mac_fair_prices 시드
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
-- 대상: MacBook Neo 13형, A18 Pro, RAM 8GB, SSD 256/512GB.
-- Apple 공식 사양에서 확인되는 두 구성만 포함. RAM16/SSD1TB 행을 만들지 않는다.
-- 512GB 모델은 Touch ID 포함. 색상/사이클/부가 액세서리 프리미엄은 따로 가산하지 않는다.
-- 정상 작동, 배터리 양호, 기본 충전 구성품 포함 중고 기준.
--
-- N01 8/256 최근 중고 표본: 850000,900000,750000,850000,860000 -> 중앙값 850000
-- https://web.joongna.com/product/232005526
-- https://web.joongna.com/product/232506195
-- https://web.joongna.com/product/232450848
-- https://web.joongna.com/product/231654128
-- https://web.joongna.com/product/232195519
-- N02 8/512 최근 중고 표본: 900000,950000,760000,900000 -> 중앙값 900000
-- https://web.joongna.com/product/232517090
-- https://web.joongna.com/product/232456623
-- https://web.joongna.com/product/232505003
-- https://web.joongna.com/product/231919586
-- 미개봉, 사기경고글, 케이스, 다른 MacBook 교환글은 위 표본에서 제외했다.
-- 목록에 나타난 호가의 중앙값이며 거래 성사 여부와 판매자 진위는 검증하지 않았다.
-- 사양: https://www.apple.com/kr/macbook-neo/specs/

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
-- MacBook Neo A18 Pro
('MacBook Neo', 'A18 Pro', 13, 8, 256, 850000), -- O: N01 n=5 중앙값
('MacBook Neo', 'A18 Pro', 13, 8, 512, 900000) -- O: N02 n=4 중앙값

ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw);
