package storage

import (
    "io"
    "os"
    "path/filepath"
)

type VideoStore struct {
    BaseDir string
}

func (s *VideoStore) Save(filename string, r io.Reader) (string, error) {
    path := filepath.Join(s.BaseDir, filename)
    f, err := os.Create(path)
    if err != nil {
        return "", err
    }
    defer f.Close()

    _, err = io.Copy(f, r)
    return path, err
}
