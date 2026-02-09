package com.my.infobanjirintelligence.infobanjir_api.controller;

import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.my.infobanjirintelligence.infobanjir_api.model.ApiResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.AskResponse;
import com.my.infobanjirintelligence.infobanjir_api.service.AskService;

import lombok.RequiredArgsConstructor;

@RequestMapping("/api")
@RestController
@RequiredArgsConstructor

public class AskController {

    private final AskService askService;

    @PostMapping("/ask")
    public ResponseEntity<ApiResponse <AskResponse>> askQuestion(@RequestBody Map<String, String> payload) {

        String question = payload.getOrDefault("question", "");
        AskResponse response = askService.handleQuestion(question);

        ApiResponse<AskResponse> apiResponse = ApiResponse.of(response, response.requestId());

        return ResponseEntity.ok(apiResponse);

    }

    
}

