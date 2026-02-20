package com.my.infobanjirintelligence.infobanjir_api.service;

import java.time.Duration;
import java.time.Instant;
import java.util.Locale;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.my.infobanjirintelligence.infobanjir_api.model.AskResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.RagAskResponse;

@Service
public class AskService {

    private static final Logger log = LoggerFactory.getLogger(AskService.class);
    private static final Pattern ISO_DATE_PATTERN = Pattern.compile("\\b\\d{4}-\\d{2}-\\d{2}\\b");
    private static final Pattern LOCATION_PATTERN = Pattern.compile("\\b(?:in|for|at)\\s+([a-z][a-z\\s]{2,30})\\b");

    private final ExpressApiClient expressApiClient;
    private final RagClient ragClient;

    @Value("${app.mode:auto}")
    private String mode;

    public AskService(ExpressApiClient expressApiClient, RagClient ragClient) {
        this.expressApiClient = expressApiClient;
        this.ragClient = ragClient;
    }

    public AskResponse handleQuestion(String question) {
        log.warn("AskService loaded from: {}", AskService.class.getProtectionDomain().getCodeSource().getLocation());

        if (question == null) {
            throw new IllegalArgumentException("Question is not valid !");
        }

        String requestId = MDC.get("correlationId");

        if (requestId == null) {
            requestId = UUID.randomUUID().toString();
        }

        Instant start = Instant.now();
        String answer;
        double confidence;

        try {
            switch (mode.toLowerCase()) {
                case "rag" -> {
                    try {
                        answer = callRagService(question);
                    } catch (Exception e) {
                        answer = callSqlOnly(question);
                    }
                }
                case "sql" -> answer = callSqlOnly(question);
                default -> answer = callAuto(question);
            }
            confidence = inferConfidence(answer);
        } catch (Exception e) {
            answer = "Service is temporarily unavailable";
            confidence = 0.0;
        }

        long latencyMs = Duration.between(start, Instant.now()).toMillis();

        return new AskResponse(
            answer,
            mode,
            confidence,
            latencyMs,
            requestId,
            Instant.now().toString()
        );
    }

    private String callRagService(String question) {
        RagAskResponse response = ragClient.ask(question);
        if (response == null || response.answer() == null || response.answer().isBlank()) {
            throw new IllegalStateException("RAG service returned empty answer");
        }
        return response.answer();
    }

    private String callSqlOnly(String question) {

        String q = normalize(question);
        String state = StateParser.findState(question);
        boolean wantsFloodRisk = isFloodRiskQuestion(q);
        boolean wantsRain = q.contains("rain");
        boolean wantsWaterLevel = q.contains("water level") || q.contains("river level");

        String unknownLocation = findUnknownLocation(question);
        if (unknownLocation != null && (wantsFloodRisk || wantsRain || wantsWaterLevel)) {
            return "I couldn't recognize \"" + unknownLocation
                + "\" as a Malaysian state. Please ask using a Malaysian state name.";
        }

        if (hasHistoricalTimeIntent(q) && (wantsFloodRisk || wantsRain || wantsWaterLevel)) {
            String scope = state == null ? "for Malaysia" : "for " + state;
            return "Historical or date-range queries are not supported in live SQL mode yet. "
                + "Please ask for current/latest readings " + scope + ".";
        }

        if (wantsFloodRisk) {
            return estimateFloodRisk(state);
        }

        if (wantsRain) {
            var rainfall = expressApiClient.getLatestRainfall(state, 50).items();
            log.warn("SQL_ONLY rainfall: state={} items={}", state, rainfall.size());
            if (rainfall.isEmpty()) {
                return state == null
                    ? "No recent rainfall readings are available."
                    : "No recent rainfall readings are available for " + state + ".";
            }
            var top = rainfall.stream()
                .filter(r -> r.rain_mm() != null)
                .sorted((a, b) -> Double.compare(b.rain_mm(), a.rain_mm()))
                .limit(3)
                .toList();
            String scope = state == null ? "Malaysia" : state;
            String summary = top.stream()
                .map(r -> r.station_name() + " (" + r.state() + ") at " + formatDecimal(r.rain_mm()) + " mm")
                .collect(Collectors.joining(", "));
            return "In " + scope + ", based on " + rainfall.size() + " recent stations, "
                + "the highest rainfall readings are " + summary + ".";
        }

        if (wantsWaterLevel) {
            var water = expressApiClient.getLatestWaterLevel(state, 50).items();
            log.warn("SQL_ONLY water level: state={} items={}", state, water.size());
            if (water.isEmpty()) {
                return state == null
                    ? "No recent water level readings are available."
                    : "No recent water level readings are available for " + state + ".";
            }
            var top = water.stream()
                .filter(w -> w.river_level_m() != null)
                .sorted((a, b) -> Double.compare(b.river_level_m(), a.river_level_m()))
                .limit(3)
                .toList();
            String scope = state == null ? "Malaysia" : state;
            String summary = top.stream()
                .map(w -> w.station_name() + " (" + w.state() + ") at " + formatDecimal(w.river_level_m()) + " m")
                .collect(Collectors.joining(", "));
            return "In " + scope + ", based on " + water.size() + " recent stations, "
                + "the highest river levels are " + summary + ".";
        }

        return "I can answer about rainfall or water level readings. Please ask about those.";
    }

