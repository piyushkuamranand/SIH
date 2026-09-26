classdef test_calibration < matlab.unittest.TestCase
%TEST_CALIBRATION Real tests for netra.calibration.applyCalibration, including
% against the actual fitted configs/calibration.json (T=2.80, fitted=true).

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
        function testNoOpAtTemperatureOne(testCase)
            probs = [0.1, 0.6, 0.2, 0.05, 0.05];
            tmpCfg = writeTempCalibConfig(1.0, false);
            r = netra.calibration.applyCalibration(probs, tmpCfg);
            testCase.verifyEqual(r.calibrated_probabilities, probs, 'AbsTol', 1e-6);
            testCase.verifyFalse(r.fitted);
            delete(tmpCfg);
        end

        function testActualFittedConfigIsApplied(testCase)
            cfgPath = fullfile(testCase.RepoRoot, 'configs', 'calibration.json');
            probs = [0.001, 0.0002, 0.003, 0.01, 0.986];  % dominated by class 5
            r = netra.calibration.applyCalibration(probs, cfgPath);
            testCase.verifyTrue(r.fitted);
            testCase.verifyEqual(r.temperature, 2.8, 'AbsTol', 1e-6);
            % Temperature > 1 softens the distribution -- top prob should decrease.
            testCase.verifyLessThan(r.confidence, max(probs) / sum(probs));
            testCase.verifyEqual(sum(r.calibrated_probabilities), 1.0, 'AbsTol', 1e-6);
        end

        function testInvalidTemperatureErrors(testCase)
            tmpCfg = writeTempCalibConfig(-1.0, true);
            testCase.verifyError(@() netra.calibration.applyCalibration([0.5, 0.5], tmpCfg), ...
                'netra:calibration:invalidTemperature');
            delete(tmpCfg);
        end

        function testNegativeProbabilityErrors(testCase)
            testCase.verifyError(@() netra.calibration.applyCalibration([-0.1, 1.1], tempdir), ...
                'netra:calibration:invalidInput');
        end
    end
end

function p = writeTempCalibConfig(temperature, fitted)
    p = fullfile(tempdir, ['netra_calib_' char(java.util.UUID.randomUUID) '.json']);
    s = struct('temperature', temperature, 'fitted', fitted, 'method', 'temperature_scaling', 'dataset', 'test');
    fid = fopen(p, 'w');
    fprintf(fid, '%s', jsonencode(s));
    fclose(fid);
end
