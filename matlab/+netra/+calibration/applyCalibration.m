function result = applyCalibration(probabilities, configPath)
%APPLYCALIBRATION Temperature-scale grading probabilities -- mirrors pipeline/grading.py's apply_calibration().
%
%   result = netra.calibration.applyCalibration(probabilities, configPath)
%
% Reads configs/calibration.json (the SAME file the Python prototype
% fitted -- temperature = 2.80, fitted by NLL minimization on the grading
% validation split, see docs/model_cards/grading.md). This function NEVER
% refits, retrains, or hardcodes a temperature value in MATLAB source code
% -- it only applies whatever value is currently on disk, and reports
% fitted=false honestly if the config is missing or unfitted.
%
% z_i = log(p_i); calibrated = softmax(z_i / T)

    probs = double(probabilities(:))';
    if any(probs < 0)
        error('netra:calibration:invalidInput', 'All probabilities must be non-negative.');
    end
    probSum = sum(probs);
    if probSum <= 0
        error('netra:calibration:invalidInput', 'Sum of probabilities must be strictly positive.');
    end
    normProbs = probs / probSum;

    if isfile(configPath)
        cfg = jsondecode(fileread(configPath));
        temperature = cfg.temperature;
        fitted = logical(cfg.fitted);
    else
        temperature = 1.0;
        fitted = false;
    end

    if temperature <= 0
        error('netra:calibration:invalidTemperature', 'Temperature must be strictly positive, got %g.', temperature);
    end

    if abs(temperature - 1.0) < 1e-9
        calibrated = normProbs;
    else
        eps_ = 1e-12;
        clipped = max(normProbs, eps_);
        logits = log(clipped) / temperature;
        calibrated = softmaxRow(logits);
    end

    confidence = max(calibrated);
    result = struct('calibrated_probabilities', calibrated, 'confidence', confidence, ...
        'temperature', temperature, 'fitted', fitted);
end

function p = softmaxRow(z)
    z = z - max(z);
    e = exp(z);
    p = e / sum(e);
end
