function result = runGrading(preprocessedImage, modelDir)
%RUNGRADING Phase 3 DR grading -- mirrors pipeline/grading.py's run_grading() exactly.
%
%   result = netra.grading.runGrading(preprocessedImage, modelDir)
%
% Loads models/grading/metadata.json via netra.contract.loadModelContract,
% resizes+normalizes preprocessedImage using ONLY the contract's input_size
% and normalization (mean/std) -- never a hardcoded value -- runs the frozen
% ResNet-50 ONNX model (imported weights, trained in PyTorch -- see
% matlab/README.md), and returns raw softmax probabilities + severity class.
% This is the SAME frozen ONNX file the Python prototype uses; the model
% itself was NOT retrained, converted, or modified in any way.
%
% Input:
%   preprocessedImage - HxWx3 single/double, canonical-space image from
%                        netra.preprocess.preprocessImage (range matches
%                        configs/preprocessing.json's normalization.range)
%   modelDir           - models/grading (or override)
%
% Output struct: severity_class, probabilities (1x5), model_name,
% model_version, logits (1x5, pre-softmax -- needed by calibration),
% features (raw CxHxW feature map -- needed by model attention).

    contract = netra.contract.loadModelContract(modelDir, 'classifier');

    inputSize = contract.input_size(:)';  % [H, W]
    resized = imresize(preprocessedImage, [inputSize(1), inputSize(2)], 'bilinear');

    normSpec = contract.normalization;
    meanVec = reshape(normSpec.mean(:), 1, 1, 3);
    stdVec = reshape(normSpec.std(:), 1, 1, 3);
    imgFloat = double(resized);
    if max(imgFloat(:)) > 1.5
        imgFloat = imgFloat / 255.0;  % contract images may already be [0,1]; be defensive like the Python side
    end
    normalized = (imgFloat - meanVec) ./ stdVec;

    % HWC -> NCHW (1, C, H, W)
    chw = permute(normalized, [3, 1, 2]);  % C,H,W
    nchw = reshape(chw, [1, size(chw)]);

    outputNames = {'logits', 'features'};
    outputs = netra.onnxio.runInference(contract.model_path_, 'input', nchw, outputNames);
    logits = squeeze(outputs{1});
    logits = logits(:)';
    features = squeeze(outputs{2});  % C x H x W

    outputFormat = lower(string(contract.output_format));
    probSum = sum(logits);
    if outputFormat == "softmax" && abs(probSum - 1.0) < 1e-2 && all(logits >= 0)
        probabilities = logits / probSum;
    else
        probabilities = softmaxRow(logits);
    end

    classLabels = contract.class_labels;
    if numel(probabilities) ~= numel(classLabels)
        error('netra:grading:classMismatch', ...
            'Grading model output dimension (%d) does not match contract class_labels length (%d).', ...
            numel(probabilities), numel(classLabels));
    end

    [~, argmaxIdx] = max(probabilities);
    severityClass = argmaxIdx - 1;  % 0-indexed ICDR grade

    result = struct('severity_class', severityClass, 'probabilities', probabilities, ...
        'logits', logits, 'features', features, 'model_name', contract.model_name, ...
        'model_version', contract.model_version, 'contract', contract);
end

function p = softmaxRow(z)
    z = z - max(z);
    e = exp(z);
    p = e / sum(e);
end
