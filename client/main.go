package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"

	"github.com/joho/godotenv"
)

type runRequest struct {
	Prompt string `json:"prompt"`
	SessionID string `json:"session_id,omitempty"`
}

type runResponse struct {
	Content string `json:"content"`
	Warning *string `json:"Warning"`
}

func main() {
	_ = godotenv.Load()
	baseURL := os.Getenv("AGNO_URL")
	if baseURL == "" {
		baseURL = "http://localhost:8000"
	}
 
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: agent \"your prompt\"")
		os.Exit(1)
	}
 
	body, _ := json.Marshal(runRequest{Prompt: strings.Join(os.Args[1:], " ")})
    resp, err := http.Post(baseURL+"/agent/run", "application/json", bytes.NewReader(body))
    if err != nil {
        fmt.Fprintln(os.Stderr, "request failed:", err)
        os.Exit(1)
    }
	defer resp.Body.Close()
 
	if resp.StatusCode != http.StatusOK {
		fmt.Fprintf(os.Stderr, "server returned %s\n", resp.Status)
		os.Exit(1)
	}
 
	var out runResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		fmt.Fprintln(os.Stderr, "decode failed:", err)
		os.Exit(1)
	}
	if out.Warning != nil {
		fmt.Fprintf(os.Stderr, "⚠ %s\n\n", *out.Warning)
	}
	fmt.Println(out.Content)
}
