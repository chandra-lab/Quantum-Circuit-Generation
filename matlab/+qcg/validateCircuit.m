function result = validateCircuit(data, options)
%VALIDATECIRCUIT Simulate one exported circuit in MATLAB and compare with Qiskit.
%   result = qcg.validateCircuit(data) where data comes from
%   qcg.loadQiskitExport.
%
%   Exact check (primary): the circuit is built from the exported spec with
%   qcg.circuitFromSpec, simulated with simulate, and its probabilities
%   abs(Amplitudes).^2 are mapped to Qiskit order with qcg.matlabToQiskitLabel
%   and compared with the Qiskit Statevector probabilities. Passes when the
%   max absolute error is <= ExactTolerance. State fidelity
%   |<psi_qiskit|psi_matlab>|^2 is reported as a phase-insensitive check.
%
%   Sampled check (secondary): randsample draws Shots samples from the same
%   state. Labels are mapped to clbit order with qcg.matlabLabelToClbits and
%   tested with chi-square against the exact measured distribution and
%   against the Aer counts. Different random generators mean the counts never
%   match exactly; the tests ask whether the difference exceeds shot noise.
%   Set Shots to 0 to skip sampling.

arguments
    data (1,1) struct
    options.ExactTolerance (1,1) double {mustBePositive} = 1e-10
    options.Alpha (1,1) double {mustBePositive} = 1e-3
    options.Shots (1,1) double = NaN
end

tolerance = options.ExactTolerance;
result = struct();
result.circuitId = data.circuitId;
result.circuitName = data.circuitName;
result.source = data.source;
result.numQubits = data.numQubits;
result.numClbits = data.numClbits;
result.gateSequence = data.gateSequence;

c = qcg.circuitFromSpec(data.spec);
state = simulate(c);
[matlabLabels, matlabProbabilities] = qcg.stateProbabilities(state);
qiskitLabels = qcg.matlabToQiskitLabel(matlabLabels);

exact = qcg.compareDistributions(data.exactStates, data.exactProbabilities, qiskitLabels, matlabProbabilities);
exact.matlabLabels = qcg.qiskitToMatlabLabel(exact.states);
exact.tolerance = tolerance;
exact.sumMatlabProbabilities = sum(matlabProbabilities);
exact.passed = exact.maxAbsError <= tolerance;
result.exact = exact;

[found, loc] = ismember(qiskitLabels, data.exactStates);
qiskitAmplitudes = zeros(numel(qiskitLabels), 1);
qiskitAmplitudes(found) = data.exactAmplitudes(loc(found));
result.stateFidelity = abs(sum(conj(qiskitAmplitudes) .* state.Amplitudes(:)))^2;
result.fidelityPassed = abs(1 - result.stateFidelity) <= tolerance;

result.querystatesMaxAbsError = NaN;
try
    [qsLabels, qsProbabilities] = querystates(state, Threshold="none");
    check = qcg.compareDistributions(matlabLabels, matlabProbabilities, qsLabels, qsProbabilities);
    result.querystatesMaxAbsError = check.maxAbsError;
catch err
    warning("qcg:querystates", "querystates cross-check skipped for %s: %s", data.circuitId, err.message);
end

result.handBuiltMaxAbsError = NaN;
result.handBuiltPassed = true;
reference = qcg.referenceCircuit(data.circuitId);
if ~isempty(reference)
    [refLabels, refProbabilities] = qcg.stateProbabilities(simulate(reference));
    check = qcg.compareDistributions(matlabLabels, matlabProbabilities, refLabels, refProbabilities);
    result.handBuiltMaxAbsError = check.maxAbsError;
    result.handBuiltPassed = check.maxAbsError <= tolerance;
end

shots = options.Shots;
if isnan(shots)
    shots = data.shots;
end
sampled = struct("skipped", shots <= 0, "shots", shots);
sampled.aerStates = data.sampledStates;
sampled.aerCounts = data.sampledCounts;
sampled.aerShots = data.shots;
if shots > 0
    [sampleLabels, sampleCounts] = qcg.sampleState(state, shots);
    clbitLabels = qcg.matlabLabelToClbits(sampleLabels, data.measurements, data.numClbits);
    [clbitLabels, sampleCounts] = qcg.accumulateLabels(clbitLabels, sampleCounts);
    sampled.states = clbitLabels;
    sampled.counts = sampleCounts;
    sampled.vsExact = qcg.compareDistributions(data.measuredStates, data.measuredProbabilities, ...
        clbitLabels, sampleCounts / shots);
    sampled.vsAer = qcg.compareDistributions(data.sampledStates, data.sampledProbabilities, ...
        clbitLabels, sampleCounts / shots);
    sampled.goodnessOfFit = qcg.chiSquareGoodnessOfFit(clbitLabels, sampleCounts, ...
        data.measuredStates, data.measuredProbabilities, Alpha=options.Alpha);
    sampled.aerGoodnessOfFit = qcg.chiSquareGoodnessOfFit(data.sampledStates, data.sampledCounts, ...
        data.measuredStates, data.measuredProbabilities, Alpha=options.Alpha);
    sampled.homogeneity = qcg.chiSquareHomogeneity(clbitLabels, sampleCounts, ...
        data.sampledStates, data.sampledCounts, Alpha=options.Alpha);
    sampled.passed = sampled.goodnessOfFit.passed && sampled.homogeneity.passed;
else
    sampled.passed = true;
end
result.sampled = sampled;

result.exactPassed = exact.passed && result.fidelityPassed && result.handBuiltPassed;
result.passed = result.exactPassed && sampled.passed;
end
