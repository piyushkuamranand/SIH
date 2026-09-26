function data = readNPY(filePath)
%READNPY Minimal native MATLAB reader for NumPy .npy files (no toolbox dependency).
%
%   data = netra.utils.readNPY(filePath)
%
% Used to load models/grading/gradcam_fc_weights.npy (the frozen grading
% model's final FC-layer weight matrix, exported once at training time --
% see training/train_grading.py) natively in MATLAB, without any Python
% dependency for this step. Supports the standard .npy format versions 1.0
% and 2.0, little-endian float32/float64, C-order or Fortran-order.
%
% This is a small, self-contained parser of the documented, stable .npy
% binary format (magic string + header dict + raw array data) -- not a
% general-purpose NumPy-compatibility layer.

    if ~isfile(filePath)
        error('netra:utils:missingFile', '.npy file not found: %s', filePath);
    end

    fid = fopen(filePath, 'r', 'ieee-le');
    if fid < 0
        error('netra:utils:openFailed', 'Could not open file: %s', filePath);
    end
    cleanupObj = onCleanup(@() fclose(fid));

    magic = fread(fid, 6, 'uint8=>char')';
    if ~strcmp(magic, char([147 78 85 77 80 89]))  % \x93NUMPY
        error('netra:utils:badMagic', 'Not a valid .npy file (bad magic bytes): %s', filePath);
    end

    majorVersion = fread(fid, 1, 'uint8');
    fread(fid, 1, 'uint8');  % minor version, unused

    if majorVersion == 1
        headerLen = fread(fid, 1, 'uint16');
    else
        headerLen = fread(fid, 1, 'uint32');
    end
    headerStr = fread(fid, headerLen, 'uint8=>char')';

    descrTok = regexp(headerStr, "'descr':\s*'([^']+)'", 'tokens', 'once');
    fortranTok = regexp(headerStr, "'fortran_order':\s*(True|False)", 'tokens', 'once');
    shapeTok = regexp(headerStr, "'shape':\s*\(([^)]*)\)", 'tokens', 'once');

    if isempty(descrTok) || isempty(shapeTok)
        error('netra:utils:badHeader', 'Could not parse .npy header: %s', headerStr);
    end

    descr = descrTok{1};
    fortranOrder = ~isempty(fortranTok) && strcmp(fortranTok{1}, 'True');
    shapeStr = strtrim(shapeTok{1});
    if isempty(shapeStr)
        shape = [1, 1];
    else
        shapeParts = str2double(strsplit(strrep(shapeStr, ',', ' ')));
        shapeParts = shapeParts(~isnan(shapeParts));
        if numel(shapeParts) == 1
            shape = [shapeParts, 1];
        else
            shape = shapeParts;
        end
    end

    switch descr
        case {'<f4', '=f4'}
            matlabClass = 'single';
        case {'<f8', '=f8'}
            matlabClass = 'double';
        case {'<i4', '=i4'}
            matlabClass = 'int32';
        case {'<i8', '=i8'}
            matlabClass = 'int64';
        otherwise
            error('netra:utils:unsupportedDtype', 'Unsupported .npy dtype: %s', descr);
    end

    raw = fread(fid, prod(shape), [matlabClass '=>' matlabClass]);

    if fortranOrder
        data = reshape(raw, shape);
    else
        data = reshape(raw, fliplr(shape));
        data = permute(data, numel(shape):-1:1);
    end
end
