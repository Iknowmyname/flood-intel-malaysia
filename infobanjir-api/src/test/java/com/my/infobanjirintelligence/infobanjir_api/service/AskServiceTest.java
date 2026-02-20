package com.my.infobanjirintelligence.infobanjir_api.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.my.infobanjirintelligence.infobanjir_api.model.AskResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.RagAskResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.RagCitation;
import com.my.infobanjirintelligence.infobanjir_api.model.RainfallReading;
import com.my.infobanjirintelligence.infobanjir_api.model.RainfallResponse;
import com.my.infobanjirintelligence.infobanjir_api.model.WaterLevelReading;
import com.my.infobanjirintelligence.infobanjir_api.model.WaterLevelResponse;

@ExtendWith(MockitoExtension.class)
class AskServiceTest {

    @Mock
    private ExpressApiClient expressApiClient;

    @Mock
    private RagClient ragClient;

    private AskService askService;

    @BeforeEach
    void setUp() {
        askService = new AskService(expressApiClient, ragClient);
        ReflectionTestUtils.setField(askService, "mode", "sql");
    }

    @Test
    void handleQuestion_rain_usesExpressRainfall() {
        var reading = new RainfallReading(
            "STN123",
            "Station Alpha",
            "Kota",
            "Selangor",
            "2026-02-05T10:30:00.000Z",
            12.4,
            "DID"
        );
        when(expressApiClient.getLatestRainfall("SEL", 50))
            .thenReturn(new RainfallResponse(List.of(reading)));

        AskResponse response = askService.handleQuestion("rain in selangor");

        assertThat(response.answer()).contains("highest rainfall readings");
        assertThat(response.answer()).contains("Station Alpha");
        assertThat(response.mode()).isEqualTo("sql");
    }

    @Test
    void handleQuestion_rain_withState_filtersByState() {
        var reading = new RainfallReading(
            "STN123",
            "Station Alpha",
            "Kota",
            "Selangor",
            "2026-02-05T10:30:00.000Z",
            12.4,
            "DID"
        );
        when(expressApiClient.getLatestRainfall("SEL", 50))
            .thenReturn(new RainfallResponse(List.of(reading)));

        AskResponse response = askService.handleQuestion("rain in Selangor");

        assertThat(response.answer()).contains("Selangor");
    }

    @Test
    void handleQuestion_waterLevel_usesExpressWaterLevel() {
        var reading = new WaterLevelReading(
            "STN456",
            "Station Beta",
            "Kuala",
            "Johor",
            "2026-02-05T10:30:00.000Z",
            3.27,
            "DID"
        );
        when(expressApiClient.getLatestWaterLevel("JHR", 50))
            .thenReturn(new WaterLevelResponse(List.of(reading)));

        AskResponse response = askService.handleQuestion("water level johor");

        assertThat(response.answer()).contains("highest river levels");
        assertThat(response.answer()).contains("Station Beta");
        assertThat(response.mode()).isEqualTo("sql");
    }

    @Test
    void handleQuestion_unknown_returnsGuidance() {
        AskResponse response = askService.handleQuestion("hello");

        assertThat(response.answer()).contains("rainfall or water level");
        assertThat(response.mode()).isEqualTo("sql");
    }

    @Test
    void handleQuestion_rain_emptyList_returnsNoData() {
        when(expressApiClient.getLatestRainfall(null, 50))
            .thenReturn(new RainfallResponse(List.of()));

        AskResponse response = askService.handleQuestion("rain");

        assertThat(response.answer()).contains("No recent rainfall readings");
        assertThat(response.mode()).isEqualTo("sql");
    }

    @Test
    void handleQuestion_rag_usesRagClient() {
        var ragResponse = new RagAskResponse(
            "RAG answer",
            List.of(new RagCitation("local", "snippet")),
            0.5,
            "req-1",
            "2026-02-05T10:30:00.000Z"
        );
        when(ragClient.ask("what is rain")).thenReturn(ragResponse);
        ReflectionTestUtils.setField(askService, "mode", "rag");

        AskResponse response = askService.handleQuestion("what is rain");

        assertThat(response.answer()).contains("RAG answer");
        assertThat(response.mode()).isEqualTo("rag");
    }

