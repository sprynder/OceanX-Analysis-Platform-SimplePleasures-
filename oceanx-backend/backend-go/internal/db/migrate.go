package db

import (
    "fmt"

    "github.com/golang-migrate/migrate/v4"
    _ "github.com/golang-migrate/migrate/v4/database/postgres"
    _ "github.com/golang-migrate/migrate/v4/source/file"
)

func RunMigrations(postgresDSN string) error {
    m, err := migrate.New(
        "file://migrations",
        postgresDSN,
    )
    if err != nil {
        return err
    }

    err = m.Up()
    if err != nil && err != migrate.ErrNoChange {
        return err
    }

    fmt.Println("Database migrations applied")
    return nil
}
