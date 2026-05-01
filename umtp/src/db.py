import os

import mysql.connector
from dotenv import load_dotenv


REQUIRED_ENV_VARS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")


def get_db_config():
    load_dotenv()

    missing = [key for key in REQUIRED_ENV_VARS if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "DB 접속 정보가 없습니다. .env 파일을 만들고 다음 값을 설정하세요: "
            + ", ".join(missing)
        )

    db_port = os.getenv("DB_PORT", "3306")
    try:
        db_port_int = int(db_port)
    except ValueError as exc:
        raise RuntimeError("DB_PORT는 숫자여야 합니다.") from exc

    return {
        "host": os.getenv("DB_HOST"),
        "port": db_port_int,
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }


def get_connection():
    config = get_db_config()
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as exc:
        raise RuntimeError(f"MySQL 연결 실패: {exc}") from exc
