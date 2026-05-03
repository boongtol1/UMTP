TEST_LISTINGS = [
    {
        "title": "맥북에어 M1 8GB 256GB 급처",
        "listing_price_krw": 430000,
    },
    {
        "title": "맥북에어 M1 8GB 256GB 상태좋음",
        "listing_price_krw": 520000,
    },
    {
        "title": "맥북에어 M1 8기가 256기가 판매",
        "listing_price_krw": 450000,
    },
    {
        "title": "맥북프로 M2 16GB 512GB 판매",
        "listing_price_krw": 900000,
    },
]


def main():
    for index, listing in enumerate(TEST_LISTINGS, start=1):
        print(f"[{index}] {listing['title']}")
        print(f"입력 매물가: {listing['listing_price_krw']}원")
        print()


if __name__ == "__main__":
    main()
