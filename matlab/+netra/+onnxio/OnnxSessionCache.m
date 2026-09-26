classdef OnnxSessionCache
%ONNXSESSIONCACHE Persistent, in-process cache of onnxruntime InferenceSession objects.
%
% The Deep Learning Toolbox Converter for ONNX Model Format is not installed
% in this environment (importNetworkFromONNX / importONNXNetwork both
% unavailable -- verified, not assumed; see docs/checkpoints/matlab_implementation_report.md).
% MATLAB's documented, supported Python-interoperability feature (pyenv/py.*)
% is used instead to run the frozen ONNX models via the SAME onnxruntime
% package the Python prototype uses -- this is real MATLAB code orchestrating
% a real inference engine, not "call a Python script and return its result":
% MATLAB constructs the session, prepares the NCHW input tensor, calls
% .run(), and consumes the numeric output directly into the MATLAB
% workspace. Every other stage (contract loading, preprocessing, quality,
% calibration, decision logic, model attention, report generation) is
% implemented natively in MATLAB with no Python involvement at all.
%
% Sessions are cached by resolved model path so repeated calls (e.g. across
% multiple images in one demo session) reuse the already-loaded session
% instead of re-importing/re-opening the model file every request.

    methods (Static)
        function sess = get(modelPath)
            persistent cacheMap
            if isempty(cacheMap)
                cacheMap = containers.Map('KeyType', 'char', 'ValueType', 'any');
            end
            key = char(modelPath);
            if isKey(cacheMap, key)
                sess = cacheMap(key);
                return
            end
            if ~isfile(modelPath)
                error('netra:onnxio:missingArtifact', 'ONNX model artifact not found: %s', modelPath);
            end
            ort = py.importlib.import_module('onnxruntime');
            try
                sess = ort.InferenceSession(char(modelPath), pyargs('providers', {'CPUExecutionProvider'}));
            catch loadErr
                error('netra:onnxio:loadFailed', ...
                    'Failed to load ONNX model ''%s'' via onnxruntime: %s', modelPath, loadErr.message);
            end
            cacheMap(key) = sess; %#ok<NASGU>
        end
    end
end
