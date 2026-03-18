<?php

namespace Storage1024;

class Storage1024 {
    private string $apiBase = "https://storage1024.onrender.com/api";
    private string $token = "";
    private string $userID = "";

    public function setToken(string $token): void {
        $this->token = $token;
    }

    public function setUserID(string $userID): void {
        $this->userID = $userID;
    }

    public function getGV(string $name): string {
        $url = "{$this->apiBase}/projects/{$this->userID}/gv/{$name}";
        $options = [
            'http' => [
                'header' => "Authorization: Bearer {$this->token}\r\n"
            ]
        ];
        $context = stream_context_create($options);
        $response = file_get_contents($url, false, $context);
        $data = json_decode($response, true);
        return $data['value'] ?? "";
    }

    public function addGV(string $name, string $value): bool {
        $url = "{$this->apiBase}/projects/{$this->userID}/gv";
        $data = json_encode(['alias' => $name, 'value' => $value]);
        $options = [
            'http' => [
                'header' => "Authorization: Bearer {$this->token}\r\n" .
                            "Content-Type: application/json\r\n",
                'method' => 'POST',
                'content' => $data
            ]
        ];
        $context = stream_context_create($options);
        $response = file_get_contents($url, false, $context);
        return $response !== false;
    }

    public function uploadFile(string $alias, string $filePath): bool {
        if (!file_exists($filePath)) return false;

        $url = "{$this->apiBase}/projects/{$this->userID}/upload";
        $curl = curl_init();
        
        $cFile = new \CURLFile($filePath);
        $postData = [
            'file' => $cFile,
            'alias' => $alias
        ];

        curl_setopt($curl, CURLOPT_URL, $url);
        curl_setopt($curl, CURLOPT_POST, true);
        curl_setopt($curl, CURLOPT_POSTFIELDS, $postData);
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($curl, CURLOPT_HTTPHEADER, [
            "Authorization: Bearer {$this->token}"
        ]);

        $response = curl_exec($curl);
        curl_close($curl);
        
        return $response !== false;
    }
}
