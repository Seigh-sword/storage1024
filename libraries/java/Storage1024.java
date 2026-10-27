import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;

/** Client for the Storage1024 REST API (Java 11+). */
public class Storage1024 {
    private String apiBase = "https://storage1024.onrender.com/api";
    private String token = "";
    private String userID = "";
    private final HttpClient client = HttpClient.newHttpClient();

    public void setToken(String t) { this.token = t == null ? "" : t; }
    public void setUserID(String id) { this.userID = id == null ? "" : id; }
    public void setApiBase(String url) { this.apiBase = url.replaceAll("/+$", ""); }

    private static String enc(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }

    /** Minimal JSON string escaper: string interpolation used to break on quotes. */
    private static String jsonString(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
                    else out.append(c);
            }
        }
        return out.append('"').toString();
    }

    /** Extract the "value" field without pulling in a JSON dependency. */
    private static String extractValue(String json) {
        String marker = "\"value\"";
        int at = json.indexOf(marker);
        if (at < 0) return "";
        int colon = json.indexOf(':', at + marker.length());
        if (colon < 0) return "";
        int start = json.indexOf('"', colon + 1);
        if (start < 0) return ""; // e.g. "value": null
        StringBuilder out = new StringBuilder();
        for (int i = start + 1; i < json.length(); i++) {
            char c = json.charAt(i);
            if (c == '"') return out.toString();
            if (c == '\\' && i + 1 < json.length()) {
                char n = json.charAt(++i);
                switch (n) {
                    case 'n': out.append('\n'); break;
                    case 'r': out.append('\r'); break;
                    case 't': out.append('\t'); break;
                    default: out.append(n);
                }
            } else {
                out.append(c);
            }
        }
        return out.toString();
    }

    private static String check(int status, String body) {
        if (status < 200 || status >= 300) {
            throw new CompletionException(new IllegalStateException("Storage1024 " + status + ": " + body));
        }
        return body;
    }

    private String projectUrl(String suffix) {
        return apiBase + "/projects/" + enc(userID) + suffix;
    }

    private HttpRequest.Builder request(URI uri) {
        return HttpRequest.newBuilder(uri).header("Authorization", "Bearer " + token);
    }

    /** Returns the variable's value. */
    public CompletableFuture<String> getGV(String name) {
        HttpRequest request = request(URI.create(projectUrl("/gv/" + enc(name))))
                .GET().build();
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(res -> extractValue(check(res.statusCode(), res.body())));
    }

    public CompletableFuture<String> listGVs() {
        HttpRequest request = request(URI.create(projectUrl("/gv"))).GET().build();
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(res -> check(res.statusCode(), res.body()));
    }

    public CompletableFuture<String> addGV(String name, String value) {
        String json = "{\"alias\":" + jsonString(name) + ", \"value\":" + jsonString(value) + "}";
        HttpRequest request = request(URI.create(projectUrl("/gv")))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(res -> check(res.statusCode(), res.body()));
    }

    public CompletableFuture<String> deleteGV(String name) {
        HttpRequest request = request(URI.create(projectUrl("/gv/" + enc(name))))
                .DELETE().build();
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(res -> check(res.statusCode(), res.body()));
    }
}
