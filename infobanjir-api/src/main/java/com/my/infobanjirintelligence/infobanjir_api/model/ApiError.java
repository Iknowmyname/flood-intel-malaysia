package com.my.infobanjirintelligence.infobanjir_api.model;


public record ApiError (String status, String message, String timestamp, String requestId) {}