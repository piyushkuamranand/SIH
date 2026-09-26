function result = assessQuality(imagePath, modelDir)
%ASSESSQUALITY Native MATLAB rule-based IQA gate -- mirrors pipeline/quality.py exactly.
%
%   result = netra.quality.assessQuality(imagePath, modelDir)
%
% Loads the SAME models/quality/metadata.json + iqa_thresholds.json used by
% the Python prototype (via netra.contract.loadModelContract), measures
% focus (Laplacian variance), illumination (mean + clipped fractions), and
% field-of-view coverage in the SAME canonical 512x512 space, and applies
% the SAME threshold rules. No threshold is invented here -- every number
% comes from models/quality/iqa_thresholds.json, exactly as read by the
% Python implementation. If that file or a required field is missing, this
% function fails closed (errors) rather than guessing a threshold.
%
% Output struct fields: quality_label ('GOOD'|'BORDERLINE'|'REJECT'),
% quality_score, reasons (cellstr), measured (struct), model_name.

    contract = netra.contract.loadModelContract(modelDir, 'classifier');
    if ~strcmpi(contract.framework, 'rule_based')
        error('netra:quality:unsupportedFramework', ...
            ['MATLAB quality module currently implements the rule-based baseline only ' ...
             '(contract framework = ''%s''). This matches the framework actually shipped ' ...
             'in models/quality/metadata.json; if that changes, this function must be extended.'], ...
            contract.framework);
    end

    thresholdsPath = contract.model_path_;  % resolved by the contract loader
    if ~isfile(thresholdsPath)
        error('netra:quality:missingThresholds', 'IQA thresholds file not found: %s', thresholdsPath);
    end
    th = jsondecode(fileread(thresholdsPath));

    if ~isfile(imagePath)
        error('netra:quality:missingImage', 'Input image not found: %s', imagePath);
    end
    raw = imread(imagePath);
    if size(raw, 3) == 1
        raw = repmat(raw, 1, 1, 3);
    end

    fovBgThreshold = th.fov.background_intensity_threshold;
    grayFull = rgb2gray(raw);
    fovMaskFull = grayFull > fovBgThreshold;
    totalPx = numel(grayFull);
    fovPx = nnz(fovMaskFull);
    fovAreaFraction = double(fovPx) / double(totalPx);

    if fovPx == 0
        measured = struct('fov_area_fraction', 0, 'laplacian_variance', 0, ...
            'mean_intensity', 0, 'dark_clipped_fraction', 1, 'bright_clipped_fraction', 0);
    else
        [rows, cols] = find(fovMaskFull);
        cropped = raw(min(rows):max(rows), min(cols):max(cols), :);
        % 'box' approximates OpenCV's cv2.INTER_AREA (area-weighted averaging
        % on downsample) more closely than 'bilinear' -- pipeline/quality.py
        % uses INTER_AREA for this specific canonical-space resize.
        canonical = imresize(cropped, [512, 512], 'box');
        grayC = rgb2gray(canonical);
        fovMaskC = grayC > fovBgThreshold;
        fovPxC = nnz(fovMaskC);

        if fovPxC < 2
            measured = struct('fov_area_fraction', fovAreaFraction, 'laplacian_variance', 0, ...
                'mean_intensity', 0, 'dark_clipped_fraction', 1, 'bright_clipped_fraction', 0);
        else
            lap = fspecial('laplacian', 0);
            % 'symmetric' approximates OpenCV's default BORDER_REFLECT_101
            % boundary handling more closely than 'replicate' -- matters here
            % because focus is measured within the FOV mask, whose boundary
            % sits at the crop/resize edges.
            lapImg = imfilter(double(grayC), lap, 'symmetric');
            lapVarianceVals = lapImg(fovMaskC);
            % NB: normalize by N (population variance), matching numpy's np.var()
            % default (ddof=0) used by pipeline/quality.py -- MATLAB's var() default
            % is N-1 (sample variance) and would silently diverge from the Python
            % measurement otherwise.
            laplacianVariance = var(lapVarianceVals, 1);

            fovPixelsC = double(grayC(fovMaskC));
            meanIntensity = mean(fovPixelsC);
            darkClippedFraction = nnz(fovPixelsC < 15) / double(fovPxC);
            brightClippedFraction = nnz(fovPixelsC > 245) / double(fovPxC);

            measured = struct('fov_area_fraction', fovAreaFraction, ...
                'laplacian_variance', laplacianVariance, 'mean_intensity', meanIntensity, ...
                'dark_clipped_fraction', darkClippedFraction, 'bright_clipped_fraction', brightClippedFraction);
        end
    end

    decision = decideQuality(measured, th);

    result = struct('quality_label', decision.label, 'quality_score', decision.score, ...
        'reasons', {decision.reasons}, 'measured', measured, 'model_name', contract.model_name);
