function result = runVesselSegmentation(preprocessedImage, modelDir)
%RUNVESSELSEGMENTATION Phase 2 vessel segmentation -- mirrors pipeline/structure.py's run_vessel_segmentation().
%
%   result = netra.vessels.runVesselSegmentation(preprocessedImage, modelDir)
%
% Frozen U-Net (trained on DRIVE in PyTorch, imported here as a frozen ONNX
% artifact -- see matlab/README.md). Output is already sigmoid-activated
% (baked into the exported graph), so this function only thresholds and
% resizes back to the source resolution -- exactly like the Python version.

    contract = netra.contract.loadModelContract(modelDir, 'segmentation');

    inputSize = contract.input_size(:)';
    originalHW = [size(preprocessedImage, 1), size(preprocessedImage, 2)];
    resized = imresize(preprocessedImage, [inputSize(1), inputSize(2)], 'bilinear');

    normSpec = contract.normalization;
    meanVec = reshape(normSpec.mean(:), 1, 1, 3);
    stdVec = reshape(normSpec.std(:), 1, 1, 3);
    imgFloat = double(resized);
    normalized = (imgFloat - meanVec) ./ stdVec;

    chw = permute(normalized, [3, 1, 2]);
    nchw = reshape(chw, [1, size(chw)]);

    outputs = netra.onnxio.runInference(contract.model_path_, 'input', nchw, {'vessel_prob'});
    probMap = squeeze(outputs{1});  % H x W, already in [0,1]

    threshold = contract.threshold;
    binaryResized = probMap >= threshold;
    binaryMask = imresize(uint8(binaryResized) * 255, originalHW, 'nearest');
    binaryMask = uint8(binaryMask > 127) * 255;

    overlay = drawOverlay(preprocessedImage, binaryMask, [0, 255, 0], 0.5);

    result = struct('vessel_mask', binaryMask, 'vessel_overlay', overlay, ...
        'model_name', contract.model_name, 'model_version', contract.model_version);
end

function overlay = drawOverlay(baseImage, mask, colorRGB, alpha)
    if max(baseImage(:)) <= 1.5
        base = uint8(baseImage * 255);
    else
        base = uint8(baseImage);
    end
    overlay = base;
    maskLogical = mask > 0;
    for c = 1:3
        chan = double(base(:, :, c));
        chan(maskLogical) = (1 - alpha) * chan(maskLogical) + alpha * colorRGB(c);
        overlay(:, :, c) = uint8(chan);
    end
end
