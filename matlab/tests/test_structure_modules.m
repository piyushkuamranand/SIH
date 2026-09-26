classdef test_structure_modules < matlab.unittest.TestCase
%TEST_STRUCTURE_MODULES Real tests for vessels, lesions, MA, and model
% attention against the actual frozen ONNX artifacts.

    properties
        RepoRoot
        PreImg
    end

    methods (TestMethodSetup)
        function setup(testCase)
            here = fileparts(fileparts(mfilename('fullpath')));
            testCase.RepoRoot = fileparts(here);
            imgPath = fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg');
            cfgPath = fullfile(testCase.RepoRoot, 'configs', 'preprocessing.json');
            testCase.PreImg = netra.preprocess.preprocessImage(imgPath, cfgPath);
        end
    end

    methods (Test)
        function testVesselMaskIsValidBinary(testCase)
            r = netra.vessels.runVesselSegmentation(testCase.PreImg, fullfile(testCase.RepoRoot, 'models', 'vessel_seg'));
            testCase.verifyEqual(size(r.vessel_mask), [size(testCase.PreImg,1), size(testCase.PreImg,2)]);
            uniqueVals = unique(r.vessel_mask(:));
            testCase.verifyTrue(all(ismember(uniqueVals, [0, 255])));
        end

        function testLesionMasksHaveCorrectChannelSemantics(testCase)
            r = netra.lesions.runLesionSegmentation(testCase.PreImg, fullfile(testCase.RepoRoot, 'models', 'lesion_seg'));
            testCase.verifyClass(r.he_presence, 'logical');
            testCase.verifyGreaterThanOrEqual(r.ex_area, 0);
            testCase.verifyLessThanOrEqual(r.ex_area, 1);
            % No invented lesion subtypes -- struct must not have flame/dot-blot/deep fields.
            testCase.verifyFalse(isfield(r, 'flame_hemorrhage'));
            testCase.verifyFalse(isfield(r, 'dot_blot_hemorrhage'));
        end

        function testMaCountIsNonNegativeInteger(testCase)
            r = netra.ma.runMADetection(testCase.PreImg, fullfile(testCase.RepoRoot, 'models', 'ma_detector'));
            testCase.verifyGreaterThanOrEqual(r.ma_count, 0);
            testCase.verifyEqual(r.ma_count, round(r.ma_count));
        end

        function testModelAttentionIsClassSpecificAndFinite(testCase)
            g = netra.grading.runGrading(testCase.PreImg, fullfile(testCase.RepoRoot, 'models', 'grading'));
            e = netra.explain.computeModelAttention(g.features, g.severity_class, ...
                fullfile(testCase.RepoRoot, 'models', 'grading'), g.contract, testCase.PreImg);
            testCase.verifyEqual(e.label, 'model attention');
            testCase.verifyTrue(e.is_class_specific);
            testCase.verifyTrue(all(isfinite(e.heatmap_raw(:))));
            testCase.verifyGreaterThanOrEqual(min(e.heatmap_raw(:)), 0);  % ReLU'd
            testCase.verifyFalse(contains(lower(e.label), 'proof'));
            testCase.verifyFalse(contains(lower(e.label), 'clinical'));
        end

        function testNVReturnsHonestUnavailable(testCase)
            r = netra.anatomy.runNVAnalysis(testCase.PreImg, fullfile(testCase.RepoRoot, 'models'));
            testCase.verifyEqual(r.status, 'unavailable');
            testCase.verifyFalse(isempty(r.reason));
        end

        function testVesselMissingArtifactErrors(testCase)
            testCase.verifyError(@() netra.vessels.runVesselSegmentation(testCase.PreImg, tempdir), ...
                'netra:contract:missingMetadata');
        end
    end
end
