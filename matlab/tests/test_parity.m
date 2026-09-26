classdef test_parity < matlab.unittest.TestCase
%TEST_PARITY Regression test locking in the MATLAB/Python parity results
% measured and recorded in docs/matlab_parity_report.md. If this test ever
% fails, docs/matlab_parity_report.md must be re-measured and updated --
% never edited to match a new failure without re-running both pipelines.

    properties
        RepoRoot
    end

    methods (TestMethodSetup)
        function setup(testCase)
            here = fileparts(fileparts(mfilename('fullpath')));
            testCase.RepoRoot = fileparts(here);
            addpath(here);
        end
    end

    methods (Test)
        function testPredictedGradeMatchesPythonOnGoodSample(testCase)
            % Python reference (docs/matlab_parity_report.md): severity_class = 0
            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'));
            testCase.verifyEqual(r.grading.severity_class, 0);
            testCase.verifyEqual(r.decision.referable_decision, 'NO REFER');
        end

        function testPredictedGradeMatchesPythonOnGrade4Sample(testCase)
            % Python reference: severity_class = 4, referable_decision = REFER
            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'aptos_grade4_875a2fc5fe23.png'));
            testCase.verifyFalse(r.stopped_at_quality, ...
                'Quality gate must pass this image (BORDERLINE) for the grading parity check to run.');
            testCase.verifyEqual(r.grading.severity_class, 4);
            testCase.verifyEqual(r.decision.referable_decision, 'REFER');
        end

        function testCalibrationTemperatureMatchesConfig(testCase)
            r = run_netradr_pipeline(fullfile(testCase.RepoRoot, 'data', 'demo', 'good_sample.jpg'));
            testCase.verifyEqual(r.calibration.temperature, 2.8, 'AbsTol', 1e-6);
            testCase.verifyTrue(r.calibration.fitted);
        end
    end
end
