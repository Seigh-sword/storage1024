using System;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace Storage1024Lib
{
    /// <summary>Client for the Storage1024 REST API (.NET 5+).</summary>
    public class Storage1024
    {
        private string apiBase = "https://storage1024.onrender.com/api";
        private string token = "";
        private string userID = "";
        private static readonly HttpClient client = new HttpClient();

        public void SetToken(string t) => token = t ?? "";
        public void SetUserID(string id) => userID = id ?? "";
        public void SetApiBase(string url) => apiBase = (url ?? "").TrimEnd('/');

        private string ProjectUrl(string suffix = "") =>
            $"{apiBase}/projects/{Uri.EscapeDataString(userID)}{suffix}";

        private HttpRequestMessage Request(HttpMethod method, string url)
        {
            if (string.IsNullOrEmpty(token)) throw new InvalidOperationException("Token not set. Use SetToken()");
            if (string.IsNullOrEmpty(userID)) throw new InvalidOperationException("Project ID not set. Use SetUserID()");
            var request = new HttpRequestMessage(method, url);
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            return request;
        }

        private static async Task<string> Send(HttpRequestMessage request)
        {
            var response = await client.SendAsync(request);
            var body = await response.Content.ReadAsStringAsync();
            if (!response.IsSuccessStatusCode)
            {
                throw new HttpRequestException($"Storage1024 {(int)response.StatusCode}: {body}");
            }
            return body;
        }

        /// <summary>Returns the variable's value (not the raw JSON envelope).</summary>
        public async Task<string> GetGV(string name)
        {
            var request = Request(HttpMethod.Get, ProjectUrl($"/gv/{Uri.EscapeDataString(name)}"));
            var body = await Send(request);
            using var doc = JsonDocument.Parse(body);
            return doc.RootElement.TryGetProperty("value", out var value) ? value.GetString() ?? "" : "";
        }

        public async Task<string> AddGV(string name, string value)
        {
            var request = Request(HttpMethod.Post, ProjectUrl("/gv"));
            // JsonSerializer handles quotes, backslashes and newlines correctly;
            // string interpolation used to produce invalid JSON here.
            var json = JsonSerializer.Serialize(new { alias = name, value = value ?? "" });
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
            return await Send(request);
        }

        public async Task<string> ListGVs()
        {
            return await Send(Request(HttpMethod.Get, ProjectUrl("/gv")));
        }

        public async Task<string> UploadFile(string alias, string filePath)
        {
            if (!File.Exists(filePath)) throw new FileNotFoundException("File not found", filePath);
            var request = Request(HttpMethod.Post, ProjectUrl("/upload"));
            using var form = new MultipartFormDataContent();
            using var stream = File.OpenRead(filePath);
            form.Add(new StreamContent(stream), "file", Path.GetFileName(filePath));
            form.Add(new StringContent(alias), "alias");
            request.Content = form;
            return await Send(request);
        }
    }
}
