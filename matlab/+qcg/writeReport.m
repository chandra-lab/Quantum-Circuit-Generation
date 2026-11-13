function files = writeReport(results, resultsDir, meta)
%WRITEREPORT Write the comparison report to resultsDir.
%   files = qcg.writeReport(results, resultsDir, meta)
%
%   results     cell array of structs from qcg.validateCircuit
%   meta        struct with run settings and versions (see run_validation)
%
%   Files written:
%     exact_comparison.csv    one row per circuit and basis state
%     sampled_comparison.csv  one row per circuit and measured clbit string
%     summary.csv             one row per circuit with every metric
%     summary.json            settings, versions, and per-circuit metrics
%     summary.txt             human-readable summary

if ~isfolder(resultsDir)
    mkdir(resultsDir);
end

exactRows = cell(numel(results), 1);
sampledRows = cell(numel(results), 1);
summaryRows = cell(numel(results), 1);
for k = 1:numel(results)
    r = results{k};
    e = r.exact;
    n = numel(e.states);
    exactRows{k} = table(repmat(r.circuitId, n, 1), e.states, e.matlabLabels, e.reference, e.candidate, ...
        e.absDiff, VariableNames=["circuit_id", "qiskit_bitstring", "matlab_label", ...
        "qiskit_probability", "matlab_probability", "abs_diff"]);

    s = r.sampled;
    if ~s.skipped
        states = unique([s.vsExact.states; s.vsAer.states]);
        m = numel(states);
        aerProbabilities = qcg.valuesFor(s.vsAer.states, s.vsAer.reference, states);
        matlabProbabilities = qcg.valuesFor(s.vsAer.states, s.vsAer.candidate, states);
        sampledRows{k} = table(repmat(r.circuitId, m, 1), states, ...
            qcg.valuesFor(s.vsExact.states, s.vsExact.reference, states), ...
            qcg.valuesFor(s.aerStates, s.aerCounts, states), aerProbabilities, ...
            qcg.valuesFor(s.states, s.counts, states), matlabProbabilities, ...
            abs(matlabProbabilities - aerProbabilities), ...
            VariableNames=["circuit_id", "clbit_bitstring", "qiskit_exact_probability", ...
            "aer_count", "aer_probability", "matlab_count", "matlab_probability", "abs_diff_vs_aer"]);
    end

    summaryRows{k} = struct2table(summaryRow(r), AsArray=true);
end

exactFile = fullfile(resultsDir, "exact_comparison.csv");
sampledFile = fullfile(resultsDir, "sampled_comparison.csv");
summaryCsv = fullfile(resultsDir, "summary.csv");
summaryJson = fullfile(resultsDir, "summary.json");
summaryTxt = fullfile(resultsDir, "summary.txt");

writetable(vertcat(exactRows{:}), exactFile);
sampledTable = vertcat(sampledRows{~cellfun(@isempty, sampledRows)});
if ~isempty(sampledTable)
    writetable(sampledTable, sampledFile);
end
summaryTable = vertcat(summaryRows{:});
writetable(summaryTable, summaryCsv);

report = struct();
report.meta = meta;
report.circuits = cellfun(@summaryRow, results, UniformOutput=false);
report.allExactPassed = all(summaryTable.exact_passed);
report.allSampledPassed = all(summaryTable.sampled_passed);
writeText(summaryJson, jsonencode(report, PrettyPrint=true));
writeText(summaryTxt, summaryText(summaryTable, meta));

files = [exactFile; sampledFile; summaryCsv; summaryJson; summaryTxt];
end

