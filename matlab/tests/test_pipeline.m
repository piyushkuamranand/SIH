classdef test_pipeline < matlab.unittest.TestCase
%TEST_PIPELINE End-to-end and error-handling tests for run_netradr_pipeline.
% Uses the actual real demo images and real models -- no mocking.

    properties
        RepoRoot
    end

    methods (TestMethodSetup)
        function setup(testCase)
            here = fileparts(fileparts(mfilename('fullpath')));
            testCase.RepoRoot = fileparts(here);
            addpath(here);  % so run_netradr_pipeline.m (at matlab/) is reachable
        end
    end

    methods (Test)
        function testGoodImageRunsFullPipeline(testCase)
            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'));
            testCase.verifyFalse(r.stopped_at_quality);
            testCase.verifyEqual(r.quality.quality_label, 'GOOD');
            testCase.verifyTrue(isfield(r, 'grading'));
            testCase.verifyTrue(isfield(r, 'calibration'));
            testCase.verifyTrue(isfield(r, 'decision'));
            testCase.verifyTrue(isfield(r, 'explainability'));
            testCase.verifyTrue(isfield(r, 'vessels'));
            testCase.verifyTrue(isfield(r, 'lesions'));
            testCase.verifyTrue(isfield(r, 'ma'));
            testCase.verifyEmpty(r.errors);
            testCase.verifyGreaterThan(r.timing.total, 0);
        end

        function testRejectImageHaltsAtQuality(testCase)
            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'reject_sample.jpg'));
            testCase.verifyTrue(r.stopped_at_quality);
            testCase.verifyEqual(r.quality.quality_label, 'REJECT');
            testCase.verifyFalse(isfield(r, 'grading'));   % never fabricated downstream
            testCase.verifyFalse(isfield(r, 'vessels'));
        end

        function testMissingImageErrors(testCase)
            testCase.verifyError(@() run_netradr_pipeline(fullfile(tempdir, 'nope.jpg')), ...
                'netra:pipeline:missingImage');
        end

        function testMissingVesselModelIsRecoverable(testCase)
            % Temporarily point at a models root with no vessel_seg -- the
            % pipeline must continue (grading etc. still run) and record a
            % recoverable, non-fabricated error for that one stage.
            tmpModelsRoot = fullfile(tempdir, ['netra_models_' char(java.util.UUID.randomUUID)]);
            copyfile(fullfile(testCase.RepoRoot, 'models'), tmpModelsRoot);
            rmdir(fullfile(tmpModelsRoot, 'vessel_seg'), 's');

            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'), ...
                'ModelsRoot', tmpModelsRoot, 'ConfigsRoot', fullfile(testCase.RepoRoot, 'configs'));

            testCase.verifyFalse(isfield(r, 'vessels'));
            testCase.verifyTrue(isfield(r, 'grading'));  % other stages still ran
            foundVesselError = false;
            for i = 1:numel(r.errors)
                if strcmp(r.errors{i}.stage, 'vessels')
                    foundVesselError = true;
                    testCase.verifyTrue(r.errors{i}.recoverable);
                end
            end
            testCase.verifyTrue(foundVesselError);

            rmdir(tmpModelsRoot, 's');
        end

        function testCorruptedGradingArtifactIsRecordedNotFabricated(testCase)
            tmpModelsRoot = fullfile(tempdir, ['netra_models_' char(java.util.UUID.randomUUID)]);
            copyfile(fullfile(testCase.RepoRoot, 'models'), tmpModelsRoot);
            fid = fopen(fullfile(tmpModelsRoot, 'grading', 'grading_model.onnx'), 'w');
            fprintf(fid, 'NOT A VALID ONNX FILE');
            fclose(fid);

            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'), ...
                'ModelsRoot', tmpModelsRoot, 'ConfigsRoot', fullfile(testCase.RepoRoot, 'configs'));

            testCase.verifyFalse(isfield(r, 'grading'));
            testCase.verifyFalse(isfield(r, 'explainability'));
            foundGradingError = false;
            for i = 1:numel(r.errors)
                if strcmp(r.errors{i}.stage, 'grading')
                    foundGradingError = true;
                end
            end
            testCase.verifyTrue(foundGradingError);

            rmdir(tmpModelsRoot, 's');
        end
    end
end
