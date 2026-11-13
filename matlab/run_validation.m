function summary = run_validation(options)
%RUN_VALIDATION Validate the Qiskit reference circuits in MATLAB.
%   run_validation() loads every export in data/qiskit_results, builds each
%   circuit with the MATLAB Support Package for Quantum Computing, simulates
%   it, compares the probabilities with Qiskit, and writes CSV/JSON/text
%   reports to results/ and PNG plots to results/plots/.
%
%   summary = run_validation(Name=Value) options:
%     DataDir         folder with the exported JSON (default data/qiskit_results)
%     ResultsDir      output folder (default results)
%     Circuits        circuit ids to run, e.g. ["bell" "ghz"] (default all)
%     ExactTolerance  max |p_matlab - p_qiskit| for the exact check (1e-10)
%     Alpha           significance level for the sampled chi-square tests (1e-3)
%     Shots           randsample shots; NaN uses the Aer shot count, 0 skips (NaN)
%     Seed            rng seed for randsample (2026)
%     MakePlots       write PNG plots (true)
%
%   Example:
%     cd matlab
%     summary = run_validation();
%     summary = run_validation(Circuits=["bell" "ghz"], Shots=10000);
%
%   See README.md in this folder for prerequisites and methodology.

arguments
    options.DataDir (1,1) string = fullfile(fileparts(mfilename("fullpath")), "data", "qiskit_results")
    options.ResultsDir (1,1) string = fullfile(fileparts(mfilename("fullpath")), "results")
    options.Circuits string = strings(0, 1)
    options.ExactTolerance (1,1) double {mustBePositive} = 1e-10
    options.Alpha (1,1) double {mustBePositive} = 1e-3
    options.Shots (1,1) double = NaN
    options.Seed (1,1) double {mustBeInteger, mustBeNonnegative} = 2026
    options.MakePlots (1,1) logical = true
end

addpath(fileparts(mfilename("fullpath")));

if isempty(which("quantumCircuit"))
    error("qcg:missingSupportPackage", ...
        "quantumCircuit was not found. Install the MATLAB Support Package for Quantum Computing " + ...
        "(Home > Add-Ons > Get Add-Ons). See matlab/README.md.");
end
if ~isfolder(options.DataDir)
    error("qcg:missingData", "Export folder %s not found. Run the Qiskit export first (see README.md).", ...
        options.DataDir);
end

files = dir(fullfile(options.DataDir, "*.json"));
files = files(~strcmp({files.name}, "manifest.json"));
if isempty(files)
    error("qcg:missingData", "No exported circuits in %s.", options.DataDir);
end

manifest = struct("versions", struct("qiskit", "unknown", "qiskit_aer", "unknown"));
manifestFile = fullfile(options.DataDir, "manifest.json");
if isfile(manifestFile)
    manifest = jsondecode(fileread(manifestFile));
end

rng(options.Seed, "twister");
plotDir = fullfile(options.ResultsDir, "plots");
results = {};
for k = 1:numel(files)
    data = qcg.loadQiskitExport(fullfile(files(k).folder, files(k).name));
    if ~isempty(options.Circuits) && ~any(options.Circuits == data.circuitId)
        continue
    end
    fprintf("Validating %-16s ", data.circuitId);
    result = qcg.validateCircuit(data, ExactTolerance=options.ExactTolerance, ...
        Alpha=options.Alpha, Shots=options.Shots);
    if options.MakePlots
        result.plots = qcg.plotComparison(result, data, plotDir);
    end
    fprintf("exact %s (max |diff| %.3g)  sampled %s\n", passFail(result.exactPassed), ...
        result.exact.maxAbsError, passFail(result.sampled.passed));
    results{end + 1} = result; %#ok<AGROW>
end
if isempty(results)
    error("qcg:noCircuits", "None of the requested circuits were found in %s.", options.DataDir);
end

meta = struct();
meta.matlabVersion = string(version);
meta.supportPackageVersion = supportPackageVersion();
meta.qiskitVersion = string(manifest.versions.qiskit);
meta.qiskitAerVersion = string(manifest.versions.qiskit_aer);
meta.dataDir = options.DataDir;
meta.exactTolerance = options.ExactTolerance;
meta.alpha = options.Alpha;
meta.seed = options.Seed;
meta.bitOrdering = "MATLAB labels (qubit 1 first) reversed to Qiskit order (qubit 0 rightmost)";

reportFiles = qcg.writeReport(results, options.ResultsDir, meta);
fprintf("\n%s", fileread(fullfile(options.ResultsDir, "summary.txt")));
fprintf("Reports: %s\n", options.ResultsDir);

summary = struct();
summary.results = results;
summary.meta = meta;
summary.reportFiles = reportFiles;
summary.allExactPassed = all(cellfun(@(r) r.exactPassed, results));
summary.allSampledPassed = all(cellfun(@(r) r.sampled.passed, results));
end

function s = passFail(ok)
if ok
    s = "PASS";
else
    s = "FAIL";
end
end

function v = supportPackageVersion()
v = "unknown";
try
    installed = matlabshared.supportpkg.getInstalled;
    names = string({installed.Name});
    match = find(contains(names, "Quantum", IgnoreCase=true), 1);
    if ~isempty(match) && isfield(installed, "InstalledVersion")
        v = string(installed(match).InstalledVersion);
    elseif ~isempty(match) && isfield(installed, "Version")
        v = string(installed(match).Version);
    end
catch
end
end
