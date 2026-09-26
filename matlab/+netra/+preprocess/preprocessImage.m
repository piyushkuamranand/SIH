function [preprocessed, info] = preprocessImage(imagePath, configPath)
%PREPROCESSIMAGE Canonical NETRA-DR preprocessing, implemented natively in MATLAB.
%
%   [preprocessed, info] = netra.preprocess.preprocessImage(imagePath, configPath)
%
% Reproduces the SAME four-step chain as pipeline/preprocessing.py's
% preprocess() -- FOV crop -> resize -> CLAHE -> normalize -- reading every
% parameter from configs/preprocessing.json (never hardcoded here). This is
% the model-input preprocessing contract; do not add any extra enhancement
% step into this function, or the model input distribution would silently
% diverge from what the frozen ONNX models were trained on.
%
% KNOWN, DOCUMENTED CROSS-PLATFORM LIMITATION (see docs/matlab_parity_report.md):
% MATLAB's adapthisteq() and OpenCV's cv2.createCLAHE() (used by the Python
% pipeline) are DIFFERENT CLAHE implementations with different clip-limit
% semantics. Parameters are best-effort matched (tile grid size mapped
% directly; clip limit re-derived for adapthisteq's normalized [0,1] scale),
% but pixel-for-pixel identical output is NOT achievable without
% reimplementing OpenCV's exact algorithm. This causes a small, bounded,
% honestly-documented divergence from the Python-preprocessed image -- not a
% floating-point rounding difference, an algorithmic one. Downstream
% predictions may differ on borderline cases as a result.
%
% Inputs:
%   imagePath  - path to a raw fundus image (jpg/png)
%   configPath - path to configs/preprocessing.json (required, no default
%                baked in here -- fail closed if not supplied)
%
% Output:
%   preprocessed - HxWx3 single, range matching config normalization.range
%                  (matches pipeline.preprocessing.preprocess()'s float32 output)
%   info         - struct with fov_bbox, target_size, source_size (for report/debug)

    if ~isfile(configPath)
        error('netra:preprocess:missingConfig', 'Preprocessing config not found: %s', configPath);
    end
    cfg = jsondecode(fileread(configPath));

    if ~isfile(imagePath)
        error('netra:preprocess:missingImage', 'Input image not found: %s', imagePath);
    end

    try
        raw = imread(imagePath);
    catch readErr
        error('netra:preprocess:corruptImage', ...
            'Corrupted or unsupported image file: %s. Details: %s', imagePath, readErr.message);
    end
    if size(raw, 3) == 1
        raw = repmat(raw, 1, 1, 3);
    elseif size(raw, 3) == 4
        raw = raw(:, :, 1:3);
    end
    sourceSize = size(raw);

    % ---- 1. FOV crop ----
    fovThreshold = cfg.fov_crop.threshold;
    fovMargin = cfg.fov_crop.margin;
    gray = rgb2gray(raw);
    mask = gray > fovThreshold;
    if ~any(mask(:))
        error('netra:preprocess:emptyFov', ...
            'Image contains no detectable fundus field of view (all pixels below threshold %d).', fovThreshold);
    end
    [rows, cols] = find(mask);
    r0 = max(1, min(rows) - fovMargin);
    r1 = min(size(raw, 1), max(rows) + fovMargin);
    c0 = max(1, min(cols) - fovMargin);
    c1 = min(size(raw, 2), max(cols) + fovMargin);
    cropped = raw(r0:r1, c0:c1, :);

    % ---- 2. Resize ----
    % Adaptive interpolation matches pipeline/preprocessing.py's resize():
    % cv2.INTER_AREA when downsampling (area-weighted averaging -- MATLAB's
    % closest equivalent is 'box'), cv2.INTER_LINEAR when upsampling.
    targetSize = cfg.target_size(:)';  % [H, W]
    curH = size(cropped, 1); curW = size(cropped, 2);
    if targetSize(1) < curH || targetSize(2) < curW
        resizeMethod = 'box';
    else
        resizeMethod = 'bilinear';
    end
    resized = imresize(cropped, [targetSize(1), targetSize(2)], resizeMethod);

    % ---- 3. CLAHE on L channel (LAB colour space) ----
    clipLimitCv = cfg.clahe.clip_limit;
    tileGrid = cfg.clahe.tile_grid_size(:)';
    labImg = rgb2lab(resized);
    Lchan = labImg(:, :, 1) / 100;  % rgb2lab L is [0,100]; adapthisteq expects [0,1]
    % Best-effort clip-limit mapping: cv2's clipLimit is an absolute
    % histogram-bin threshold (typical range 1-4); adapthisteq's ClipLimit
    % is normalized to (0,1] as a fraction of the tile's pixel count. There
    % is no exact conversion between the two -- clipLimitCv/64 keeps the
    % mapped value in adapthisteq's valid, typically-effective range for
    % clipLimitCv in [1,4], and is documented here as an approximation.
    matlabClipLimit = min(0.99, max(0.001, clipLimitCv / 64));
    Lenhanced = adapthisteq(Lchan, 'NumTiles', [tileGrid(1), tileGrid(2)], ...
                             'ClipLimit', matlabClipLimit);
    labImg(:, :, 1) = Lenhanced * 100;
    enhanced = lab2rgb(labImg, 'OutputType', 'uint8');

    % ---- 4. Normalize ----
    rangeVals = cfg.normalization.range(:)';
    imgFloat = single(enhanced) / 255.0;
    preprocessed = imgFloat * (rangeVals(2) - rangeVals(1)) + rangeVals(1);
    preprocessed = max(rangeVals(1), min(rangeVals(2), preprocessed));

    info = struct('fov_bbox', [r0, r1, c0, c1], 'target_size', targetSize, ...
                   'source_size', sourceSize, 'clahe_note', ...
                   'adapthisteq used (approximation of OpenCV CLAHE) -- see docs/matlab_parity_report.md');
end
