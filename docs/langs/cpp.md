# C / C++

Use the header-only C++ library or talk directly to the REST API using libcurl.

### Header-only Library

Include `storage1024.h` in your project.

```cpp
#include "storage1024.h"
#include <iostream>

int main() {
    Storage1024 s1024;
    s1024.set_userID("YOUR_PROJECT_ID");
    s1024.set_token("YOUR_TOKEN");

    // Read a variable
    std::string score = s1024.get_gv("score");
    std::cout << "Current Score: " << score << std::endl;

    // Write a variable
    s1024.add_gv("score", "9001");

    return 0;
}
```

### Manual libcurl Usage

If you prefer raw cURL calls in C:

```cpp
#include <curl/curl.h>

CURL *curl = curl_easy_init();
struct curl_slist *headers = NULL;
headers = curl_slist_append(headers, "Authorization: Bearer YOUR_TOKEN");

curl_easy_setopt(curl, CURLOPT_URL, "https://storage1024.onrender.com/api/projects/YOUR_ID/gv/score");
curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
curl_easy_perform(curl);
```
