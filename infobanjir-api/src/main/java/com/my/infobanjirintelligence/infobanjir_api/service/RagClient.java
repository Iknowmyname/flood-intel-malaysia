package com.my.infobanjirintelligence.infobanjir_api.service;

import java.util.Map;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.util.UriComponentsBuilder;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.my.infobanjirintelligence.infobanjir_api.model.RagAskResponse;

@Service
public class RagClient {

    private static final Logger log = LoggerFactory.getLogger(RagClient.class);

    private final HttpClient httpClient;
    private final String baseUrl;
    private final ObjectMapper objectMapper;

    public RagClient(
        ObjectMapper objectMapper,
        @Value("${services.rag.base-url}") String baseUrl
    ) {
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .version(HttpClient.Version.HTTP_1_1)
            .build();
        this.objectMapper = objectMapper;
        this.baseUrl = baseUrl;
    }

    public RagAskResponse ask(String question) {
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
            .path("/rag/ask")
            .toUriString();

        String normalizedQuestion = question == null ? "" : question.trim();
        if (normalizedQuestion.isBlank()) {
            throw new IllegalArgumentException("Question must not be blank");
        }

        String payloadJson;
        try {
            payloadJson = objectMapper.writeValueAsString(Map.of("question", normalizedQuestion));
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Failed to serialize RAG payload", ex);
        }

        try {
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json; charset=utf-8")
                .header("Accept", "application/json")
                .timeout(Duration.ofSeconds(30))
                .POST(HttpRequest.BodyPublishers.ofByteArray(payloadJson.getBytes(StandardCharsets.UTF_8)))
                .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                log.warn("RAG request failed status={} body={}", response.statusCode(), response.body());
                throw new IllegalStateException("RAG service request failed with status " + response.statusCode());
            }
            return objectMapper.readValue(response.body(), RagAskResponse.class);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("RAG service request interrupted", ex);
        } catch (Exception ex) {
            throw new IllegalStateException("RAG service request failed", ex);
        }
    }
}
