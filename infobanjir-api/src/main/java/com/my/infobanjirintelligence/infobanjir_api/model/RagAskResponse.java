package com.my.infobanjirintelligence.infobanjir_api.model;

import java.util.List;

public record RagAskResponse(
    String answer,
    List<RagCitation> citations,
    Double confidence,
    String request_id,
    String timestamp
) {}