    @Test
    void handleQuestion_rag_failure_fallsBackToSql() {
        when(ragClient.ask("rain")).thenThrow(new RuntimeException("RAG down"));
        when(expressApiClient.getLatestRainfall(null, 50))
            .thenReturn(new RainfallResponse(List.of()));
        ReflectionTestUtils.setField(askService, "mode", "rag");

        AskResponse response = askService.handleQuestion("rain");

        assertThat(response.answer()).contains("No recent rainfall readings");
        assertThat(response.mode()).isEqualTo("rag");
    }

    @Test
    void handleQuestion_auto_prefersSqlForNumericQueries() {
        when(expressApiClient.getLatestWaterLevel("SEL", 50))
            .thenReturn(new WaterLevelResponse(List.of()));
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("average water level in Selangor");

        assertThat(response.answer()).contains("No recent water level readings");
        assertThat(response.mode()).isEqualTo("auto");
    }

    @Test
    void handleQuestion_auto_usesRagForGeneralQuestions() {
        var ragResponse = new RagAskResponse(
            "RAG general answer",
            List.of(new RagCitation("local", "snippet")),
            0.6,
            "req-2",
            "2026-02-05T10:30:00.000Z"
        );
        when(ragClient.ask("what is hydrology")).thenReturn(ragResponse);
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("what is hydrology");

        assertThat(response.answer()).contains("RAG general answer");
        assertThat(response.mode()).isEqualTo("auto");
    }

    @Test
    void handleQuestion_auto_floodRisk_usesDeterministicEstimator() {
        var rain = new RainfallReading(
            "STN123",
            "Station Alpha",
            "Kota",
            "SEL",
            "2026-02-05T10:30:00.000Z",
            12.4,
            "DID"
        );
        var water = new WaterLevelReading(
            "STN456",
            "Station Beta",
            "Kuala",
            "SEL",
            "2026-02-05T10:30:00.000Z",
            15.0,
            "DID"
        );
        when(expressApiClient.getLatestRainfall("SEL", 50))
            .thenReturn(new RainfallResponse(List.of(rain)));
        when(expressApiClient.getLatestWaterLevel("SEL", 50))
            .thenReturn(new WaterLevelResponse(List.of(water)));
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("What is the flood risk in Selangor today?");

        assertThat(response.answer()).contains("Estimated flood risk in SEL");
        assertThat(response.answer()).contains("heuristic estimate");
        assertThat(response.mode()).isEqualTo("auto");
    }

    @Test
    void handleQuestion_auto_explanationQuestion_returnsMethodExplanation() {
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("How does this assistant estimate flood risk?");

        assertThat(response.answer()).contains("how this assistant estimates flood risk");
        assertThat(response.confidence()).isLessThan(1.0);
        assertThat(response.mode()).isEqualTo("auto");
    }

    @Test
    void handleQuestion_auto_unknownState_returnsValidationMessage() {
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("What is the flood risk in Atlantis today?");

        assertThat(response.answer()).contains("couldn't recognize");
        assertThat(response.mode()).isEqualTo("auto");
    }

    @Test
    void handleQuestion_auto_historicalRange_returnsScopeWarning() {
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("What changed in flood risk for Selangor between 2026-02-19 and 2026-02-20?");

        assertThat(response.answer()).contains("Historical or date-range queries are not supported");
        assertThat(response.mode()).isEqualTo("auto");
    }

    @Test
    void handleQuestion_auto_offTopic_returnsCapabilityGuidance() {
        ReflectionTestUtils.setField(askService, "mode", "auto");

        AskResponse response = askService.handleQuestion("Tell me a joke about floods");

        assertThat(response.answer()).contains("I can help with Malaysian flood");
        assertThat(response.mode()).isEqualTo("auto");
    }
}
