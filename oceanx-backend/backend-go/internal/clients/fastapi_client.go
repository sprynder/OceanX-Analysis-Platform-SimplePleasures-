package clients

import "net/http"

type FastAPIClient struct {
    BaseURL string
    Client  *http.Client
}

func NewFastAPIClient(base string) *FastAPIClient {
    return &FastAPIClient{
        BaseURL: base,
        Client:  &http.Client{},
    }
}
