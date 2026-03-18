use reqwest::blocking::{Client, multipart};
use serde::{Deserialize, Serialize};

pub struct Storage1024 {
    api_base: String,
    token: String,
    user_id: String,
}

#[derive(Serialize, Deserialize)]
struct GVData {
    alias: String,
    value: String,
}

#[derive(Deserialize)]
struct GVResponse {
    value: String,
}

impl Storage1024 {
    pub fn new() -> Self {
        Self {
            api_base: "https://storage1024.onrender.com/api".to_string(),
            token: String::new(),
            user_id: String::new(),
        }
    }

    pub fn set_token(&mut self, token: &str) {
        self.token = token.to_string();
    }

    pub fn set_user_id(&mut self, user_id: &str) {
        self.user_id = user_id.to_string();
    }

    pub fn get_gv(&self, name: &str) -> Result<String, Box<dyn std::error::Error>> {
        let url = format!("{}/projects/{}/gv/{}", self.api_base, self.user_id, name);
        let client = Client::new();
        let resp = client.get(url)
            .header("Authorization", format!("Bearer {}", self.token))
            .send()?
            .json::<GVResponse>()?;
        Ok(resp.value)
    }

    pub fn add_gv(&self, name: &str, value: &str) -> Result<(), Box<dyn std::error::Error>> {
        let url = format!("{}/projects/{}/gv", self.api_base, self.user_id);
        let data = GVData { alias: name.to_string(), value: value.to_string() };
        let client = Client::new();
        client.post(url)
            .header("Authorization", format!("Bearer {}", self.token))
            .json(&data)
            .send()?;
        Ok(())
    }

    pub fn upload_file(&self, alias: &str, file_path: &str) -> Result<(), Box<dyn std::error::Error>> {
        let url = format!("{}/projects/{}/upload", self.api_base, self.user_id);
        let form = multipart::Form::new()
            .text("alias", alias.to_string())
            .file("file", file_path)?;
        
        let client = Client::new();
        client.post(url)
            .header("Authorization", format!("Bearer {}", self.token))
            .multipart(form)
            .send()?;
        Ok(())
    }
}
