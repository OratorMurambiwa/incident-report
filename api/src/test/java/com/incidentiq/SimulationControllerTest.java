package com.incidentiq;

import com.incidentiq.dev.SimulationController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(SimulationController.class)
@ActiveProfiles("dev")
@TestPropertySource(properties = "incidentiq.simulation.enabled=true")
class SimulationControllerTest {
    @Autowired MockMvc mvc;
    @Test void explicitDevelopmentSimulationReturns500() throws Exception {
        mvc.perform(get("/api/dev/simulate/failure")).andExpect(status().isInternalServerError()).andExpect(jsonPath("$.simulated").value(true));
    }
    @Test void boundedLatencySimulationReturns200() throws Exception {
        mvc.perform(get("/api/dev/simulate/latency?delayMs=1")).andExpect(status().isOk()).andExpect(jsonPath("$.delayMs").value(1));
    }
    @Test void excessiveDelayIsRejected() throws Exception {
        mvc.perform(get("/api/dev/simulate/latency?delayMs=2001")).andExpect(status().isBadRequest());
    }
}
