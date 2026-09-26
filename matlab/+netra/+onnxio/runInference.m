function outputs = runInference(modelPath, inputName, inputArray, outputNames)
%RUNINFERENCE Run one ONNX model via MATLAB's Python interoperability (onnxruntime).
%
%   outputs = netra.onnxio.runInference(modelPath, inputName, inputArray, outputNames)
%
% See netra.onnxio.OnnxSessionCache for why this path is used (no ONNX
% Model Format Converter support package installed in this MATLAB
% environment -- importNetworkFromONNX/importONNXNetwork both verified
% unavailable). Sessions are cached by resolved path so repeated calls
% reuse the loaded model.
%
% Inputs:
%   modelPath   - path to the .onnx file (char/string)
%   inputName   - the model's input tensor name (from contract, never hardcoded upstream)
%   inputArray  - MATLAB numeric array, already in the model's expected
%                 shape (e.g. NCHW for the image models). MATLAB's
%                 automatic py.numpy.array() conversion preserves both the
%                 shape and per-element indexing exactly (verified: a
%                 MATLAB array A(i,j,k) maps to numpy A[i-1,j-1,k-1]) --
%                 no manual permute/reshape is needed here.
%   outputNames - cellstr of requested output tensor names, in the order
%                 the caller wants them returned (from contract)
%
% Output:
%   outputs - cell array of MATLAB double arrays, one per requested output
%             name, in the same order as outputNames, with the original
%             tensor shape preserved.

    sess = netra.onnxio.OnnxSessionCache.get(modelPath);

    npInput = py.numpy.array(single(inputArray));
    feedDict = py.dict(pyargs(char(inputName), npInput));
    pyOutNames = py.list(cellstr(outputNames));

    try
        pyOutputs = sess.run(pyOutNames, feedDict);
    catch runErr
        error('netra:onnxio:inferenceFailed', ...
            'ONNX inference failed for model ''%s'': %s', modelPath, runErr.message);
    end

    n = length(pyOutNames);
    outputs = cell(1, n);
    for i = 1:n
        arr = double(pyOutputs{i});
        if ~all(isfinite(arr(:)))
            error('netra:onnxio:nonFiniteOutput', ...
                'Model ''%s'' output ''%s'' contains non-finite values (NaN/Inf).', ...
                modelPath, outputNames{i});
        end
        outputs{i} = arr;
    end
end
