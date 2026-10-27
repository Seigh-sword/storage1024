//! Blocking Rust client for the Storage1024 API.

use reqwest::blocking::{multipart, Client};
use serde::{Deserialize, Serialize};

pub struct Storage1024 {
    api_base: String,
    token: String,
    user_id: String,
    client: Client,
}

#[derive(Serialize)]
struct GVData<'a> {
    alias: &'a str,
    value: &'a str,
}

#[derive(Deserialize)]
struct GVResponse {
    value: String,
}

fn path_segment(value: &str) -> String {
    let mut out = String::new();
    for byte in value.bytes() {
        match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(byte as char)
            }
            _ => out.push_str(&format!("%{:02X}", byte)),
        }
    }
    out
}

impl Storage1024 {
    pub fn new() -> Self {
        Self {
            api_base: "https://storage1024.onrender.com/api".to_string(),
            token: String::new(),
            user_id: String::new(),
            client: Client::new(),
        }
    }

    pub fn set_api_base(&mut self, api_base: &str) {
        self.api_base = api_base.trim_end_matches('/').to_string();
    }

    pub fn set_token(&mut self, token: &str) {
        self.token = token.to_string();
    }

    pub fn set_user_id(&mut self, user_id: &str) {
        self.user_id = user_id.to_string();
    }

    fn project_url(&self, suffix: &str) -> String {
        format!(
            "{}/projects/{}{}",
            self.api_base,
            path_segment(&self.user_id),
            suffix
        )
    }

    fn auth(&self) -> String {
        format!("Bearer {}", self.token)
    }

    pub fn get_gv(&self, name: &str) -> Result<String, Box<dyn std::error::Error>> {
        let url = self.project_url(&format!("/gv/{}", path_segment(name)));
        let response = self
            .client
            .get(url)
            .header("Authorization", self.auth())
            .send()?
            .error_for_status()?;
        let parsed: GVResponse = response.json()?;
        Ok(parsed.value)
    }

    pub fn add_gv(&self, name: &str, value: &str) -> Result<(), Box<dyn std::error::Error>> {
        let url = self.project_url("/gv");
        let data = GVData {
            alias: name,
            value,
        };
        self.client
            .post(url)
            .header("Authorization", self.auth())
            .json(&data)
            .send()?
            .error_for_status()?;
        Ok(())
    }

    pub fn upload_file(
        &self,
        alias: &str,
        file_path: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let url = self.project_url("/upload");
        let form = multipart::Form::new()
            .text("alias", alias.to_string())
            .file("file", file_path)?;
        self.client
            .post(url)
            .header("Authorization", self.auth())
            .multipart(form)
            .send()?
            .error_for_status()?;
        Ok(())
    }

    pub fn get_file(&self, alias: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let url = self.project_url(&format!("/files/{}", path_segment(alias)));
        let response = self
            .client
            .get(url)
            .header("Authorization", self.auth())
            .send()?
            .error_for_status()?;
        Ok(response.bytes()?.to_vec())
    }
}

impl Default for Storage1024 {
    fn default() -> Self {
        Self::new()
    }
}
