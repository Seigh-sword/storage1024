using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;

namespace Storage1024Lib
{
    public class Storage1024
    {
        private string apiBase = "https://storage1024.onrender.com/api";
        private string token;
        private string userID;
        private static readonly HttpClient client = new HttpClient();

        public void SetToken(string t) => token = t;
        public void SetUserID(string id) => userID = id;

        public async Task<string> GetGV(string name)
        {
            var request = new HttpRequestMessage(HttpMethod.Get, $"{apiBase}/projects/{userID}/gv/{name}");
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            var response = await client.SendAsync(request);
            return await response.Content.ReadAsStringAsync();
        }

        public async Task<string> AddGV(string name, string value)
        {
            var request = new HttpRequestMessage(HttpMethod.Post, $"{apiBase}/projects/{userID}/gv");
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            var json = $"{{\"alias\":\"{name}\", \"value\":\"{value}\"}}";
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await client.SendAsync(request);
            return await response.Content.ReadAsStringAsync();
        }
    }
}
