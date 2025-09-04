`default_nettype none

module tt_um_lsnn_hschweig(
    input  wire [7:0] ui_in,    // Dedicated inputs - input current
    output wire [7:0] uo_out,   // Dedicated outputs (membrane and spike)
    input  wire [7:0] uio_in,   // IOs: Input path (unused)
    output wire [7:0] uio_out,  // IOs: Output path (threshold)
    output wire [7:0] uio_oe,   // IOs: Enable path
    input  wire       ena,      // Enable (ignored)
    input  wire       clk,      // Clock
    input  wire       rst_n     // Reset (active low)
);

    // Parameters
    parameter b0j = 8'd50;         // Base threshold
    parameter adapt_jump = 8'd30;  // Adaptation jump after spike
    parameter REFRACT_TIME = 3'd3; // Refractory period cycles
    parameter TAU = 4'd8;          // Time constant (power of 2 for efficiency)
    
    // State registers
    reg [7:0] membrane;        // Membrane potential
    reg [7:0] threshold;       // Current threshold register
    reg [2:0] refract_count;   // Single refractory counter
    reg spike_occurred;        // Register to track if spike happened this cycle
    
    // Refractory state tracking
    wire in_refractory = (refract_count > 0);
    
    // Spike detection - only when not in refractory period
    wire spike = !in_refractory && (membrane >= threshold);
    
    // Leaky integration calculation
    wire [7:0] scaled_input = ui_in;
    wire [7:0] neg_membrane = (~membrane) + 1'b1;
    wire [8:0] membrane_change = scaled_input + neg_membrane;
    wire [7:0] delta_v = membrane_change[8:0] >>> $clog2(TAU);

    // Sequential logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            membrane <= 8'b0;
            threshold <= b0j;
            refract_count <= 0;
            spike_occurred <= 0;
        end else begin
            // Update spike_occurred for threshold adaptation
            spike_occurred <= spike;
            
            // Update threshold - do this first so we update right after spike
            if (spike) begin
                threshold <= threshold + adapt_jump;  // Direct threshold update on spike
            end else if (threshold > b0j) begin
                threshold <= threshold - 1;
            end
            
            // Update refractory counter
            if (spike) begin
                refract_count <= REFRACT_TIME;
            end else if (refract_count > 0) begin
                refract_count <= refract_count - 1;
            end

            // Update membrane potential
            if (spike || in_refractory) begin
                membrane <= 8'b0;
            end else begin
                membrane <= (delta_v[7] && membrane < |delta_v) ? 8'b0 :
                           (!delta_v[7] && membrane > (8'hFF - delta_v)) ? 8'hFF :
                           membrane + delta_v;
            end
        end
    end

    // Output assignments
    assign uo_out = {membrane[6:0], spike};  // Output current membrane and spike status
    assign uio_out = threshold;
    assign uio_oe = 8'hFF;

    // Handle unused inputs
    wire _unused = &{ena, uio_in};

endmodule