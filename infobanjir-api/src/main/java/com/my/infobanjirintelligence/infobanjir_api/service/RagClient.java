package com.my.infobanjirintelligence.infobanjir_api.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import com.my.infobanjirintelligence.infobanjir_api.model.RagAskRequest;
import com.my.infobanjirintelligence.infobanjir_api.model.RagAskResponse;

@Service
public class RagClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public RagClient(RestTemplate restTemplate, @Value("${services.rag.base-url}") String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    public RagAskResponse ask(String question) {
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
            .path("/rag/ask")
            .toUriString();

        // Simple synchronous call; caller handles fallback on errors/timeouts.
        return restTemplate.postForObject(url, new RagAskRequest(question), RagAskResponse.class);
    }
}
