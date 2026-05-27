package com.my.infobanjirintelligence.infobanjir_api.service;

import java.util.Collections;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.Assert;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import com.my.infobanjirintelligence.infobanjir_api.model.RagAskResponse;

@Service
public class RagClient {

    private static final Logger log = LoggerFactory.getLogger(RagClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;
    

    public RagClient(RestTemplate restTemplate,  @Value("${services.rag.base-url}") String baseUrl) {
        this.restTemplate = restTemplate;
        Assert.hasText(baseUrl, "base-url must be configured in application properties!");
        this.baseUrl = baseUrl;
    }

    public RagAskResponse ask(String question) {

    
        String url = UriComponentsBuilder.fromUriString(baseUrl)
            .path("/rag/ask")
            .toUriString();

        String normalizedQuestion = question == null ? "" : question.trim();
        if (normalizedQuestion.isBlank()) {
            throw new IllegalArgumentException("Question must not be blank");
        }


        try {
           
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setAccept(Collections.singletonList(MediaType.APPLICATION_JSON));
            

            Map<String, String> body = Map.of("question", normalizedQuestion);

            HttpEntity<Map<String,String>> request = new HttpEntity<>(body, headers);
            log.info("Correlation id at RagClient :" + MDC.get("correlationId"));

            ResponseEntity<RagAskResponse> response = restTemplate.exchange(url,HttpMethod.POST, request, RagAskResponse.class);
            
            if (response.getBody() == null) {
                throw new IllegalStateException("RAG service returned an empty response!");
            }
            return response.getBody();
        } catch (HttpStatusCodeException ex) {
            throw new IllegalStateException("RAG service bad status code", ex);
        } catch (ResourceAccessException ex) {
            throw new IllegalStateException("RAG service request failed", ex);
        }
    }
}
