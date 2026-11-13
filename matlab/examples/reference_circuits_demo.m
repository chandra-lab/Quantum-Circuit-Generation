%REFERENCE_CIRCUITS_DEMO Build, simulate, and sample the reference circuits in MATLAB.
%   Uses the hand-built circuits in qcg.referenceCircuit (hGate, cxGate,
%   xGate), simulate, and randsample. Each table shows the MATLAB basis label
%   (qubit 1 first) next to the Qiskit bitstring for the same state.
%   Requires the MATLAB Support Package for Quantum Computing.

addpath(fileparts(fileparts(mfilename("fullpath"))));
rng(2026, "twister");

for id = ["bell", "superposition", "ghz", "bit_flip"]
    c = qcg.referenceCircuit(id);
    s = simulate(c);
    [labels, p] = qcg.stateProbabilities(s);
    m = randsample(s, 1000);

    fprintf("\n== %s ==\n", id);
    disp(formula(s));
    disp(table(labels, qcg.matlabToQiskitLabel(labels), p, ...
        VariableNames=["matlab_label", "qiskit_bitstring", "probability"]));
    disp(table(m.MeasuredStates, qcg.matlabToQiskitLabel(m.MeasuredStates), m.Counts, m.Probabilities, ...
        VariableNames=["matlab_label", "qiskit_bitstring", "count", "probability"]));
end
