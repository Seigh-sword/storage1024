package com.storage1024

import java.net.URI
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.charset.StandardCharsets
import java.util.concurrent.CompletableFuture

/** Client for the Storage1024 REST API (JVM, Java 11+). */
class Storage1024 {
    private var apiBase = "https://storage1024.onrender.com/api"
    private var token = ""
    private var userID = ""
    private val client = HttpClient.newHttpClient()

    fun setToken(t: String) { token = t }
    fun setUserID(id: String) { userID = id }
    fun setApiBase(url: String) { apiBase = url.trimEnd('/') }

    private fun enc(value: String) =
        URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20")

    private fun jsonString(value: String): String = buildString {
        append('"')
        for (c in value) {
            when (c) {
                '"' -> append("\\\"")
                '\\' -> append("\\\\")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> if (c < ' ') append("\\u%04x".format(c.code)) else append(c)
            }
        }
        append('"')
    }

    private fun extractValue(json: String): String {
        val at = json.indexOf("\"value\"")
        if (at < 0) return ""
        val colon = json.indexOf(':', at + 7)
        if (colon < 0) return ""
        val start = json.indexOf('"', colon + 1)
        if (start < 0) return ""
        val out = StringBuilder()
        var i = start + 1
        while (i < json.length) {
            val c = json[i]
            if (c == '"') return out.toString()
            if (c == '\\' && i + 1 < json.length) {
                when (val n = json[++i]) {
                    'n' -> out.append('\n')
                    'r' -> out.append('\r')
                    't' -> out.append('\t')
                    else -> out.append(n)
                }
            } else out.append(c)
            i++
        }
        return out.toString()
    }

    private fun check(status: Int, body: String): String {
        if (status < 200 || status >= 300) error("Storage1024 $status: $body")
        return body
    }

    private fun projectUrl(suffix: String) = "$apiBase/projects/${enc(userID)}$suffix"

    private fun request(uri: URI) =
        HttpRequest.newBuilder(uri).header("Authorization", "Bearer $token")

    /** Returns the variable's value, not the JSON envelope. */
    fun getGV(name: String): CompletableFuture<String> {
        val request = request(URI.create(projectUrl("/gv/${enc(name)}"))).GET().build()
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply { check(it.statusCode(), extractValue(it.body())) }
    }

    fun listGVs(): CompletableFuture<String> {
        val request = request(URI.create(projectUrl("/gv"))).GET().build()
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply { check(it.statusCode(), it.body()) }
    }

    fun addGV(name: String, value: String): CompletableFuture<String> {
        val json = "{\"alias\":${jsonString(name)}, \"value\":${jsonString(value)}}"
        val request = request(URI.create(projectUrl("/gv")))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build()
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply { check(it.statusCode(), it.body()) }
    }

    fun deleteGV(name: String): CompletableFuture<String> {
        val request = request(URI.create(projectUrl("/gv/${enc(name)}"))).DELETE().build()
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply { check(it.statusCode(), it.body()) }
    }
}
