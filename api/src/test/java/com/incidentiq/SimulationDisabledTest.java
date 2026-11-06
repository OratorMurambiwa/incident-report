package com.incidentiq;

import com.incidentiq.dev.SimulationController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(SimulationController.class)
@TestPropertySource(properties = "incidentiq.simulation.enabled=true")
class SimulationDisabledTest {
    @Autowired MockMvc mvc;
    @Test void flagAloneDoesNotEnableSimulationWithoutDevProfile() throws Exception {
        mvc.perform(get("/api/dev/simulate/failure")).andExpect(status().isNotFound());
        mvc.perform(get("/api/dev/simulate/latency")).andExpect(status().isNotFound());
    }
}
