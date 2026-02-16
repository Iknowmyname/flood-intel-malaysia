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
                return switch (state) {
                    case "johor" -> "JHR";
                    case "kedah" -> "KED";
                    case "kelantan" -> "KTN";
                    case "melaka" -> "MLK";
                    case "negeri sembilan" -> "NSN";
                    case "pahang" -> "PHG";
                    case "perak" -> "PRK";
                    case "perlis" -> "PLS";
                    case "pulau pinang", "penang" -> "PNG";
                    case "sabah" -> "SAB";
                    case "sarawak" -> "SWK";
                    case "selangor" -> "SEL";
                    case "terengganu" -> "TRG";
                    case "kuala lumpur" -> "KUL";
                    case "labuan" -> "LBN";
                    case "putrajaya" -> "PTJ";
                    default -> null;
                };
            }
        }
        return null;
    }
}
