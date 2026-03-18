package com.storage1024

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.util.concurrent.CompletableFuture

class Storage1024 {
    private var apiBase = "https://storage1024.onrender.com/api"
    private var token = ""
    private var userID = ""
    private val client = HttpClient.newHttpClient()

    fun setToken(t: String) { this.token = t }
    fun setUserID(id: String) { this.userID = id }

    fun getGV(name: String): CompletableFuture<String> {
        val request = HttpRequest.newBuilder()
            .uri(URI.create("$apiBase/projects/$userID/gv/$name"))
            .header("Authorization", "Bearer $token")
            .GET()
            .build()

        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply { it.body() }
    }

    fun addGV(name: String, value: String): CompletableFuture<String> {
        val json = "{\"alias\":\"$name\", \"value\":\"$value\"}"
        val request = HttpRequest.newBuilder()
            .uri(URI.create("$apiBase/projects/$userID/gv"))
            .header("Authorization", "Bearer $token")
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build()

        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply { it.body() }
    }
}
