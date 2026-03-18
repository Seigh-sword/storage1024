import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.concurrent.CompletableFuture;

public class Storage1024 {
    private String apiBase = "https://storage1024.onrender.com/api";
    private String token;
    private String userID;
    private final HttpClient client = HttpClient.newHttpClient();

    public void setToken(String t) { this.token = t; }
    public void setUserID(String id) { this.userID = id; }

    public CompletableFuture<String> getGV(String name) {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(apiBase + "/projects/" + userID + "/gv/" + name))
                .header("Authorization", "Bearer " + token)
                .GET()
                .build();

        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(HttpResponse::body);
    }

    public CompletableFuture<String> addGV(String name, String value) {
        String json = String.format("{\"alias\":\"%s\", \"value\":\"%s\"}", name, value);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(apiBase + "/projects/" + userID + "/gv"))
                .header("Authorization", "Bearer " + token)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();

        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(HttpResponse::body);
    }
}