end

function decision = decideQuality(m, th)
    rejectReasons = {};
    borderlineReasons = {};

    rejectFov = th.fov.reject_min_area_fraction;
    borderlineFov = th.fov.borderline_min_area_fraction;
    if m.fov_area_fraction < rejectFov
        rejectReasons{end+1} = sprintf('field of view too small (%.1f%% of frame, need >= %.0f%%)', ...
            m.fov_area_fraction * 100, rejectFov * 100);
    elseif m.fov_area_fraction < borderlineFov
        borderlineReasons{end+1} = sprintf('field of view partially cropped (%.1f%% of frame)', m.fov_area_fraction * 100);
    end

    rejectFocus = th.focus.reject_max_laplacian_variance;
    borderlineFocus = th.focus.borderline_max_laplacian_variance;
    if m.laplacian_variance < rejectFocus
        rejectReasons{end+1} = sprintf('severe blur (focus score %.1f, need >= %.0f)', m.laplacian_variance, rejectFocus);
    elseif m.laplacian_variance < borderlineFocus
        borderlineReasons{end+1} = sprintf('reduced sharpness (focus score %.1f)', m.laplacian_variance);
    end

    rejectDark = th.illumination.reject_max_dark_clipped_fraction;
    rejectBright = th.illumination.reject_max_bright_clipped_fraction;
    borderlineDark = th.illumination.borderline_max_dark_clipped_fraction;
    borderlineBright = th.illumination.borderline_max_bright_clipped_fraction;
    if m.dark_clipped_fraction > rejectDark
        rejectReasons{end+1} = sprintf('severe underexposure (%.1f%% of FOV near-black)', m.dark_clipped_fraction * 100);
    elseif m.dark_clipped_fraction > borderlineDark
        borderlineReasons{end+1} = sprintf('partial underexposure (%.1f%% of FOV near-black)', m.dark_clipped_fraction * 100);
    end
    if m.bright_clipped_fraction > rejectBright
        rejectReasons{end+1} = sprintf('severe overexposure/glare (%.1f%% of FOV near-white)', m.bright_clipped_fraction * 100);
    elseif m.bright_clipped_fraction > borderlineBright
        borderlineReasons{end+1} = sprintf('partial overexposure/glare (%.1f%% of FOV near-white)', m.bright_clipped_fraction * 100);
    end

    idealLo = th.illumination.ideal_mean_range(1);
    idealHi = th.illumination.ideal_mean_range(2);
    slack = th.illumination.borderline_mean_slack;
    if m.mean_intensity < (idealLo - slack) || m.mean_intensity > (idealHi + slack)
        rejectReasons{end+1} = sprintf('illumination far outside expected range (mean intensity %.0f)', m.mean_intensity);
    elseif m.mean_intensity < idealLo || m.mean_intensity > idealHi
        borderlineReasons{end+1} = sprintf('illumination slightly outside ideal range (mean intensity %.0f)', m.mean_intensity);
    end

    if ~isempty(rejectReasons)
        label = 'REJECT'; reasons = rejectReasons;
    elseif ~isempty(borderlineReasons)
        label = 'BORDERLINE'; reasons = borderlineReasons;
    else
        label = 'GOOD'; reasons = {'focus, illumination, and field of view all within expected range'};
    end

    fovMargin = min(1.0, m.fov_area_fraction / max(borderlineFov, eps));
    focusMargin = min(1.0, m.laplacian_variance / max(borderlineFocus, eps));
    darkMargin = 1.0 - min(1.0, m.dark_clipped_fraction / max(borderlineDark, eps));
    brightMargin = 1.0 - min(1.0, m.bright_clipped_fraction / max(borderlineBright, eps));
    composite = max(0, min(1, mean([fovMargin, focusMargin, darkMargin, brightMargin])));

    switch label
        case 'GOOD'
            score = max(0, min(1, 0.55 + 0.45 * composite));
        case 'BORDERLINE'
            score = max(0.35, min(0.75, 0.45 + 0.20 * composite));
        otherwise
            score = max(0.35, min(0.95, 0.55 + 0.35 * (1 - composite)));
    end

    decision = struct('label', label, 'score', score, 'reasons', {reasons});
end
