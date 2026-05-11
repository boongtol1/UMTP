from db import get_connection
from macbook_air_units import calculate_rule_based_fair_price, generate_macbook_air_units


DEFAULT_USER_ID = "test_user"
DEFAULT_ALERT_DROP_RATE_PERCENT = 20


def upsert_user_fair_price(cursor, user_id, unit, fair_price_krw):
    cursor.execute(
        """
        INSERT INTO user_fair_prices (
            user_id,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            alert_drop_rate_percent
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            fair_price_krw = VALUES(fair_price_krw),
            alert_drop_rate_percent = VALUES(alert_drop_rate_percent)
        """,
        (
            user_id,
            unit["product_type"],
            unit["chip"],
            unit["screen_inch"],
            unit["ram_gb"],
            unit["ssd_gb"],
            fair_price_krw,
            DEFAULT_ALERT_DROP_RATE_PERCENT,
        ),
    )


def main():
    connection = None
    cursor = None
    try:
        units = generate_macbook_air_units()
        user_id = DEFAULT_USER_ID

        print("MacBook Air 공정가 seed 시작")
        print(f"user_id: {user_id}")
        print(f"생성된 조합 수: {len(units)}")

        connection = get_connection()
        cursor = connection.cursor()

        for unit in units:
            fair_price_krw = calculate_rule_based_fair_price(
                chip=unit["chip"],
                screen_inch=unit["screen_inch"],
                ram_gb=unit["ram_gb"],
                ssd_gb=unit["ssd_gb"],
            )
            upsert_user_fair_price(
                cursor=cursor,
                user_id=user_id,
                unit=unit,
                fair_price_krw=fair_price_krw,
            )

        connection.commit()
        print(f"저장/업데이트 완료: {len(units)}개")
    except Exception as exc:
        print(f"seed 실패: {exc}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
