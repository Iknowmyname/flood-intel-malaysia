package com.my.infobanjirintelligence.infobanjir_api.exception;

import java.time.Instant;
import java.util.NoSuchElementException;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.my.infobanjirintelligence.infobanjir_api.model.ApiError;

@RestControllerAdvice
public class GlobalErrorHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalErrorHandler.class);

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiError> handleBadRequest(IllegalArgumentException ex) {

        String requestId = UUID.randomUUID().toString();
        log.warn("Bad Request [{}]: {}", requestId, ex.getMessage());

        ApiError apiError = new ApiError(
            HttpStatus.BAD_REQUEST.name(),
            ex.getMessage(),
            Instant.now().toString(),
            requestId
        );

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(apiError); 
        

    }

    @ExceptionHandler(NoSuchElementException.class)
    public ResponseEntity<ApiError> handleNotFound(NoSuchElementException ex) {

        String requestId = UUID.randomUUID().toString();
        log.warn("Not found [{}]: {}", requestId, ex.getMessage());

        ApiError apiError = new ApiError(
            HttpStatus.NOT_FOUND.name(),
            ex.getMessage(),
            Instant.now().toString(),
            requestId
        );

        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(apiError);
    }

        @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleGenericError(Exception ex) {
        String requestId = UUID.randomUUID().toString();
        log.error("Internal Server Error [{}]: {}", requestId, ex.getMessage(), ex);

        ApiError apiError = new ApiError(
                HttpStatus.INTERNAL_SERVER_ERROR.name(),
                "An unexpected error occurred. Please try again later.",
                Instant.now().toString(),
                requestId
        );

        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(apiError);
    }
}