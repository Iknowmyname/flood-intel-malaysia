package com.my.infobanjirintelligence.infobanjir_api.service;

import java.util.Collections;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import com.my.infobanjirintelligence.infobanjir_api.model.RainfallResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.WaterLevelResponse;

@Service
public class ExpressApiClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public ExpressApiClient(RestTemplate restTemplate, @Value("${services.express.base-url}") String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    public RainfallResponse getLatestRainfall(String state, Integer limit) {
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
            .path("/api/readings/latest/rain")
            .queryParamIfPresent("state", Optional.ofNullable(state))
            .queryParamIfPresent("limit", Optional.ofNullable(limit))
            .toUriString();

        RainfallResponse response = restTemplate.getForObject(url, RainfallResponse.class);
     
        return response != null ? response : new RainfallResponse(Collections.emptyList());
    }

    public WaterLevelResponse getLatestWaterLevel(String state, Integer limit) {
        String url = UriComponentsBuilder.fromHttpUrl(baseUrl)
            .path("/api/readings/latest/water_level")
            .queryParamIfPresent("state", Optional.ofNullable(state))
            .queryParamIfPresent("limit", Optional.ofNullable(limit))
            .toUriString();

        WaterLevelResponse response = restTemplate.getForObject(url, WaterLevelResponse.class);
   
        return response != null ? response : new WaterLevelResponse(Collections.emptyList());
    }
}
