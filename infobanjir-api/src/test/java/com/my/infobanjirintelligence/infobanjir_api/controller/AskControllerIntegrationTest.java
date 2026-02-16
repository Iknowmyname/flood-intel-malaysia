package com.my.infobanjirintelligence.infobanjir_api.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.http.HttpMethod.GET;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

@SpringBootTest(
    webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
    properties = {
        "app.mode=sql",
        "services.express.base-url=http://express.test"
    }
)
class AskControllerIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private RestTemplate appRestTemplate;

    private MockRestServiceServer mockServer;

    @Test
    void ask_returnsDeterministicSqlAnswer() {
        mockServer = MockRestServiceServer.createServer(appRestTemplate);
        String expressBody = """
            {
              "items": [
                {
                  "station_id": "STN123",
                  "station_name": "Station Alpha",
                  "district": "Kota",
                  "state": "Selangor",
                  "recorded_at": "2026-02-05T10:30:00.000Z",
                  "rain_mm": 12.4,
                  "source": "DID"
                }
              ]
            }
            """;

        mockServer.expect(requestTo("http://express.test/api/readings/latest/rain?limit=50"))
            .andExpect(method(GET))
            .andRespond(withSuccess(expressBody, MediaType.APPLICATION_JSON));

        ResponseEntity<String> response = restTemplate.postForEntity(
            "/api/ask",
            Map.of("question", "rain"),
            String.class
        );

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).contains("\"status\":\"SUCCESS\"");
        assertThat(response.getBody()).contains("highest rainfall readings");
    }
}
