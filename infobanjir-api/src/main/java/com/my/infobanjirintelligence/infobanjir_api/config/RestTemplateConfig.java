package com.my.infobanjirintelligence.infobanjir_api.config;

import java.util.List;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class RestTemplateConfig {

    private final CorrelationIdInterceptor correlationIdInterceptor;

    public RestTemplateConfig(CorrelationIdInterceptor interceptor) {

        this.correlationIdInterceptor = interceptor;
    }

    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder.additionalInterceptors(List.of(correlationIdInterceptor)).build();
    }

}