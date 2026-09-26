classdef test_quality < matlab.unittest.TestCase
%TEST_QUALITY Real tests for netra.quality.assessQuality against the actual
% demo images and models/quality/iqa_thresholds.json.

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
        function testGoodSampleIsGood(testCase)
            r = netra.quality.assessQuality(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'), ...
                fullfile(testCase.RepoRoot, 'models', 'quality'));
            testCase.verifyEqual(r.quality_label, 'GOOD');
            testCase.verifyGreaterThan(r.quality_score, 0.9);
        end

        function testRejectSampleIsReject(testCase)
            r = netra.quality.assessQuality(fullfile(testCase.RepoRoot, 'data', 'demo', 'reject_sample.jpg'), ...
                fullfile(testCase.RepoRoot, 'models', 'quality'));
            testCase.verifyEqual(r.quality_label, 'REJECT');
            testCase.verifyNotEmpty(r.reasons);
        end

        function testMeasuredValuesAreFinite(testCase)
            r = netra.quality.assessQuality(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'), ...
                fullfile(testCase.RepoRoot, 'models', 'quality'));
            fns = fieldnames(r.measured);
            for i = 1:numel(fns)
                testCase.verifyTrue(isfinite(r.measured.(fns{i})), ['Non-finite measured value: ' fns{i}]);
            end
        end

        function testMissingImageErrors(testCase)
            testCase.verifyError(@() netra.quality.assessQuality(fullfile(tempdir, 'does_not_exist.jpg'), ...
                fullfile(testCase.RepoRoot, 'models', 'quality')), 'netra:quality:missingImage');
        end

        function testCorruptedImageErrors(testCase)
            % A corrupted/unreadable "image" file must raise an error, not
            % silently produce a fabricated quality result. The specific
            % MATLAB error identifier for an unreadable file depends on the
            % file-format sniffing path, so this checks that SOME error is
            % thrown, not fabricated output -- the stronger guarantee
            % (never fabricate) rather than a brittle identifier match.
            tmpFile = fullfile(tempdir, ['netra_corrupt_' char(java.util.UUID.randomUUID) '.jpg']);
            fid = fopen(tmpFile, 'w');
            fwrite(fid, uint8(randi(255, 1, 200)));
            fclose(fid);
            testCase.verifyError(@() netra.quality.assessQuality(tmpFile, ...
                fullfile(testCase.RepoRoot, 'models', 'quality')), ?MException);
            delete(tmpFile);
        end
    end
end
