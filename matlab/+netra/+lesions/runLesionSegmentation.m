function result = runLesionSegmentation(preprocessedImage, modelDir)
%RUNLESIONSEGMENTATION Phase 2 HE/EX/SE lesion segmentation -- mirrors pipeline/structure.py.
%
%   result = netra.lesions.runLesionSegmentation(preprocessedImage, modelDir)
%
% Frozen 3-channel U-Net (trained on IDRiD in PyTorch, imported as frozen
% ONNX -- see matlab/README.md). Channel order is read from
% contract.mask_labels -- NEVER assumed to be [HE,EX,SE] in code, exactly
% matching pipeline/structure.py's run_lesion_segmentation().

    contract = netra.contract.loadModelContract(modelDir, 'segmentation');
    maskLabels = upper(string(contract.mask_labels));
    for req = ["HE", "EX", "SE"]
        if ~any(maskLabels == req)
            error('netra:lesions:missingLabel', ...
                'Contract mask_labels %s does not contain required lesion label ''%s''.', ...
                mat2str(maskLabels), req);
        end
    end
    idxHE = find(maskLabels == "HE", 1);
    idxEX = find(maskLabels == "EX", 1);
    idxSE = find(maskLabels == "SE", 1);

    inputSize = contract.input_size(:)';
    originalHW = [size(preprocessedImage, 1), size(preprocessedImage, 2)];
    resized = imresize(preprocessedImage, [inputSize(1), inputSize(2)], 'bilinear');

    normSpec = contract.normalization;
    meanVec = reshape(normSpec.mean(:), 1, 1, 3);
    stdVec = reshape(normSpec.std(:), 1, 1, 3);
    normalized = (double(resized) - meanVec) ./ stdVec;
    chw = permute(normalized, [3, 1, 2]);
    nchw = reshape(chw, [1, size(chw)]);

    outputs = netra.onnxio.runInference(contract.model_path_, 'input', nchw, {'lesion_probs'});
    probMaps = squeeze(outputs{1});  % 3 x H x W

    threshold = contract.threshold;
    heMask = toMask(squeeze(probMaps(idxHE, :, :)), threshold, originalHW);
    exMask = toMask(squeeze(probMaps(idxEX, :, :)), threshold, originalHW);
    seMask = toMask(squeeze(probMaps(idxSE, :, :)), threshold, originalHW);

    hePresenceThreshold = getFieldOr(contract, 'he_presence_threshold', 50);
    hePresence = nnz(heMask) >= hePresenceThreshold;
    totalPixels = originalHW(1) * originalHW(2);
    exArea = nnz(exMask) / totalPixels;
    seArea = nnz(seMask) / totalPixels;

    overlay = drawLesionOverlay(preprocessedImage, heMask, exMask, seMask);

    result = struct('he_mask', heMask, 'ex_mask', exMask, 'se_mask', seMask, ...
        'he_presence', hePresence, 'ex_area', exArea, 'se_area', seArea, ...
        'lesion_overlay', overlay, 'model_name', contract.model_name, ...
        'model_version', contract.model_version);
end

function v = getFieldOr(s, name, default)
    if isfield(s, name)
        v = s.(name);
    else
        v = default;
    end
end

function mask = toMask(probMap, threshold, originalHW)
    binarySmall = uint8(probMap >= threshold) * 255;
    resized = imresize(binarySmall, originalHW, 'nearest');
    mask = uint8(resized > 127) * 255;
end

function overlay = drawLesionOverlay(baseImage, heMask, exMask, seMask)
    if max(baseImage(:)) <= 1.5
        base = uint8(baseImage * 255);
    else
        base = uint8(baseImage);
    end
    overlay = base;
    overlay = applyColor(overlay, heMask, [255, 0, 0], 0.45);   % HE: red
    overlay = applyColor(overlay, exMask, [255, 200, 0], 0.45); % EX: yellow
    overlay = applyColor(overlay, seMask, [0, 100, 255], 0.45); % SE: blue
end

function img = applyColor(img, mask, colorRGB, alpha)
    maskLogical = mask > 0;
    for c = 1:3
        chan = double(img(:, :, c));
        chan(maskLogical) = (1 - alpha) * chan(maskLogical) + alpha * colorRGB(c);
        img(:, :, c) = uint8(chan);
    end
end
