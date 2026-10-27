// Package storage1024 is a small client for the Storage1024 REST API.
package storage1024

import (
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Storage1024 struct {
	APIBase string
	Token   string
	UserID  string
	Client  *http.Client
}

func New() *Storage1024 {
	return &Storage1024{
		APIBase: "https://storage1024.onrender.com/api",
		Client:  &http.Client{Timeout: 10 * time.Minute},
	}
}

func (s *Storage1024) SetToken(token string)  { s.Token = token }
func (s *Storage1024) SetUserID(id string)    { s.UserID = id }
func (s *Storage1024) SetAPIBase(base string) { s.APIBase = strings.TrimRight(base, "/") }

func (s *Storage1024) httpClient() *http.Client {
	if s.Client != nil {
		return s.Client
	}
	return http.DefaultClient
}

func (s *Storage1024) endpoint(format string, args ...interface{}) string {
	return fmt.Sprintf("%s/projects/%s", strings.TrimRight(s.APIBase, "/"), url.PathEscape(s.UserID)) +
		fmt.Sprintf(format, args...)
}

func (s *Storage1024) newRequest(method, url, body string, contentType string) (*http.Request, error) {
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, url, reader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+s.Token)
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	return req, nil
}

func (s *Storage1024) do(req *http.Request) (*http.Response, error) {
	resp, err := s.httpClient().Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		defer resp.Body.Close()
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return nil, fmt.Errorf("storage1024 %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
	}
	return resp, nil
}

// GetGV returns one global variable.
func (s *Storage1024) GetGV(name string) (string, error) {
	endpoint := s.endpoint("/gv/%s", url.PathEscape(name))
	req, err := s.newRequest(http.MethodGet, endpoint, "", "")
	if err != nil {
		return "", err
	}
	resp, err := s.do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	var result struct {
		Value string `json:"value"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	return result.Value, nil
}

// AddGV creates or updates a global variable.
func (s *Storage1024) AddGV(name, value string) error {
	payload, err := json.Marshal(map[string]string{"alias": name, "value": value})
	if err != nil {
		return err
	}
	req, err := s.newRequest(http.MethodPost, s.endpoint("/gv"), string(payload), "application/json")
	if err != nil {
		return err
	}
	resp, err := s.do(req)
	if err != nil {
		return err
	}
	return resp.Body.Close()
}

// UploadFile streams a local file to the project. The old implementation sent
// multipart.Writer.FormDataHeader() as the request Content-Type, which is a
// part header, not a media type - the server could not parse the body.
func (s *Storage1024) UploadFile(alias, filePath string) (map[string]interface{}, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	pr, pw := io.Pipe()
	writer := multipart.NewWriter(pw)
	writeErr := make(chan error, 1)
	go func() {
		var err error
		part, err := writer.CreateFormFile("file", filepath.Base(filePath))
		if err == nil {
			_, err = io.Copy(part, file)
		}
		if err == nil {
			err = writer.WriteField("alias", alias)
		}
		if closeErr := writer.Close(); err == nil {
			err = closeErr
		}
		writeErr <- err
		pw.CloseWithError(err)
	}()

	req, err := http.NewRequest(http.MethodPost, s.endpoint("/upload"), pr)
	if err != nil {
		pr.CloseWithError(err)
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+s.Token)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	resp, err := s.do(req)
	if err != nil {
		pr.CloseWithError(err)
		<-writeErr
		return nil, err
	}
	defer resp.Body.Close()
	if err := <-writeErr; err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

// DownloadFile fetches a stored file into memory.
func (s *Storage1024) DownloadFile(alias string) ([]byte, error) {
	req, err := s.newRequest(http.MethodGet, s.endpoint("/files/%s", url.PathEscape(alias)), "", "")
	if err != nil {
		return nil, err
	}
	resp, err := s.do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

// ListGVs returns every global variable in the project.
func (s *Storage1024) ListGVs() (map[string]string, error) {
	req, err := s.newRequest(http.MethodGet, s.endpoint("/gv"), "", "")
	if err != nil {
		return nil, err
	}
	resp, err := s.do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}
