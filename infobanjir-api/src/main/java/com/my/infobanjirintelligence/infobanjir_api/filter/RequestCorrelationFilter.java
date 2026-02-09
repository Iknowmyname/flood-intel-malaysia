package com.my.infobanjirintelligence.infobanjir_api.filter;

import java.io.IOException;
import java.util.UUID;

import org.slf4j.MDC;
import org.springframework.lang.NonNull;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@Component
public class RequestCorrelationFilter extends OncePerRequestFilter{


    public static final String CORRELATION_ID_HEADER = "X-Correlation-ID";

    public static final String CORRELATION_ID_KEY = "correlationId";

    @Override
    protected void doFilterInternal(
        @NonNull HttpServletRequest request,
        @NonNull HttpServletResponse response,
        @NonNull FilterChain filterChain
    ) throws ServletException, IOException {

        String correlationId = extractOrGenerateCorrelationId(request);

        // Store correlation id in MDC so logs and downstream calls can use it.
        MDC.put(CORRELATION_ID_HEADER, correlationId);

        try {
            response.setHeader(CORRELATION_ID_HEADER, correlationId);

            filterChain.doFilter(request, response);
            
        } finally { 

            MDC.remove(CORRELATION_ID_KEY);
        }
    }

    private String extractOrGenerateCorrelationId (HttpServletRequest request) {

        String headerId = request.getHeader(CORRELATION_ID_HEADER);

        if (headerId != null && !headerId.isBlank()) {
            return headerId.trim();
        }

        return UUID.randomUUID().toString();

    }



}
