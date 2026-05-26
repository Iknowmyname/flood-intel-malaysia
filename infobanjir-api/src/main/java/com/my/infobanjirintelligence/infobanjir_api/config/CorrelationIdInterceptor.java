package com.my.infobanjirintelligence.infobanjir_api.config;


import java.io.IOException;

import org.slf4j.MDC;
import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpRequestExecution;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.stereotype.Component;

@Component
public class CorrelationIdInterceptor implements ClientHttpRequestInterceptor {

    private static final String CORRELATION_HEADER = "X-Correlation-ID";

    @Override 
    public ClientHttpResponse intercept (HttpRequest request, byte [] body, ClientHttpRequestExecution execution) throws IOException {

        String correlationId = MDC.get("correlationId");
        // Propagate correlation id to downstream services for traceability.
        if (correlationId != null) {
            request.getHeaders().add(CORRELATION_HEADER, correlationId);
        }

        return execution.execute(request, body);
    }
}
