classdef NetraDRApp < handle
%NETRADRAPP Minimal MATLAB demonstration UI for NETRA-DR (uifigure-based).
%
%   app = NetraDRApp()
%
% This is an ADDITIONAL demonstration path alongside the existing, unchanged
% Flask/Python UI (app/app.py) -- it does not replace it. It calls the same
% native-MATLAB run_netradr_pipeline() orchestrator that everything else in
% matlab/ uses. Clean medical/research styling, no fabricated metrics: every
% displayed value comes directly from the pipeline result struct.

    properties
        Fig
        UploadLabel
        PreviewAxes
        RunButton
        ReportButton
        StatusLabel
        ResultsPanel
        ResultsText
        ImagePath
        LastResult
        RepoRoot
    end

    methods
        function app = NetraDRApp()
            % This file lives at matlab/ui/NetraDRApp.m, so repo root is
            % three levels up: ui/ -> matlab/ -> repo root.
            app.RepoRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));

            app.Fig = uifigure('Name', 'NETRA-DR — MATLAB Demonstration', 'Position', [100 100 900 700], ...
                'Color', [0.043 0.059 0.098]);

            title1 = uilabel(app.Fig, 'Text', 'NETRA-DR', 'FontSize', 24, 'FontWeight', 'bold', ...
                'FontColor', [0.22 0.74 0.97], 'Position', [30 650 400 30]);
            title2 = uilabel(app.Fig, 'Text', 'Explainable AI for Diabetic Retinopathy Screening', ...
                'FontSize', 12, 'FontColor', [0.58 0.64 0.72], 'Position', [30 630 500 20]); %#ok<NASGU>
            title3 = uilabel(app.Fig, 'Text', 'Screening aid — human review required. Not a diagnostic device.', ...
                'FontSize', 10, 'FontColor', [0.58 0.64 0.72], 'FontAngle', 'italic', 'Position', [30 612 500 18]); %#ok<NASGU>

            uploadBtn = uibutton(app.Fig, 'Text', 'Upload Fundus Image', 'Position', [30 570 160 30], ...
                'ButtonPushedFcn', @(~,~) app.onUpload());
            demoBtn = uibutton(app.Fig, 'Text', 'Load Demo Case', 'Position', [200 570 140 30], ...
                'ButtonPushedFcn', @(~,~) app.onLoadDemo());
            app.RunButton = uibutton(app.Fig, 'Text', 'Run Analysis', 'Position', [350 570 120 30], ...
                'Enable', 'off', 'ButtonPushedFcn', @(~,~) app.onRunAnalysis()); %#ok<NASGU>
            app.ReportButton = uibutton(app.Fig, 'Text', 'Generate Report', 'Position', [480 570 140 30], ...
                'Enable', 'off', 'ButtonPushedFcn', @(~,~) app.onGenerateReport()); %#ok<NASGU>

            app.UploadLabel = uilabel(app.Fig, 'Text', '(no image selected)', 'Position', [30 545 600 18], ...
                'FontColor', [0.58 0.64 0.72]);

            app.PreviewAxes = uiaxes(app.Fig, 'Position', [30 320 280 210]);
            app.PreviewAxes.Toolbar.Visible = 'off';
            title(app.PreviewAxes, 'Preview');

            app.StatusLabel = uilabel(app.Fig, 'Text', 'Status: idle', 'Position', [330 505 500 18], ...
                'FontColor', [0.22 0.74 0.97]);

            app.ResultsText = uitextarea(app.Fig, 'Position', [30 30 840 270], 'Editable', 'off', ...
                'FontName', 'Consolas', 'Value', {'Results will appear here after Run Analysis.'});
        end

        function onUpload(app)
            [file, pathStr] = uigetfile({'*.jpg;*.jpeg;*.png', 'Fundus images'}, 'Select a fundus image');
            if isequal(file, 0)
                return
            end
            app.ImagePath = fullfile(pathStr, file);
            app.showPreview();
        end

        function onLoadDemo(app)
            demoDir = fullfile(app.RepoRoot, 'data', 'demo');
            [file, ok] = listdlg('PromptString', 'Select a demo case:', ...
                'ListString', {'good_sample.jpg', 'reject_sample.jpg', ...
                    'aptos_grade0_0d0b8fc9ab5c.png', 'aptos_grade2_025a169a0bb0.png', 'aptos_grade4_875a2fc5fe23.png'}, ...
                'SelectionMode', 'single');
            if ~ok
                return
            end
            names = {'good_sample.jpg', 'reject_sample.jpg', ...
                'aptos_grade0_0d0b8fc9ab5c.png', 'aptos_grade2_025a169a0bb0.png', 'aptos_grade4_875a2fc5fe23.png'};
            app.ImagePath = fullfile(demoDir, names{file});
            app.showPreview();
        end

        function showPreview(app)
            app.UploadLabel.Text = app.ImagePath;
            try
                img = imread(app.ImagePath);
                imshow(img, 'Parent', app.PreviewAxes);
                app.RunButton.Enable = 'on';
                app.StatusLabel.Text = 'Status: image loaded, ready to run.';
            catch e
                app.StatusLabel.Text = ['Status: invalid image - ' e.message];
                app.RunButton.Enable = 'off';
            end
        end

        function onRunAnalysis(app)
            app.StatusLabel.Text = 'Status: running pipeline (quality -> preprocessing -> evidence -> grading -> attention)...';
            drawnow;
            try
                app.LastResult = run_netradr_pipeline(app.ImagePath);
                app.renderResults();
                app.ReportButton.Enable = 'on';
                app.StatusLabel.Text = sprintf('Status: done in %.2f s.', app.LastResult.timing.total);
            catch e
                app.StatusLabel.Text = ['Status: pipeline error - ' e.message];
                app.ResultsText.Value = {sprintf('PIPELINE ERROR: %s', e.message)};
            end
        end

        function renderResults(app)
            r = app.LastResult;
            lines = {};
            lines{end+1} = sprintf('=== PHASE 1: IMAGE QUALITY ===');
            lines{end+1} = sprintf('Status: %s  (score %.3f)', r.quality.quality_label, r.quality.quality_score);
            for i = 1:numel(r.quality.reasons)
                lines{end+1} = ['  - ' r.quality.reasons{i}]; %#ok<AGROW>
            end

            if r.stopped_at_quality
                lines{end+1} = '';
                lines{end+1} = 'REJECT: downstream analysis halted. Recapture required. Nothing fabricated.';
                app.ResultsText.Value = lines;
                return
            end

            lines{end+1} = '';
            lines{end+1} = '=== PHASE 2: RETINAL EVIDENCE ===';
            if isfield(r, 'vessels')
                lines{end+1} = sprintf('Vessels: %d px detected', nnz(r.vessels.vessel_mask));
            else
                lines{end+1} = 'Vessels: unavailable';
            end
            if isfield(r, 'lesions')
                lines{end+1} = sprintf('Hemorrhage present: %d | Exudate area: %.5f', r.lesions.he_presence, r.lesions.ex_area);
            else
                lines{end+1} = 'Lesions: unavailable';
            end
            if isfield(r, 'ma')
                lines{end+1} = sprintf('Microaneurysm count: %d', r.ma.ma_count);
            else
                lines{end+1} = 'MA: unavailable';
            end
            lines{end+1} = sprintf('Neovascularization: %s (%s)', r.nv.status, r.nv.reason);

            lines{end+1} = '';
            lines{end+1} = '=== PHASE 3: DR SEVERITY ===';
            if isfield(r, 'grading')
                icdrLabels = {'No DR', 'Mild NPDR', 'Moderate NPDR', 'Severe NPDR', 'Proliferative DR'};
                lines{end+1} = sprintf('Grade %d - %s', r.grading.severity_class, icdrLabels{r.grading.severity_class + 1});
                lines{end+1} = sprintf('Calibrated confidence: %.1f%% (T=%.2f, fitted=%d)', ...
                    r.calibration.confidence * 100, r.calibration.temperature, r.calibration.fitted);
                lines{end+1} = sprintf('Referral: %s  (grade-alone: %s)', r.decision.referable_decision, r.decision.grade_alone_decision);
                lines{end+1} = ['  ' r.decision.reason];
            else
                lines{end+1} = 'Grading: unavailable';
            end

            lines{end+1} = '';
            lines{end+1} = '=== PHASE 4: MODEL ATTENTION ===';
            if isfield(r, 'explainability')
                lines{end+1} = 'Model attention indicates image regions contributing to the model output;';
                lines{end+1} = 'it is not a substitute for clinician interpretation.';
                lines{end+1} = ['Method: ' r.explainability.method_note];
            else
                lines{end+1} = 'Model attention: unavailable';
            end

            lines{end+1} = '';
            lines{end+1} = '=== PROCESSING TIME ===';
            fns = fieldnames(r.timing);
            for i = 1:numel(fns)
                lines{end+1} = sprintf('%s: %.1f ms', fns{i}, r.timing.(fns{i}) * 1000); %#ok<AGROW>
            end

            if ~isempty(r.errors)
                lines{end+1} = '';
                lines{end+1} = '=== STAGE ERRORS (recoverable, no fabricated output) ===';
                for i = 1:numel(r.errors)
                    lines{end+1} = sprintf('[%s] %s -- %s', r.errors{i}.stage, r.errors{i}.message, r.errors{i}.recommended_action); %#ok<AGROW>
                end
            end

            app.ResultsText.Value = lines;
        end

        function onGenerateReport(app)
            outDir = fullfile(app.RepoRoot, 'matlab', 'reports');  % RepoRoot is now the true repo root (fixed above)
            try
                p = netra.report.generateReport(app.LastResult, app.ImagePath, outDir);
                app.StatusLabel.Text = ['Status: report written to ' p];
            catch e
                app.StatusLabel.Text = ['Status: report generation failed - ' e.message];
            end
        end
    end
end
