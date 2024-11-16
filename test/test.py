import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_lsnn(dut):
    """Test LSNN behavioral characteristics"""
    
    # Parameters
    BASE_THRESHOLD = 50
    ADAPT_JUMP = 30
    REFRACT_TIME = 3

    # Start clock
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset sequence")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    # Test neuron behavior with constant input
    test_current = 60  # Above threshold to ensure spiking
    dut.ui_in.value = test_current
    
    dut._log.info(f"\nTesting neuron behavior with input current: {test_current}")
    
    # Track state machine behavior
    spikes_seen = 0
    last_threshold = BASE_THRESHOLD
    membrane_history = []
    threshold_history = []
    spike_history = []
    refractory_count = 0
    spike_detected = False  # Flag to check threshold on next cycle
    
    # Monitor behavior for several cycles
    for cycle in range(30):
        await RisingEdge(dut.clk)
        
        # Read outputs
        uo_out_value = int(dut.uo_out.value)
        membrane = uo_out_value >> 1
        spike = uo_out_value & 0b1
        threshold = int(dut.uio_out.value)
        
        membrane_history.append(membrane)
        threshold_history.append(threshold)
        spike_history.append(spike)
        
        dut._log.info(f"\nCycle {cycle}:")
        dut._log.info(f"  Membrane: {membrane}")
        dut._log.info(f"  Threshold: {threshold}")
        dut._log.info(f"  Spike: {spike}")
        
        # Check threshold adaptation one cycle after spike
        if spike_detected:
            spike_detected = False
            assert threshold > last_threshold, "Threshold should increase after spike"
            last_threshold = threshold
        
        # Track spikes and verify threshold adaptation
        if spike:
            spikes_seen += 1
            refractory_count = REFRACT_TIME  # Start refractory period
            spike_detected = True  # Set flag to check threshold next cycle
        elif refractory_count > 0:
            refractory_count -= 1
            # During refractory period, membrane should stay low and no spikes should occur
            assert membrane < threshold, "Membrane should stay below threshold during refractory"
            assert spike == 0, "No spikes should occur during refractory period"

    # Final behavioral checks
    dut._log.info("\nBehavioral Analysis:")
    
    # Check if we saw spikes
    assert spikes_seen > 0, "Should have seen at least one spike"
    dut._log.info(f"Total spikes observed: {spikes_seen}")
    
    # Check threshold adaptation
    spike_indices = [i for i, spike in enumerate(spike_history) if spike]
    thresholds_after_spikes = [threshold_history[i+1] for i in spike_indices[:-1]]  # Get threshold from cycle after spike
    
    # Verify increasing thresholds after spikes
    for i in range(1, len(thresholds_after_spikes)):
        assert thresholds_after_spikes[i] >= thresholds_after_spikes[i-1], \
            "Subsequent spikes should have higher thresholds"
    
    dut._log.info(f"Thresholds after spikes: {thresholds_after_spikes}")
    
    # Verify refractory periods between spikes
    for i in range(len(spike_indices)-1):
        period = spike_indices[i+1] - spike_indices[i]
        assert period > REFRACT_TIME, \
            f"Period between spikes ({period}) should be greater than refractory period ({REFRACT_TIME})"
    
    dut._log.info("All behavioral checks passed!")