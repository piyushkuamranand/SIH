classdef test_grading < matlab.unittest.TestCase
%TEST_GRADING Real tests for netra.grading.runGrading against the actual
% frozen ResNet-50 ONNX model.

    properties
        RepoRoot
    end

    methods (TestMethodSetup)
        function setup(testCase)
            here = fileparts(fileparts(mfilename('fullpath')));
            testCase.RepoRoot = fileparts(here);
        end
    end

    methods (Test)
        function testGradingOnRealImageProducesValidOutput(testCase)
            imgPath = fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg');
            cfgPath = fullfile(testCase.RepoRoot, 'configs', 'preprocessing.json');
            pre = netra.preprocess.preprocessImage(imgPath, cfgPath);
            g = netra.grading.runGrading(pre, fullfile(testCase.RepoRoot, 'models', 'grading'));

            testCase.verifyGreaterThanOrEqual(g.severity_class, 0);
            testCase.verifyLessThanOrEqual(g.severity_class, 4);
            testCase.verifyEqual(numel(g.probabilities), 5);
            testCase.verifyEqual(sum(g.probabilities), 1.0, 'AbsTol', 1e-4);
            testCase.verifyTrue(all(isfinite(g.probabilities)));
            testCase.verifyFalse(isempty(g.model_name));
            % ResNet-50 is the required final architecture -- never ResNet-18.
            testCase.verifySubstring(lower(g.model_name), 'resnet50');
        end

        function testGradingMissingArtifactErrors(testCase)
            testCase.verifyError(@() netra.grading.runGrading(zeros(512,512,3,'single'), tempdir), ...
                'netra:contract:missingMetadata');
        end

        function testFeatureMapShapeMatchesExpectedChannels(testCase)
            imgPath = fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg');
            cfgPath = fullfile(testCase.RepoRoot, 'configs', 'preprocessing.json');
            pre = netra.preprocess.preprocessImage(imgPath, cfgPath);
            g = netra.grading.runGrading(pre, fullfile(testCase.RepoRoot, 'models', 'grading'));
            % ResNet-50's final conv block has 2048 channels.
            testCase.verifyEqual(size(g.features, 1), 2048);
        end
    end
end
