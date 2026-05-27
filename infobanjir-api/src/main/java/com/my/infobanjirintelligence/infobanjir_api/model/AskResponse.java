package com.my.infobanjirintelligence.infobanjir_api.model;
import com.my.infobanjirintelligence.infobanjir_api.service.AskService.Mode;

public record AskResponse (

    String answer,
    Mode mode,
    Double confidence,
    Long latencyMs,
    String requestId,
    String timestamp
) {}



