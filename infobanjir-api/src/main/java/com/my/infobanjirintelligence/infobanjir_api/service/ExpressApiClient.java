package com.my.infobanjirintelligence.infobanjir_api.service;

import java.util.Collections;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.my.infobanjirintelligence.infobanjir_api.model.RainfallResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.WaterLevelResponse;

@Service
public class ExpressApiClient {

    private static final Logger log = LoggerFactory.getLogger(ExpressApiClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final ObjectMapper objectMapper;

    public ExpressApiClient(
        RestTemplate restTemplate,
        ObjectMapper objectMapper,
        @Value("${services.express.base-url}") String baseUrl
    ) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
        this.baseUrl = baseUrl;
    }

    public RainfallResponse getLatestRainfall(String state, Integer limit) {
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
            .path("/api/readings/latest/rain")
            .queryParamIfPresent("state", Optional.ofNullable(state))
            .queryParamIfPresent("limit", Optional.ofNullable(limit))
            .toUriString();

        return fetch(url, RainfallResponse.class, "rainfall", state);
    }

    public WaterLevelResponse getLatestWaterLevel(String state, Integer limit) {
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
            .path("/api/readings/latest/water_level")
            .queryParamIfPresent("state", Optional.ofNullable(state))
            .queryParamIfPresent("limit", Optional.ofNullable(limit))
            .toUriString();

        return fetch(url, WaterLevelResponse.class, "water level", state);
    }

    private <T> T fetch(String url, Class<T> type, String label, String state) {
        
        System.out.println("Express GET " + url);
        ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
        String body = response.getBody();
        if (body == null || body.isBlank()) {
            log.warn("Express {} response body empty for state={}", label, state);
            System.out.println("Express " + label + " response body empty for state=" + state);
            return emptyResponse(type);
        }
        try {
            return objectMapper.readValue(body, type);
        } catch (Exception ex) {
            log.warn("Express {} response parse failed for state={} len={}", label, state, body.length());
            System.out.println("Express " + label + " response parse failed for state=" + state + " len=" + body.length());
            return emptyResponse(type);
        }
    }

    private <T> T emptyResponse(Class<T> type) {
        if (type.equals(RainfallResponse.class)) {
            return type.cast(new RainfallResponse(Collections.emptyList()));
        }
        if (type.equals(WaterLevelResponse.class)) {
            return type.cast(new WaterLevelResponse(Collections.emptyList()));
        }
        return null;
    }
}
