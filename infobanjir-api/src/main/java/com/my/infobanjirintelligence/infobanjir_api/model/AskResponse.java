package com.my.infobanjirintelligence.infobanjir_api.model;

public record AskResponse (

    String answer,
    String mode,
    Double confidence,
    Long latencyMs,
    String requestId,
    String timestamp
) {}



