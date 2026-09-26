function result = computeModelAttention(features, severityClass, modelDir, contract, sourceImage)
%COMPUTEMODELATTENTION Exact class activation mapping -- mirrors pipeline/explain.py's real CAM path.
%
%   result = netra.explain.computeModelAttention(features, severityClass, modelDir, contract, sourceImage)
%
% This is the EXACT (Zhou et al. 2016) class activation map, not an
% approximation and not native MATLAB gradCAM() -- gradCAM() requires a
% dlnetwork object, which requires importNetworkFromONNX, which is not
% available in this environment (no ONNX Model Format Converter support
% package installed -- verified). Because the grading model's head is
% GAP -> single FC layer (see docs/model_cards/grading.md), the exact CAM
% for the predicted class needs no gradient/backward pass at all:
%
%   CAM_c(x,y) = ReLU( sum_k  w[c,k] * feature_map[k,x,y] )
%
% where feature_map is the last conv block's output (already returned by
% netra.grading.runGrading) and w[c,:] is the FC layer's weight row for
% class c, read from models/grading/gradcam_fc_weights.npy (exported once
% at training time, exactly the array pipeline/explain.py uses on the
% Python side). This is mathematically identical to the Python
% implementation's "cam_fc_weighted" mode -- not a fallback, not a
% synthetic heatmap.
%
% UI terminology: "model attention" only -- never "clinical proof".

    fcWeightsFile = getFieldOr(contract, 'gradcam_fc_weights_file', '');
    if isempty(fcWeightsFile)
        error('netra:explain:noWeightsFile', ...
            'Contract does not declare gradcam_fc_weights_file -- model attention cannot be computed exactly.');
    end
    fcWeightsPath = fullfile(modelDir, fcWeightsFile);
    if ~isfile(fcWeightsPath)
        error('netra:explain:missingWeights', 'gradcam_fc_weights file not found: %s', fcWeightsPath);
    end

    fcWeights = netra.utils.readNPY(fcWeightsPath);  % (num_classes, C)
    numClasses = size(fcWeights, 1);
    if severityClass < 0 || severityClass > numClasses - 1
        error('netra:explain:invalidClass', 'severityClass %d out of range [0, %d].', severityClass, numClasses - 1);
    end

    classWeights = fcWeights(severityClass + 1, :);  % 1 x C
    if numel(classWeights) ~= size(features, 1)
        error('netra:explain:channelMismatch', ...
            'gradcam_fc_weights channel count (%d) does not match feature map channels (%d).', ...
            numel(classWeights), size(features, 1));
    end

    % features: C x H x W
    C = size(features, 1);
    cam = zeros(size(features, 2), size(features, 3));
    for k = 1:C
        cam = cam + classWeights(k) * squeeze(features(k, :, :));
    end
    cam = max(cam, 0);  % ReLU

    camMax = max(cam(:));
    if camMax > 0
        camNorm = cam / camMax;
    else
        camNorm = cam;
    end

    overlay = renderHeatmapOverlay(sourceImage, camNorm);

    result = struct('heatmap_raw', camNorm, 'heatmap_overlay', overlay, ...
        'label', 'model attention', 'severity_class', severityClass, ...
        'cam_mode', 'cam_fc_weighted_matlab', 'is_class_specific', true, ...
        'method_note', ['Exact class activation map (Zhou et al. 2016): FC-layer weights times last-conv ' ...
            'feature map, computed natively in MATLAB. Not MATLAB gradCAM() (that needs a dlnetwork, ' ...
            'unavailable without the ONNX converter package) and not a synthetic/fabricated heatmap.']);
end

function v = getFieldOr(s, name, default)
    if isstruct(s) && isfield(s, name)
        v = s.(name);
    else
        v = default;
    end
end

function overlay = renderHeatmapOverlay(sourceImage, camNorm)
    if max(sourceImage(:)) <= 1.5
        base = uint8(sourceImage * 255);
    else
        base = uint8(sourceImage);
    end
    [h, w, ~] = size(base);
    camResized = imresize(camNorm, [h, w], 'bilinear');
    camResized = max(0, min(1, camResized));
    cmap = jet(256);
    idx = max(1, min(256, round(camResized * 255) + 1));
    heat = ind2rgb(idx, cmap);
    heatUint8 = uint8(heat * 255);
    alpha = 0.5;
    overlay = uint8((1 - alpha) * double(base) + alpha * double(heatUint8));
end
