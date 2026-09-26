function result = runDecisionFusion(calibratedProbabilities, maCount, hePresence, exArea, qualityLabel, configPath, decisionModelDir)
%RUNDECISIONFUSION Phase 3 referral decision -- mirrors pipeline/decision.py's run_decision_fusion().
%
%   result = netra.decision.runDecisionFusion(calibratedProbabilities, maCount, ...
%                hePresence, exArea, qualityLabel, configPath, decisionModelDir)
%
% Reads configs/decision_rule.json for the quality-tier thresholds. If a
% fitted logistic-regression fusion model exists at
% <decisionModelDir>/metadata.json (fitted=true, with weights+intercept),
% it is used; otherwise this function uses the SAME documented grade-alone
% quality-tier fallback the Python prototype uses, and reports
% fitted=false honestly -- it never invents fusion coefficients.

    qualityNorm = validatestring(qualityLabel, {'Good', 'Borderline', 'Reject', 'GOOD', 'BORDERLINE', 'REJECT'});
    qualityNorm = [upper(qualityNorm(1)), lower(qualityNorm(2:end))];
    if strcmpi(qualityNorm, 'Reject')
        error('netra:decision:rejectedImage', ...
            'Reject-quality image cannot receive an automated referral decision.');
    end

    probs = double(calibratedProbabilities(:))';
    probs = probs / sum(probs);
    [~, predictedGrade0] = max(probs);
    predictedGrade = predictedGrade0 - 1;
    referableProbability = sum(probs(3:end));  % Grade >= 2 => indices 3,4,5 (1-based for grades 2,3,4)

    grade_alone_threshold = 0.50;
    grade_alone_referable = (referableProbability >= grade_alone_threshold) || (predictedGrade >= 2);
    grade_alone_decision = ternary(grade_alone_referable, 'REFER', 'NO REFER');

    fittedModel = tryLoadFittedFusion(decisionModelDir);
    cfg = loadDecisionConfig(configPath);

    evidence = struct('ma_count', max(0, round(maCount)), 'he_presence', logical(hePresence), ...
        'ex_area', max(0, min(1, exArea)));

    if ~isempty(fittedModel)
        isBorderline = strcmpi(qualityNorm, 'Borderline');
        features = [referableProbability, evidence.ma_count, double(evidence.he_presence), ...
                    evidence.ex_area, double(isBorderline)];
        weights = fittedModel.weights(:)';
        if numel(weights) ~= numel(features)
            error('netra:decision:weightMismatch', ...
                'Fusion model weights dimension mismatch: expected %d, got %d.', numel(features), numel(weights));
        end
        logit = fittedModel.intercept + sum(weights .* features);
        fusionProb = 1 / (1 + exp(-logit));
        modelThreshold = getFieldOr(fittedModel, 'threshold', 0.50);
        isReferable = fusionProb >= modelThreshold;
        referableDecision = ternary(isReferable, 'REFER', 'NO REFER');
        thresholdApplied = modelThreshold;
        fitted = true;
        fusionStatus = 'fitted_logistic_regression';
        reasonMsg = sprintf(['Fitted logistic regression decision: fused probability = %.3f (threshold: %.2f). ' ...
            'Evidence: P(Grade>=2)=%.3f, MAs=%d, HE=%d, EX_area=%.4f, Quality=%s.'], ...
            fusionProb, modelThreshold, referableProbability, evidence.ma_count, evidence.he_presence, evidence.ex_area, qualityNorm);
    else
        if strcmpi(qualityNorm, 'Borderline')
            thresholdApplied = getFieldOr(getFieldOr(cfg.thresholds, 'borderline_quality', struct('referable_prob_threshold', 0.35)), 'referable_prob_threshold', 0.35);
        else
            thresholdApplied = getFieldOr(getFieldOr(cfg.thresholds, 'good_quality', struct('referable_prob_threshold', 0.50)), 'referable_prob_threshold', 0.50);
        end
        isReferable = (referableProbability >= thresholdApplied) || (predictedGrade >= 2);
        referableDecision = ternary(isReferable, 'REFER', 'NO REFER');
        fitted = false;
        fusionStatus = 'using grade-alone fallback, fusion model not yet trained';
        if isReferable
            reasonMsg = sprintf(['Referral recommended (%s quality tier): calibrated P(Grade>=2) = %.3f >= ' ...
                'threshold %.2f (predicted ICDR Grade %d). Lesion evidence logged: %d MAs, HE present=%d, EX area=%.4f.'], ...
                qualityNorm, referableProbability, thresholdApplied, predictedGrade, evidence.ma_count, evidence.he_presence, evidence.ex_area);
        else
            reasonMsg = sprintf(['No referral needed (%s quality tier): calibrated P(Grade>=2) = %.3f < ' ...
                'threshold %.2f (predicted ICDR Grade %d). Lesion evidence logged: %d MAs, HE present=%d, EX area=%.4f.'], ...
                qualityNorm, referableProbability, thresholdApplied, predictedGrade, evidence.ma_count, evidence.he_presence, evidence.ex_area);
        end
    end

    result = struct('referable_decision', referableDecision, 'grade_alone_decision', grade_alone_decision, ...
        'predicted_grade', predictedGrade, 'referable_probability', referableProbability, ...
        'quality_tier', qualityNorm, 'threshold_applied', thresholdApplied, 'evidence', evidence, ...
        'fusion_status', fusionStatus, 'fitted', fitted, 'reason', reasonMsg);
end

function s = ternary(cond, a, b)
    if cond, s = a; else, s = b; end
end

function v = getFieldOr(s, name, default)
    if isstruct(s) && isfield(s, name)
        v = s.(name);
    else
        v = default;
    end
end

function cfg = loadDecisionConfig(configPath)
    if isfile(configPath)
        cfg = jsondecode(fileread(configPath));
    else
        cfg = struct('thresholds', struct( ...
            'good_quality', struct('referable_prob_threshold', 0.50), ...
            'borderline_quality', struct('referable_prob_threshold', 0.35)));
    end
end

function m = tryLoadFittedFusion(decisionModelDir)
    m = [];
    metaPath = fullfile(decisionModelDir, 'metadata.json');
    if ~isfile(metaPath)
        return
    end
    try
        meta = jsondecode(fileread(metaPath));
        if isfield(meta, 'fitted') && meta.fitted && isfield(meta, 'weights') && isfield(meta, 'intercept')
            m = meta;
        end
    catch
        m = [];
    end
end