function row = summaryRow(r)
row = struct();
row.circuit_id = r.circuitId;
row.circuit_name = r.circuitName;
row.source = r.source;
row.num_qubits = r.numQubits;
row.gates = strjoin(r.gateSequence, " ");
row.exact_max_abs_error = r.exact.maxAbsError;
row.exact_total_variation = r.exact.totalVariation;
row.exact_hellinger = r.exact.hellinger;
row.exact_kl_divergence = r.exact.klDivergence;
row.state_fidelity = r.stateFidelity;
row.hand_built_max_abs_error = r.handBuiltMaxAbsError;
row.querystates_max_abs_error = r.querystatesMaxAbsError;
row.exact_tolerance = r.exact.tolerance;
row.exact_passed = r.exactPassed;
s = r.sampled;
row.matlab_shots = s.shots;
if s.skipped
    row.sampled_tvd_vs_aer = NaN;
    row.sampled_hellinger_vs_aer = NaN;
    row.sampled_tvd_vs_exact = NaN;
    row.sampled_gof_p_value = NaN;
    row.aer_gof_p_value = NaN;
    row.homogeneity_p_value = NaN;
else
    row.sampled_tvd_vs_aer = s.vsAer.totalVariation;
    row.sampled_hellinger_vs_aer = s.vsAer.hellinger;
    row.sampled_tvd_vs_exact = s.vsExact.totalVariation;
    row.sampled_gof_p_value = s.goodnessOfFit.pValue;
    row.aer_gof_p_value = s.aerGoodnessOfFit.pValue;
    row.homogeneity_p_value = s.homogeneity.pValue;
end
row.sampled_passed = s.passed;
row.passed = r.passed;
end

function text = summaryText(t, meta)
lines = strings(0, 1);
lines(end + 1) = "MATLAB vs Qiskit validation summary";
lines(end + 1) = "===================================";
lines(end + 1) = sprintf("MATLAB %s, Quantum Computing support package %s", meta.matlabVersion, meta.supportPackageVersion);
lines(end + 1) = sprintf("Qiskit %s, Qiskit Aer %s (from %s)", meta.qiskitVersion, meta.qiskitAerVersion, meta.dataDir);
lines(end + 1) = sprintf("Exact tolerance %.0e on max |p_matlab - p_qiskit|; sampled alpha %.0e; MATLAB rng seed %d", ...
    meta.exactTolerance, meta.alpha, meta.seed);
lines(end + 1) = "Bit order: MATLAB labels (qubit 1 first) are reversed to Qiskit order (qubit 0 last) before comparing.";
lines(end + 1) = "";
lines(end + 1) = sprintf("%-16s %-6s %-11s %-11s %-11s %-9s %-8s %-8s %-6s", "circuit", "exact", ...
    "max|diff|", "TVD", "Hellinger", "fidelity", "TVD/Aer", "p(homog)", "sampled");
for k = 1:height(t)
    lines(end + 1) = sprintf("%-16s %-6s %-11.3g %-11.3g %-11.3g %-9.6f %-8.4f %-8.3g %-6s", ...
        t.circuit_id(k), passFail(t.exact_passed(k)), t.exact_max_abs_error(k), ...
        t.exact_total_variation(k), t.exact_hellinger(k), t.state_fidelity(k), ...
        t.sampled_tvd_vs_aer(k), t.homogeneity_p_value(k), passFail(t.sampled_passed(k)));
end
lines(end + 1) = "";
lines(end + 1) = sprintf("Exact comparison: %s (%d of %d circuits within tolerance)", ...
    passFail(all(t.exact_passed)), nnz(t.exact_passed), height(t));
lines(end + 1) = sprintf("Sampled comparison: %s (%d of %d circuits pass chi-square at alpha %.0e)", ...
    passFail(all(t.sampled_passed)), nnz(t.sampled_passed), height(t), meta.alpha);
lines(end + 1) = "Sampled tests are statistical: at alpha 1e-3 an occasional failure can be chance. Rerun with another seed before treating it as a mismatch.";
text = strjoin(lines, newline) + newline;
end

function s = passFail(ok)
if ok
    s = "PASS";
else
    s = "FAIL";
end
end

function writeText(file, text)
fid = fopen(file, "w", "n", "UTF-8");
if fid < 0
    error("qcg:writeFailed", "Cannot write %s.", file);
end
closer = onCleanup(@() fclose(fid));
fprintf(fid, "%s", text);
end
