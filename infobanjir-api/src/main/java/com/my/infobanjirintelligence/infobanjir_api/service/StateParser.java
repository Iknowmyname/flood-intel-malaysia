package com.my.infobanjirintelligence.infobanjir_api.service;

import java.util.List;

public final class StateParser {

    // Lowercase variants to allow simple substring matching on user questions.
    private static final List<String> STATES = List.of(
        "johor",
        "kedah",
        "kelantan",
        "melaka",
        "negeri sembilan",
        "pahang",
        "perak",
        "perlis",
        "pulau pinang",
        "penang",
        "sabah",
        "sarawak",
        "selangor",
        "terengganu",
        "kuala lumpur",
        "labuan",
        "putrajaya"
    );

    private StateParser() {}

    public static String findState(String question) {
        if (question == null) {
            return null;
        }
        String q = question.toLowerCase();
        for (String state : STATES) {
            if (q.contains(state)) {
                if (state.equals("penang") || state.equals("pulau pinang")) {
                    return "Pulau Pinang";
                }
                if (state.equals("kuala lumpur")) {
                    return "Kuala Lumpur";
                }
                if (state.equals("negeri sembilan")) {
                    return "Negeri Sembilan";
                }
                if (state.equals("putrajaya")) {
                    return "Putrajaya";
                }
                if (state.equals("labuan")) {
                    return "Labuan";
                }
                return Character.toUpperCase(state.charAt(0)) + state.substring(1);
            }
        }
        return null;
    }
}