    private String callAuto(String question) {
        String q = normalize(question);
        boolean asksFloodRisk = isFloodRiskQuestion(q);
        boolean asksForNumbers = q.contains("average") || q.contains("latest") || q.contains("current")
            || q.contains("top") || q.contains("highest") || q.contains("summary");
        boolean asksForRain = q.contains("rain");
        boolean asksForWater = q.contains("water level") || q.contains("river level");
        boolean asksHydroMetrics = asksFloodRisk || asksForNumbers || asksForRain || asksForWater;

        if (isOffTopic(q)) {
            return "I can help with Malaysian flood, rainfall, and river-level questions. "
                + "Please ask one of those.";
        }

        if (asksForExplanation(q)) {
            return explainMethodology();
        }

        if (asksHydroMetrics) {
            return callSqlOnly(question);
        }

        try {
            return callRagService(question);
        } catch (Exception e) {
            return callSqlOnly(question);
        }
    }

    private String formatDecimal(Double value) {
        if (value == null) {
            return "n/a";
        }
        return String.format(Locale.US, "%.2f", value);
    }

    private String normalize(String question) {
        return question == null ? "" : question.trim().toLowerCase(Locale.ROOT);
    }

    private boolean isFloodRiskQuestion(String q) {
        return q.contains("flood")
            || q.contains("risk")
            || q.contains("danger")
            || q.contains("warning")
            || q.contains("alert");
    }

    private boolean hasHistoricalTimeIntent(String q) {
        return q.contains("yesterday")
            || q.contains("last 24 hours")
            || q.contains("between")
            || q.contains("from ")
            || q.contains(" on ")
            || ISO_DATE_PATTERN.matcher(q).find();
    }

    private boolean asksForExplanation(String q) {
        return q.contains("how")
            || q.contains("why")
            || q.contains("explain")
            || q.contains("method")
            || q.contains("methodology")
            || q.contains("limitation")
            || q.contains("data source")
            || q.contains("source");
    }

    private boolean isOffTopic(String q) {
        return q.contains("joke")
            || q.contains("poem")
            || q.contains("song")
            || q.contains("story");
    }

    private String findUnknownLocation(String question) {
        if (question == null) {
            return null;
        }
        if (StateParser.findState(question) != null) {
            return null;
        }
        String q = normalize(question);
        Matcher matcher = LOCATION_PATTERN.matcher(q);
        if (!matcher.find()) {
            return null;
        }
        String candidate = matcher.group(1)
            .replaceAll("\\b(today|yesterday|tomorrow|latest|current|now)\\b", "")
            .trim();
        if (candidate.isBlank()) {
            return null;
        }
        if (candidate.contains("malaysia")) {
            return null;
        }
        if (StateParser.findState(candidate) != null) {
            return null;
        }
        return candidate;
    }

