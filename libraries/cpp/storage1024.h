#ifndef STORAGE1024_H
#define STORAGE1024_H

// Header-only C++ client for Storage1024. Link with -lcurl.
//   g++ main.cpp -lcurl -o main

#include <curl/curl.h>
#include <cctype>
#include <iomanip>
#include <sstream>
#include <string>

class Storage1024 {
private:
    std::string apiBase = "https://storage1024.onrender.com/api";
    std::string token;
    std::string userID;

    static std::string jsonEscape(const std::string& value) {
        std::ostringstream out;
        out << '"';
        for (unsigned char c : value) {
            switch (c) {
                case '"': out << "\\\""; break;
                case '\\': out << "\\\\"; break;
                case '\n': out << "\\n"; break;
                case '\r': out << "\\r"; break;
                case '\t': out << "\\t"; break;
                default:
                    if (c < 0x20) out << "\\u" << std::hex << std::setw(4)
                                       << std::setfill('0') << (int)c << std::dec;
                    else out << c;
            }
        }
        return out.str() + '"';
    }

    static std::string pathEscape(const std::string& value) {
        static const char* hex = "0123456789ABCDEF";
        std::string out;
        for (unsigned char c : value) {
            if (std::isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') out += c;
            else { out += '%'; out += hex[c >> 4]; out += hex[c & 15]; }
        }
        return out;
    }

    std::string projectUrl(const std::string& suffix) const {
        return apiBase + "/projects/" + pathEscape(userID) + suffix;
    }

    std::string request(const std::string& url, const std::string& method,
                        const std::string& body, const std::string& contentType) const {
        CURL* curl = curl_easy_init();
        if (!curl) return "";
        std::string readBuffer;
        struct curl_slist* headers = NULL;
        headers = curl_slist_append(headers, ("Authorization: Bearer " + token).c_str());
        if (!contentType.empty())
            headers = curl_slist_append(headers, ("Content-Type: " + contentType).c_str());

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        if (method == "POST") {
            curl_easy_setopt(curl, CURLOPT_POST, 1L);
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
            curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)body.size());
        } else if (method == "DELETE") {
            curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "DELETE");
        }
        CURLcode code = curl_easy_perform(curl);
        long status = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
        curl_slist_free_all(headers);   // the old code leaked this on every call
        curl_easy_cleanup(curl);
        if (code != CURLE_OK || status < 200 || status >= 300) return "";
        return readBuffer;
    }

    static std::string extractValue(const std::string& json) {
        const std::string key = "\"value\"";
        size_t at = json.find(key);
        if (at == std::string::npos) return "";
        size_t start = json.find('"', json.find(':', at + key.size()) + 1);
        if (start == std::string::npos) return "";
        std::string out;
        for (size_t i = start + 1; i < json.size(); ++i) {
            char c = json[i];
            if (c == '"') return out;
            if (c == '\\' && i + 1 < json.size()) {
                char n = json[++i];
                out += (n == 'n') ? '\n' : (n == 'r') ? '\r' : (n == 't') ? '\t' : n;
            } else out += c;
        }
        return out;
    }

public:
    void set_api_base(const std::string& url) { apiBase = url; }
    void set_token(const std::string& t) { token = t; }
    void set_userID(const std::string& id) { userID = id; }

    static size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
        ((std::string*)userp)->append((char*)contents, size * nmemb);
        return size * nmemb;
    }

    std::string get_gv(const std::string& name) {
        return extractValue(request(projectUrl("/gv/" + pathEscape(name)), "GET", "", ""));
    }

    std::string add_gv(const std::string& name, const std::string& value) {
        std::string data = "{\"alias\":" + jsonEscape(name) +
                           ", \"value\":" + jsonEscape(value) + "}";
        return request(projectUrl("/gv"), "POST", data, "application/json");
    }

    std::string gv_json() {
        return request(projectUrl("/gv"), "GET", "", "");
    }

    std::string delete_gv(const std::string& name) {
        return request(projectUrl("/gv/" + pathEscape(name)), "DELETE", "", "");
    }
};

#endif
