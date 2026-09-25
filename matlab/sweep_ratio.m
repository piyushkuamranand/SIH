% NETRA-DR — TASK-021: Simulink Ratio Sweep Script
% matlab/sweep_ratio.m
%
% Programmatically sweeps the technician-to-ophthalmologist ratio
% across N_oph = [1, 2, 3, 5, 10] and records queue wait time + utilisation.
%
% Prerequisites:
%   - MATLAB R2022b+ with Simulink + SimEvents toolboxes
%   - workflow_simulation.slx open or on MATLAB path
%
% Usage:
%   cd matlab/
%   sweep_ratio
%
% Outputs:
%   matlab/sweep_results.csv  — tabular results
%   matlab/sweep_chart.png    — wait time vs ratio chart

% ── PLACEHOLDER PARAMETERS — replace with measured values once available ──
N_PATIENTS_PER_DAY   = 120;   % placeholder: district daily volume
RECAPTURE_RATE       = 0.15;  % placeholder: ungradable fraction
REFERRAL_RATE        = 0.30;  % placeholder: AI referral fraction
AI_INFERENCE_SEC     = 10;    % placeholder: ONNX CPU inference time
OPH_REVIEW_MIN       = 5;     % placeholder: mean ophthalmologist review time
TECHNICIAN_COUNT     = 3;     % fixed for the sweep
SIM_DURATION_MIN     = 480;   % 1 working day

% ── Sweep values ───────────────────────────────────────────────────────────
N_oph_values = [1, 2, 3, 5, 10];

results = zeros(length(N_oph_values), 3);  % [N_oph, mean_wait_min, oph_utilisation]

for idx = 1:length(N_oph_values)
    N_oph = N_oph_values(idx);
    fprintf('Running simulation: N_oph=%d (ratio %d:%d)...\n', ...
            N_oph, TECHNICIAN_COUNT, N_oph);

    % Set model workspace parameters before simulation
    % (These parameter names must match the variable names in workflow_simulation.slx)
    simIn = Simulink.SimulationInput('workflow_simulation');
    simIn = setVariable(simIn, 'N_patients_per_day',  N_PATIENTS_PER_DAY);
    simIn = setVariable(simIn, 'recapture_rate',       RECAPTURE_RATE);
    simIn = setVariable(simIn, 'referral_rate',        REFERRAL_RATE);
    simIn = setVariable(simIn, 'ai_inference_sec',     AI_INFERENCE_SEC);
    simIn = setVariable(simIn, 'oph_review_min',       OPH_REVIEW_MIN);
    simIn = setVariable(simIn, 'N_ophthalmologists',   N_oph);
    simIn = setVariable(simIn, 'StopTime',             SIM_DURATION_MIN * 60);  % in seconds

    try
        simOut = sim(simIn);
        % Extract logged statistics (SimEvents logs queue wait time and utilisation)
        % Adjust signal names to match the actual Simulink block output signal names
        mean_wait     = mean(simOut.logsout{'ophQueueWaitTime'}.Values.Data);  % seconds
        utilisation   = mean(simOut.logsout{'ophUtilisation'}.Values.Data);    % fraction
        mean_wait_min = mean_wait / 60;

        results(idx, :) = [N_oph, mean_wait_min, utilisation];
        fprintf('  --> Wait: %.1f min | Utilisation: %.0f%%\n', ...
                mean_wait_min, utilisation * 100);
    catch ME
        fprintf('  [ERROR] Simulation failed for N_oph=%d: %s\n', N_oph, ME.message);
        results(idx, :) = [N_oph, NaN, NaN];
    end
end

% ── Save tabular results ───────────────────────────────────────────────────
T = table(N_oph_values', ...
          round(results(:, 2), 1), ...
          round(results(:, 3) * 100, 1), ...
          'VariableNames', {'N_Ophthalmologists', 'Mean_Wait_Min', 'Utilisation_Pct'});
writetable(T, 'sweep_results.csv');
fprintf('\nResults saved to matlab/sweep_results.csv\n');

% ── Plot and save chart ────────────────────────────────────────────────────
fig = figure('Visible', 'off');
yyaxis left
plot(N_oph_values, results(:, 2), 'b-o', 'LineWidth', 2);
ylabel('Mean Ophthalmologist Queue Wait Time (min)');
yyaxis right
plot(N_oph_values, results(:, 3) * 100, 'r--s', 'LineWidth', 2);
ylabel('Ophthalmologist Utilisation (%)');
xlabel('Number of Ophthalmologists (Technician Count Fixed at 3)');
title('NETRA-DR District Workflow — Bottleneck Sweep (PLACEHOLDER RATES)');
grid on;
legend({'Queue Wait Time (min)', 'Utilisation (%)'}, 'Location', 'northeast');

% Annotate optimal point
[~, opt_idx] = min(abs(results(:, 3) - 0.85));  % ~85% utilisation target
xline(N_oph_values(opt_idx), 'g--', sprintf('~Optimal: N=%d', N_oph_values(opt_idx)));

saveas(fig, 'sweep_chart.png');
fprintf('Chart saved to matlab/sweep_chart.png\n');
close(fig);

disp('Ratio sweep complete. See sweep_results.csv and sweep_chart.png.');
