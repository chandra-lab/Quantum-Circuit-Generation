function results = run_tests()
%RUN_TESTS Run the matlab.unittest suite in tests/.
%   BitOrderTest, CompareDistributionsTest, and LoadExportTest need only
%   base MATLAB. CircuitLoaderTest needs the MATLAB Support Package for
%   Quantum Computing and is reported as Incomplete without it.

root = fileparts(mfilename("fullpath"));
addpath(root);
results = runtests(fullfile(root, "tests"));
disp(table(results));
failed = [results.Failed];
if any(failed)
    error("qcg:testsFailed", "%d of %d MATLAB tests failed.", nnz(failed), numel(results));
end
end
