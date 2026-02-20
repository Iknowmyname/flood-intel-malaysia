package com.my.infobanjirintelligence.infobanjir_api.service;

import static org.springframework.http.HttpMethod.GET;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.databind.ObjectMapper;

class ExpressApiClientTest {

    private ExpressApiClient expressApiClient;
    private MockRestServiceServer mockServer;

    @BeforeEach
    void setUp() {
        RestTemplate restTemplate = new RestTemplate();
        mockServer = MockRestServiceServer.createServer(restTemplate);
        expressApiClient = new ExpressApiClient(restTemplate, new ObjectMapper(), "http://express.test");
    }

    @Test
    void getLatestRainfall_mapsKedahToUpstreamCode() {
        mockServer.expect(requestTo("http://express.test/api/readings/latest/rain?state=KDH&limit=50"))
            .andExpect(method(GET))
            .andRespond(withSuccess("{\"items\":[]}", MediaType.APPLICATION_JSON));

        expressApiClient.getLatestRainfall("KED", 50);

        mockServer.verify();
    }

    @Test
    void getLatestWaterLevel_mapsKelantanToUpstreamCode() {
        mockServer.expect(requestTo("http://express.test/api/readings/latest/water_level?state=KEL&limit=50"))
            .andExpect(method(GET))
            .andRespond(withSuccess("{\"items\":[]}", MediaType.APPLICATION_JSON));

        expressApiClient.getLatestWaterLevel("KTN", 50);

        mockServer.verify();
    }
}

