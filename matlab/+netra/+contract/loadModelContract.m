function contract = loadModelContract(modelDir, modelType)
%LOADMODELCONTRACT Load and validate a NETRA-DR model contract (metadata.json).
%
%   contract = netra.contract.loadModelContract(modelDir, modelType)
%
% Mirrors pipeline/contract.py exactly (same mandatory field set, same
% per-type extra fields) so the MATLAB and Python layers enforce the
% identical contract against the same metadata.json files. This function
% does NOT hardcode input size, normalization, class order, or thresholds
% anywhere else in the MATLAB codebase -- every consumer reads those values
% from the struct this function returns.
%
% Inputs:
%   modelDir  - path to a models/<stage> directory (char/string)
%   modelType - one of 'classifier', 'segmentation', 'ma_detector'
%
% Output:
%   contract  - struct decoded from metadata.json, validated for the
%               mandatory fields required by modelType. Also carries
%               contract.model_dir_ and contract.model_path_ (resolved,
%               verified-to-exist artifact path) for convenience.
%
% Raises (via MATLAB error(), with a clear identifier and message -- never
% silently continues with an invalid/missing contract):
%   netra:contract:missingMetadata   - metadata.json not found
%   netra:contract:invalidJson       - metadata.json is not valid JSON
%   netra:contract:missingField      - a mandatory field is absent
%   netra:contract:unsupportedType   - modelType not recognised
%   netra:contract:missingArtifact   - contract.model_file does not exist on disk

    coreFields = {'model_name','model_version','input_size','channels', ...
                  'normalization','model_file','framework','training_dataset', ...
                  'preprocessing','eval_metrics'};

    switch modelType
        case 'classifier'
            typeFields = {'class_labels','output_format','threshold'};
        case 'segmentation'
            typeFields = {'mask_labels','output_format','mask_resolution'};
        case 'ma_detector'
            typeFields = {'candidate_extraction_method','fp_reducer_model_file','output_format'};
        otherwise
            error('netra:contract:unsupportedType', ...
                'Unsupported model type ''%s''. Supported: classifier, segmentation, ma_detector.', modelType);
    end

    metadataPath = fullfile(modelDir, 'metadata.json');
    if ~isfile(metadataPath)
        error('netra:contract:missingMetadata', ...
            'Model contract metadata file not found at: %s', metadataPath);
    end

    try
        raw = fileread(metadataPath);
        contract = jsondecode(raw);
    catch decodeErr
        error('netra:contract:invalidJson', ...
            'Corrupted or invalid JSON in model contract at ''%s'': %s', metadataPath, decodeErr.message);
    end

    requiredFields = [coreFields, typeFields];
    missing = requiredFields(~isfield(contract, requiredFields));
    if ~isempty(missing)
        error('netra:contract:missingField', ...
            'Model contract at ''%s'' is missing required field(s) for type ''%s'': %s', ...
            metadataPath, modelType, strjoin(missing, ', '));
    end

    if ~isfield(contract, 'model_file') || isempty(contract.model_file)
        error('netra:contract:missingField', 'Model contract does not specify ''model_file''.');
    end

    modelFile = contract.model_file;
    if isAbsolutePath(modelFile)
        modelPath = modelFile;
    else
        modelPath = fullfile(modelDir, modelFile);
    end

    if ~isfile(modelPath)
        error('netra:contract:missingArtifact', ...
            'Model artifact not found: ''%s'' (expected from contract ''model_file'': ''%s'')', ...
            modelPath, modelFile);
    end

    contract.model_dir_ = char(modelDir);
    contract.model_path_ = char(modelPath);
end

function tf = isAbsolutePath(p)
    p = char(p);
    tf = startsWith(p, '/') || (numel(p) >= 2 && p(2) == ':');
end
