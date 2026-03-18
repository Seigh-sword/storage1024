#ifndef STORAGE1024_H
#define STORAGE1024_H

#include <string>
#include <curl/curl.h>

class Storage1024 {
private:
    std::string apiBase = "https://storage1024.onrender.com/api";
    std::string token;
    std::string userID;

public:
    void set_token(const std::string& t) { token = t; }
    void set_userID(const std::string& id) { userID = id; }

    static size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
        ((std::string*)userp)->append((char*)contents, size * nmemb);
        return size * nmemb;
    }

    std::string get_gv(const std::string& name) {
        CURL* curl = curl_easy_init();
        std::string readBuffer;
        if(curl) {
            std::string url = apiBase + "/projects/" + userID + "/gv/" + name;
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            struct curl_slist* headers = NULL;
            headers = curl_slist_append(headers, ("Authorization: Bearer " + token).c_str());
            curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
            curl_easy_perform(curl);
            curl_easy_cleanup(curl);
        }
        return readBuffer;
    }

    std::string add_gv(const std::string& name, const std::string& value) {
        CURL* curl = curl_easy_init();
        std::string readBuffer;
        if(curl) {
            std::string url = apiBase + "/projects/" + userID + "/gv";
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            struct curl_slist* headers = NULL;
            headers = curl_slist_append(headers, ("Authorization: Bearer " + token).c_str());
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
            std::string data = "{\"alias\":\"" + name + "\", \"value\":\"" + value + "\"}";
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
            curl_easy_perform(curl);
            curl_easy_cleanup(curl);
        }
        return readBuffer;
    }
};

#endif
