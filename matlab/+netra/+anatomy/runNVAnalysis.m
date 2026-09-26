function result = runNVAnalysis(~, modelsRootDir)
%RUNNVANALYSIS Neovascularization analysis interface -- honestly unavailable.
%
%   result = netra.anatomy.runNVAnalysis(preprocessedImage, modelsRootDir)
%
% The PS includes neovascularization detection, scoped by the project's own
% Final Model Stack to FGADR-sourced data only. FGADR was never downloaded
% for this project (explicitly out of scope) and no NV model was trained.
% This function does NOT fabricate an NV mask or a plausible-looking score.
% If a real, contract-conformant NV model is ever added at
% models/nv/metadata.json, this function should be extended to load and run
% it (mirroring the pattern of every other stage) -- until then it returns
% an honest "unavailable" status.

    nvModelDir = fullfile(modelsRootDir, 'nv');
    metaPath = fullfile(nvModelDir, 'metadata.json');

    if isfile(metaPath)
        error('netra:anatomy:nvNotImplemented', ...
            ['A models/nv/metadata.json was found, but netra.anatomy.runNVAnalysis has no ' ...
             'validated inference path implemented for it yet. Do not silently skip this -- ' ...
             'extend this function before claiming NV analysis is operational.']);
    end

    result = struct('status', 'unavailable', ...
        'reason', 'No validated NV model artifact is installed (FGADR-scoped per project spec; FGADR not downloaded).', ...
        'nv_mask', [], 'nv_score', []);
end
