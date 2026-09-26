function run_netradr_demo()
%RUN_NETRADR_DEMO One-command MATLAB demonstration entry point for NETRA-DR.
%
%   run_netradr_demo()
%
% From a MATLAB command window with the working directory anywhere:
%   run(fullfile('D:', 'SIH-1', 'matlab', 'run_netradr_demo.m'))   % adjust drive/path
% or, having cd'd into the repo:
%   run('matlab/run_netradr_demo.m')
% or from a terminal (verified in this environment, MATLAB R2026a):
%   matlab -batch "run('<repo>/matlab/run_netradr_demo.m')"
%   (batch mode validates the environment and launches the UI where a
%   display is available; for a live presentation, run this from an
%   interactive MATLAB desktop session instead of -batch so the uifigure
%   window is visible.)
%
% Steps: determine repo root -> validate model artifacts -> validate
% toolbox/Python availability -> launch the MATLAB demonstration UI
% (matlab/ui/NetraDRApp.m). Does not replace or modify the existing Flask
% prototype (app/app.py) -- this is an additional demonstration path.

    repoRoot = fileparts(mfilename('fullpath'));  % this file is at matlab/, so repoRoot IS matlab/
    repoRoot = fileparts(repoRoot);               % .. = actual repo root

    fprintf('%s\n', repmat('=', 1, 70));
    fprintf('  NETRA-DR MATLAB Demonstration -- Environment Validation\n');
    fprintf('%s\n', repmat('=', 1, 70));

    fprintf('MATLAB version: %s\n', version);

    requiredModels = {'quality', 'vessel_seg', 'lesion_seg', 'ma_detector', 'grading'};
    allReady = true;
    for i = 1:numel(requiredModels)
        stage = requiredModels{i};
        modelDir = fullfile(repoRoot, 'models', stage);
        metaPath = fullfile(modelDir, 'metadata.json');
        if isfile(metaPath)
            try
                meta = jsondecode(fileread(metaPath));
                modelFile = fullfile(modelDir, meta.model_file);
                if isfile(modelFile)
                    fprintf('  [OK]   %-14s %s\n', stage, meta.model_name);
                else
                    fprintf('  [MISS] %-14s metadata found but artifact missing: %s\n', stage, modelFile);
                    allReady = false;
                end
            catch e
                fprintf('  [MISS] %-14s invalid metadata.json: %s\n', stage, e.message);
                allReady = false;
            end
        else
            fprintf('  [MISS] %-14s metadata.json not found\n', stage);
            allReady = false;
        end
    end

    try
        pe = pyenv;
        fprintf('Python (for ONNX inference via onnxruntime): %s (%s)\n', pe.Version, pe.Executable);
    catch
        fprintf('WARNING: pyenv not available -- ONNX inference will fail (see matlab/README.md).\n');
        allReady = false;
    end

    if allReady
        fprintf('\nAll model artifacts and the Python/onnxruntime path are present.\n');
    else
        fprintf('\nWARNING: one or more models/environment pieces are missing -- affected stages will report\n');
        fprintf('"unavailable" honestly during the demo rather than crashing or fabricating output.\n');
    end

    matlabDir = fullfile(repoRoot, 'matlab');
    fprintf('\nLaunching MATLAB demonstration UI...\n');
    addpath(matlabDir);                     % so run_netradr_pipeline.m is on the path from the UI callbacks
    addpath(fullfile(matlabDir, 'ui'));     % ui/ is a plain folder (not a +package), NetraDRApp.m lives here
    app = NetraDRApp(); %#ok<NASGU>
end
