package main

import "testing"

func TestStatus(t *testing.T) {
	if got := Status(); got != "ok" {
		t.Fatalf("Status() = %q, want ok", got)
	}
}
