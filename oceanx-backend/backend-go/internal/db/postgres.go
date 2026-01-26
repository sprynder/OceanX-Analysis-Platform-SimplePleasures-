package db

import (
    "context"
    "log"

    "github.com/jackc/pgx/v5"
)

func Connect(dsn string) *pgx.Conn {
    conn, err := pgx.Connect(context.Background(), dsn)
    if err != nil {
        log.Fatal(err)
    }
    return conn
}