    private String explainMethodology() {
        return "Here is how this assistant estimates flood risk: "
            + "it uses the latest rainfall and river-level station readings from the upstream data service, "
            + "picks the strongest recent rainfall and river-level drivers, normalizes those signals, and combines "
            + "them into a heuristic risk score (Low/Moderate/High). "
            + "This is a guidance estimate from recent observations, not an official warning.";
    }

    private double inferConfidence(String answer) {
        if (answer == null || answer.isBlank()) {
            return 0.0;
        }
        String text = answer.toLowerCase(Locale.ROOT);
        if (text.contains("service is temporarily unavailable")) {
            return 0.0;
        }
        if (text.startsWith("estimated flood risk in ")
            || text.startsWith("in ")
            || text.startsWith("top relevant readings:")) {
            return 0.85;
        }
        if (text.startsWith("estimated flood risk summary")) {
            return 0.7;
        }
        if (text.startsWith("here is how this assistant estimates flood risk")) {
            return 0.75;
        }
        if (text.startsWith("historical or date-range queries are not supported")) {
            return 0.45;
        }
        if (text.startsWith("i couldn't recognize")) {
            return 0.35;
        }
        if (text.startsWith("i can help with malaysian flood")) {
            return 0.35;
        }
        if (text.startsWith("no recent") || text.startsWith("no matching")) {
            return 0.4;
        }
        return 0.6;
    }

    private String estimateFloodRisk(String state) {
        var rainfall = expressApiClient.getLatestRainfall(state, 50).items();
        var water = expressApiClient.getLatestWaterLevel(state, 50).items();

        var topRain = rainfall.stream()
            .filter(r -> r.rain_mm() != null)
            .sorted((a, b) -> Double.compare(b.rain_mm(), a.rain_mm()))
            .findFirst();
        var topWater = water.stream()
            .filter(w -> w.river_level_m() != null)
            .sorted((a, b) -> Double.compare(b.river_level_m(), a.river_level_m()))
            .findFirst();

        if (topRain.isEmpty() && topWater.isEmpty()) {
            return state == null
                ? "No recent rainfall or water level readings are available to estimate flood risk."
                : "No recent rainfall or water level readings are available for " + state + " to estimate flood risk.";
        }

        double rainMax = topRain.map(r -> r.rain_mm()).orElse(0.0);
        double waterMax = topWater.map(w -> w.river_level_m()).orElse(0.0);
        double rainScore = clampPercent((rainMax / 60.0) * 100.0);
        double waterScore = clampPercent((waterMax / 120.0) * 100.0);
        double riskScore = Math.round(((rainScore + waterScore) / 2.0) * 10.0) / 10.0;
        String riskLevel = riskScore >= 65.0 ? "High" : riskScore >= 35.0 ? "Moderate" : "Low";

        String scope = state == null ? "Malaysia" : state;
        String rainDriver = topRain
            .map(r -> r.station_name() + " (" + r.state() + ") at " + formatDecimal(r.rain_mm()) + " mm")
            .orElse("no recent rainfall station data");
        String waterDriver = topWater
            .map(w -> w.station_name() + " (" + w.state() + ") at " + formatDecimal(w.river_level_m()) + " m")
            .orElse("no recent river station data");

        return "Estimated flood risk in " + scope + " is " + riskLevel
            + " (score " + formatDecimal(riskScore) + "/100). "
            + "Rainfall driver: " + rainDriver + ". "
            + "River-level driver: " + waterDriver + ". "
            + "This is a heuristic estimate based on recent readings, not an official warning.";
    }

    private double clampPercent(double value) {
        if (value < 0.0) {
            return 0.0;
        }
        if (value > 100.0) {
            return 100.0;
        }
        return value;
    }
}
