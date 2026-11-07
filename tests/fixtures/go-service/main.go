package main

import (
	"fmt"
	"net/http"
)

// Status returns the health message served at /health.
func Status() string { return "ok" }

func main() {
	http.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) { fmt.Fprint(w, Status()) })
	_ = http.ListenAndServe(":8080", nil)
}
