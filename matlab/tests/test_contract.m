classdef test_contract < matlab.unittest.TestCase
%TEST_CONTRACT Real tests for netra.contract.loadModelContract against the
% actual models/ directories on disk (no mocked filesystem).

    properties
        RepoRoot
    end

    methods (TestMethodSetup)
        function setup(testCase)
            here = fileparts(fileparts(mfilename('fullpath')));  % tests/.. = matlab/
            testCase.RepoRoot = fileparts(here);                 % matlab/.. = repo root
        end
    end

    methods (Test)
        function testValidGradingContract(testCase)
            c = netra.contract.loadModelContract(fullfile(testCase.RepoRoot, 'models', 'grading'), 'classifier');
            testCase.verifyEqual(numel(c.class_labels), 5);
            testCase.verifyTrue(isfile(c.model_path_));
        end

        function testValidSegmentationContract(testCase)
            c = netra.contract.loadModelContract(fullfile(testCase.RepoRoot, 'models', 'vessel_seg'), 'segmentation');
            testCase.verifyTrue(isfield(c, 'mask_labels'));
            testCase.verifyTrue(isfile(c.model_path_));
        end

        function testValidMaDetectorContract(testCase)
            c = netra.contract.loadModelContract(fullfile(testCase.RepoRoot, 'models', 'ma_detector'), 'ma_detector');
            testCase.verifyTrue(isfield(c, 'candidate_extraction_method'));
        end

        function testMissingMetadataErrors(testCase)
            testCase.verifyError(@() netra.contract.loadModelContract(tempdir, 'classifier'), ...
                'netra:contract:missingMetadata');
        end

        function testUnsupportedTypeErrors(testCase)
            testCase.verifyError(@() netra.contract.loadModelContract(tempdir, 'not_a_type'), ...
                'netra:contract:unsupportedType');
        end

        function testMalformedMetadataErrors(testCase)
            tmpDir = fullfile(tempdir, ['netra_test_' char(java.util.UUID.randomUUID)]);
            mkdir(tmpDir);
            fid = fopen(fullfile(tmpDir, 'metadata.json'), 'w');
            fprintf(fid, '{not valid json');
            fclose(fid);
            testCase.verifyError(@() netra.contract.loadModelContract(tmpDir, 'classifier'), ...
                'netra:contract:invalidJson');
            rmdir(tmpDir, 's');
        end

        function testMissingFieldErrors(testCase)
            tmpDir = fullfile(tempdir, ['netra_test_' char(java.util.UUID.randomUUID)]);
            mkdir(tmpDir);
            fid = fopen(fullfile(tmpDir, 'metadata.json'), 'w');
            fprintf(fid, '{"model_name": "x"}');
            fclose(fid);
            testCase.verifyError(@() netra.contract.loadModelContract(tmpDir, 'classifier'), ...
                'netra:contract:missingField');
            rmdir(tmpDir, 's');
        end

        function testMissingArtifactErrors(testCase)
            tmpDir = fullfile(tempdir, ['netra_test_' char(java.util.UUID.randomUUID)]);
            mkdir(tmpDir);
            meta = struct('model_name', 'x', 'model_version', '1', 'input_size', [224 224], ...
                'channels', 3, 'normalization', struct('mean', [0 0 0], 'std', [1 1 1]), ...
                'model_file', 'does_not_exist.onnx', 'framework', 'onnx', 'training_dataset', 'x', ...
                'preprocessing', {{'x'}}, 'eval_metrics', struct(), 'class_labels', {{'0','1'}}, ...
                'output_format', 'softmax', 'threshold', 0.5);
            fid = fopen(fullfile(tmpDir, 'metadata.json'), 'w');
            fprintf(fid, '%s', jsonencode(meta));
            fclose(fid);
            testCase.verifyError(@() netra.contract.loadModelContract(tmpDir, 'classifier'), ...
                'netra:contract:missingArtifact');
            rmdir(tmpDir, 's');
        end
    end
end
