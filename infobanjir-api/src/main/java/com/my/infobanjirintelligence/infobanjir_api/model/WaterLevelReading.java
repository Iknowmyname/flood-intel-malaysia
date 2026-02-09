package com.my.infobanjirintelligence.infobanjir_api.model;

public record WaterLevelReading(
    String station_id,
    String station_name,
    String district,
    String state,
    String recorded_at,
    Double river_level_m,
    String source
) {}
