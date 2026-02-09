package com.my.infobanjirintelligence.infobanjir_api.model;

import java.time.Instant;

public record ApiResponse <T>(
    String status,
    T data,
    String timeStamp,
    String requestId

) {

    public static <T> ApiResponse<T> of(T data, String reqeustId) {
        return new ApiResponse<>(
            "SUCCESS",
            data,
            Instant.now().toString(),
            reqeustId
        );
    }


}


