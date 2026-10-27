<?php

namespace Storage1024;

/**
 * PHP client for Storage1024 (PHP 7.4+, ext-curl required).
 */
class Storage1024
{
    private string $apiBase = "https://storage1024.onrender.com/api";
    private string $token = "";
    private string $userID = "";

    public function setApiBase(string $url): void
    {
        $this->apiBase = rtrim($url, '/');
    }

    public function setToken(string $token): void
    {
        $this->token = $token;
    }

    public function setUserID(string $userID): void
    {
        $this->userID = $userID;
    }

    private function projectUrl(string $suffix = ''): string
    {
        return $this->apiBase . '/projects/' . rawurlencode($this->userID) . $suffix;
    }

    /** @return array{status:int, body:string} */
    private function request(string $method, string $url, $body = null, array $extraHeaders = []): array
    {
        $curl = curl_init($url);
        $headers = array_merge(["Authorization: Bearer {$this->token}"], $extraHeaders);
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => $method,
            CURLOPT_HTTPHEADER     => $headers,
            CURLOPT_TIMEOUT        => 120,
        ]);
        if ($body !== null) {
            curl_setopt($curl, CURLOPT_POSTFIELDS, $body);
        }
        $response = curl_exec($curl);
        $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
        $error = curl_error($curl);
        curl_close($curl);
        if ($response === false) {
            throw new \RuntimeException("Storage1024 request failed: {$error}");
        }
        if ($status < 200 || $status >= 300) {
            throw new \RuntimeException("Storage1024 {$status}: {$response}");
        }
        return ['status' => $status, 'body' => $response];
    }

    public function getGV(string $name): string
    {
        $response = $this->request('GET', $this->projectUrl('/gv/' . rawurlencode($name)));
        $data = json_decode($response['body'], true);
        return is_array($data) ? (string) ($data['value'] ?? '') : '';
    }

    /** @return array<string, mixed> */
    public function gvJson(): array
    {
        $response = $this->request('GET', $this->projectUrl('/gv'));
        $data = json_decode($response['body'], true);
        return is_array($data) ? $data : [];
    }

    public function addGV(string $name, string $value): bool
    {
        $payload = json_encode(['alias' => $name, 'value' => $value]);
        $this->request(
            'POST',
            $this->projectUrl('/gv'),
            $payload,
            ['Content-Type: application/json']
        );
        return true;
    }

    public function deleteGV(string $name): bool
    {
        $this->request('DELETE', $this->projectUrl('/gv/' . rawurlencode($name)));
        return true;
    }

    /** @return array<string, mixed> */
    public function uploadFile(string $alias, string $filePath): array
    {
        if (!is_file($filePath)) {
            throw new \RuntimeException("File not found: {$filePath}");
        }
        $payload = [
            'file'  => new \CURLFile($filePath, '', basename($filePath)),
            'alias' => $alias,
        ];
        $response = $this->request('POST', $this->projectUrl('/upload'), $payload);
        $data = json_decode($response['body'], true);
        return is_array($data) ? $data : [];
    }

    public function getFile(string $alias): string
    {
        return $this->request('GET', $this->projectUrl('/files/' . rawurlencode($alias)))['body'];
    }
}
