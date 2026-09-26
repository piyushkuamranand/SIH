function result = runMADetection(preprocessedImage, modelDir)
%RUNMADETECTION Phase 2 hybrid MA detection -- mirrors pipeline/structure.py's run_ma_detection().
%
%   result = netra.ma.runMADetection(preprocessedImage, modelDir)
%
% Stage A (classical): morphological top-hat on the green channel,
% reimplemented natively in MATLAB using the SAME parameters
% (tophat_disk_radius, tophat_threshold_factor) read from
% models/ma_detector/metadata.json -- identical algorithm to
% pipeline/structure.py's _extract_candidates_tophat (black-hat highlights
% dark blobs on a bright background; threshold = mean + factor*std).
%
% Stage B (CNN false-positive reducer): frozen small CNN (trained on IDRiD
% candidate patches in PyTorch, imported as frozen ONNX). Candidate
% coordinates are computed in the SAME canonical resolution the model was
% trained at (per its contract's input_size) -- this pipeline does not
% additionally downsample candidates, but note the known, documented
% limitation already recorded in docs/model_cards/ma_detector.md: the
% shared 512x512 canonical space itself is already a significant
% downsampling from IDRiD's native ~4288x2848, which is the primary
% measured cause of this detector's FROC gap vs. the literature -- MATLAB
% reproduces that same canonical-space behaviour, it does not fix it.
%
% method must be 'top_hat' -- this MATLAB implementation does not (yet)
% provide the matched_filter alternative; it errors clearly if the contract
% requests an unsupported method rather than silently using a different one.

    contract = netra.contract.loadModelContract(modelDir, 'ma_detector');

    method = lower(string(contract.candidate_extraction_method));
    if method ~= "top_hat"
        error('netra:ma:unsupportedMethod', ...
            ['MATLAB MA module implements ''top_hat'' only (matches the method actually ' ...
             'configured in models/ma_detector/metadata.json). Contract requests ''%s''.'], method);
    end

    diskRadius = getFieldOr(contract, 'tophat_disk_radius', 6);
    thresholdFactor = getFieldOr(contract, 'tophat_threshold_factor', 2.0);
    patchSize = double(contract.patch_size);
    positiveClassIdx = double(getFieldOr(contract, 'ma_positive_class_index', 1));

    candidates = extractCandidatesTopHat(preprocessedImage, diskRadius, thresholdFactor);

    fpReducerPath = fullfile(modelDir, contract.fp_reducer_model_file);
    if ~isfile(fpReducerPath)
        error('netra:ma:missingArtifact', 'FP-reducer ONNX model not found: %s', fpReducerPath);
    end

    outputFormat = lower(string(contract.output_format));
    trueMaLocations = zeros(0, 2);
    for k = 1:size(candidates, 1)
        row = candidates(k, 1); col = candidates(k, 2);
        patch = preparePatch(preprocessedImage, row, col, patchSize);
        if isempty(patch)
            continue
        end
        outputs = netra.onnxio.runInference(fpReducerPath, 'input', patch, {'probs'});
        probs = squeeze(outputs{1});
        probs = probs(:)';
        if outputFormat == "softmax"
            % already softmax-activated in the exported graph
        elseif any(outputFormat == ["sigmoid", "logits"])
            probs = 1 ./ (1 + exp(-probs));
        end
        if numel(probs) > positiveClassIdx
            [~, predictedClass0] = max(probs);
            predictedClass = predictedClass0 - 1;
        else
            predictedClass = double(probs(1) >= 0.5);
        end
        if predictedClass == positiveClassIdx
            trueMaLocations(end+1, :) = [row, col]; %#ok<AGROW>
        end
    end

    maCount = size(trueMaLocations, 1);
    overlay = drawMaOverlay(preprocessedImage, trueMaLocations);

    result = struct('ma_count', maCount, 'ma_locations', trueMaLocations, ...
        'ma_overlay', overlay, 'model_name', 'ma_hybrid_tophat_cnn');
end

function v = getFieldOr(s, name, default)
    if isfield(s, name)
        v = s.(name);
    else
        v = default;
    end
end

function candidates = extractCandidatesTopHat(preprocessedImage, diskRadius, thresholdFactor)
    if max(preprocessedImage(:)) <= 1.5
        img8 = uint8(preprocessedImage * 255);
    else
        img8 = uint8(preprocessedImage);
    end
    green = img8(:, :, 2);

    se = strel('disk', diskRadius);
    tophatImg = double(imbothat(green, se));  % black-hat: highlights dark blobs on bright background

    mu = mean(tophatImg(:));
    sigma = std(tophatImg(:));
    threshold = mu + thresholdFactor * sigma;

    bw = tophatImg > threshold;
    stats = regionprops(bw, 'Centroid');
    n = numel(stats);
    candidates = zeros(n, 2);
    for i = 1:n
        c = stats(i).Centroid;  % [x, y] = [col, row]
        candidates(i, :) = [round(c(2)), round(c(1))];  % [row, col]
    end
end

function patch = preparePatch(preprocessedImage, row, col, patchSize)
    [h, w, ~] = size(preprocessedImage);
    half = floor(patchSize / 2);
    r0 = row - half; r1 = row + half;
    c0 = col - half; c1 = col + half;
    if r0 < 1 || r1 > h || c0 < 1 || c1 > w
        patch = [];
        return
    end
    cropped = preprocessedImage(r0:r1-1, c0:c1-1, :);
    if size(cropped, 1) ~= patchSize || size(cropped, 2) ~= patchSize
        cropped = imresize(cropped, [patchSize, patchSize], 'bilinear');
    end
    chw = permute(double(cropped), [3, 1, 2]);
    patch = reshape(chw, [1, size(chw)]);
end

function overlay = drawMaOverlay(baseImage, locations)
    if max(baseImage(:)) <= 1.5
        base = uint8(baseImage * 255);
    else
        base = uint8(baseImage);
    end
    overlay = base;
    r = 3;
    [h, w, ~] = size(base);
    for k = 1:size(locations, 1)
        row = locations(k, 1); col = locations(k, 2);
        rr = max(1, row-r):min(h, row+r);
        cc = max(1, col-r):min(w, col+r);
        overlay(rr, cc, 1) = 255;
        overlay(rr, cc, 2) = 0;
        overlay(rr, cc, 3) = 0;
    end
end
