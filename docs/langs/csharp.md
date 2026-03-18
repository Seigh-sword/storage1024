# C#

Integrate with .NET using the native client class.

### Installation

Include `Storage1024.cs` in your project.

### Usage

```csharp
using Storage1024Lib;

var s1024 = new Storage1024();
s1024.SetUserID("YOUR_PROJECT_ID");
s1024.SetToken("YOUR_TOKEN");

// Read a variable
string score = await s1024.GetGV("score");
Console.WriteLine($"Score: {score}");

// Write a variable
await s1024.AddGV("score", "9001");
```

### Manual HttpClient Usage

```csharp
using System.Net.Http.Headers;

var client = new HttpClient();
client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", "TOKEN");

var response = await client.GetAsync("https://storage1024.onrender.com/api/projects/ID/gv/score");
var body = await response.Content.ReadAsStringAsync();
```
