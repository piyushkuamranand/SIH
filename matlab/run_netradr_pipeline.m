function result = run_netradr_pipeline(imagePath, varargin)
%RUN_NETRADR_PIPELINE NETRA-DR full pipeline orchestrator, implemented natively in MATLAB.
%
%   result = run_netradr_pipeline(imagePath)
%   result = run_netradr_pipeline(imagePath, 'ModelsRoot', path, 'ConfigsRoot', path)
%
% Mirrors pipeline/report.py's run_full_pipeline() stage order exactly:
%   quality -> (reject halts here) -> preprocessing -> vessels -> lesions ->
%   MA -> NV (interface only) -> grading -> calibration -> decision -> model
%   attention -> report
%
% All paths are derived from this file's own location (mfilename/fileparts)
% so the pipeline works after the repository is cloned or moved to any
% drive/folder -- nothing here is machine-specific.
%
% Never silently swallows an exception: every stage failure is recorded in
% result.errors with {stage, error_type, message, recoverable, recommended_action},
% and the corresponding result.<stage> is left empty/absent rather than a
% fabricated value -- exactly like pipeline/report.py's per-phase try/except.
%
% Returns a struct: result.quality, result.preprocessing, result.vessels,
% result.lesions, result.ma, result.nv, result.grading, result.calibration,
% result.decision, result.explainability, result.timing, result.errors,
% result.stopped_at_quality.

    repoRoot = fileparts(fileparts(mfilename('fullpath')));  % matlab/.. = repo root

    p = inputParser;
    addParameter(p, 'ModelsRoot', fullfile(repoRoot, 'models'));
    addParameter(p, 'ConfigsRoot', fullfile(repoRoot, 'configs'));
    parse(p, varargin{:});
    modelsRoot = p.Results.ModelsRoot;
    configsRoot = p.Results.ConfigsRoot;

    pipelineStart = tic;
    result = struct();
    result.errors = {};
    result.timing = struct();
    result.stopped_at_quality = false;

    if ~isfile(imagePath)
        error('netra:pipeline:missingImage', 'Input image not found: %s', imagePath);
    end

    % ---- Phase 1: Quality ----
    t0 = tic;
    try
        result.quality = netra.quality.assessQuality(imagePath, fullfile(modelsRoot, 'quality'));
        result.timing.quality_gate = toc(t0);
    catch e
        result = recordError(result, 'quality', e, false, ...
            'Verify models/quality/metadata.json and iqa_thresholds.json exist and are valid.');
        result.stopped_at_quality = true;
        result.timing.total = toc(pipelineStart);
        return
    end

    if strcmpi(result.quality.quality_label, 'REJECT')
        result.stopped_at_quality = true;
        result.timing.total = toc(pipelineStart);
        return
    end

    % ---- Preprocessing (canonical model-input space) ----
    t0 = tic;
    try
        [preImg, preInfo] = netra.preprocess.preprocessImage(imagePath, fullfile(configsRoot, 'preprocessing.json'));
        result.preprocessing = struct('image', preImg, 'info', preInfo);
        result.timing.preprocessing = toc(t0);
    catch e
        result = recordError(result, 'preprocessing', e, false, 'Verify configs/preprocessing.json.');
        result.timing.total = toc(pipelineStart);
        return
    end

    % ---- Phase 2a: Vessels ----
    t0 = tic;
    try
        result.vessels = netra.vessels.runVesselSegmentation(preImg, fullfile(modelsRoot, 'vessel_seg'));
        result.timing.vessels = toc(t0);
    catch e
        result = recordError(result, 'vessels', e, true, ...
            'Vessel analysis unavailable: model artifact not found or inference failed.');
    end

    % ---- Phase 2b: Lesions (HE/EX/SE) ----
    t0 = tic;
    lesionOut = struct('he_presence', false, 'ex_area', 0, 'se_area', 0);
    try
        lesionOut = netra.lesions.runLesionSegmentation(preImg, fullfile(modelsRoot, 'lesion_seg'));
        result.lesions = lesionOut;
        result.timing.lesions = toc(t0);
    catch e
        result = recordError(result, 'lesions', e, true, ...
            'Lesion analysis unavailable: model artifact not found or inference failed.');
    end

    % ---- Phase 2c: MA ----
    t0 = tic;
    maCount = 0;
    try
        maOut = netra.ma.runMADetection(preImg, fullfile(modelsRoot, 'ma_detector'));
        result.ma = maOut;
        maCount = maOut.ma_count;
        result.timing.ma = toc(t0);
    catch e
        result = recordError(result, 'ma', e, true, ...
            'MA analysis unavailable: model artifact not found or inference failed.');
    end

    % ---- Phase 2d: NV (interface only, honestly unavailable) ----
    try
        result.nv = netra.anatomy.runNVAnalysis(preImg, modelsRoot);
    catch e
        result = recordError(result, 'nv', e, true, 'Neovascularization analysis unavailable.');
    end

    % ---- Phase 3: Grading + Calibration + Decision ----
    t0 = tic;
    try
        gradingOut = netra.grading.runGrading(preImg, fullfile(modelsRoot, 'grading'));
        result.grading = gradingOut;
        result.timing.grading = toc(t0);

        t0 = tic;
        calOut = netra.calibration.applyCalibration(gradingOut.probabilities, fullfile(configsRoot, 'calibration.json'));
        result.calibration = calOut;
        result.timing.calibration = toc(t0);

        t0 = tic;
        result.decision = netra.decision.runDecisionFusion(calOut.calibrated_probabilities, maCount, ...
            lesionOut.he_presence, lesionOut.ex_area, result.quality.quality_label, ...
            fullfile(configsRoot, 'decision_rule.json'), fullfile(modelsRoot, 'decision_fusion'));
        result.timing.decision = toc(t0);

        % ---- Phase 4: Model attention ----
        t0 = tic;
        result.explainability = netra.explain.computeModelAttention(gradingOut.features, ...
            gradingOut.severity_class, fullfile(modelsRoot, 'grading'), gradingOut.contract, preImg);
        result.timing.gradcam = toc(t0);
    catch e
        result = recordError(result, 'grading', e, false, ...
            'Grading unavailable: model artifact not found. Downstream calibration/decision/explainability also unavailable.');
    end

    result.timing.total = toc(pipelineStart);
end

function result = recordError(result, stage, e, recoverable, recommendedAction)
    entry = struct('stage', stage, 'error_type', e.identifier, 'message', e.message, ...
        'recoverable', recoverable, 'recommended_action', recommendedAction);
    result.errors{end+1} = entry;
    warning('netra:pipeline:stageFailed', '[%s] %s', stage, e.message);
end
