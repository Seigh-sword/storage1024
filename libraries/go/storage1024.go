package storage1024

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
)

type Storage1024 struct {
	APIBase string
	Token   string
	UserID  string
}

func New() *Storage1024 {
	return &Storage1024{
		APIBase: "https://storage1024.onrender.com/api",
	}
}

func (s *Storage1024) SetToken(token string) {
	s.Token = token
}

func (s *Storage1024) SetUserID(userID string) {
	s.UserID = userID
}

func (s *Storage1024) GetGV(name string) (string, error) {
	url := fmt.Sprintf("%s/projects/%s/gv/%s", s.APIBase, s.UserID, name)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("Authorization", "Bearer "+s.Token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		Value string `json:"value"`
	}
	json.NewDecoder(resp.Body).Decode(&result)
	return result.Value, nil
}

func (s *Storage1024) AddGV(name, value string) error {
	url := fmt.Sprintf("%s/projects/%s/gv", s.APIBase, s.UserID)
	data := map[string]string{"alias": name, "value": value}
	jsonData, _ := json.Marshal(data)

	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	req.Header.Set("Authorization", "Bearer "+s.Token)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func (s *Storage1024) UploadFile(alias, filePath string) error {
	url := fmt.Sprintf("%s/projects/%s/upload", s.APIBase, s.UserID)
	file, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, _ := writer.CreateFormFile("file", filePath)
	io.Copy(part, file)
	writer.WriteField("alias", alias)
	writer.Close()

	req, _ := http.NewRequest("POST", url, body)
	req.Header.Set("Authorization", "Bearer "+s.Token)
	req.Header.Set("Content-Type", writer.FormDataHeader())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}
