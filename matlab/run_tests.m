%RUN_TESTS Run the full MATLAB test suite for NETRA-DR.
%   From a MATLAB session with any working directory:
%       run(fullfile('<repo>', 'matlab', 'run_tests.m'))
%   or, having cd'd into matlab/:
%       runtests('tests')

repoMatlabDir = fileparts(mfilename('fullpath'));
addpath(repoMatlabDir);
results = runtests(fullfile(repoMatlabDir, 'tests'));
table(results)
fprintf('\nTOTAL: %d passed, %d failed, %d incomplete\n', ...
    sum([results.Passed]), sum([results.Failed]), sum([results.Incomplete]));
