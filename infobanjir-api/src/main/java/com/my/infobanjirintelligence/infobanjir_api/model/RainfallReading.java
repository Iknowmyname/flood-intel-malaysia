package com.my.infobanjirintelligence.infobanjir_api.model;

public record RainfallReading(
    String station_id,
    String station_name,
    String district,
    String state,
    String recorded_at,
    Double rain_mm,
    String source
) {}
