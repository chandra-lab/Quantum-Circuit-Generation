function c = circuitFromSpec(spec)
%CIRCUITFROMSPEC Build a quantumCircuit from an exported circuit spec.
%   c = qcg.circuitFromSpec(spec) maps each gate in spec.gates to the
%   matching MATLAB gate function. spec is the "spec" field of a Qiskit
%   export (or any JSON spec accepted by the backend validator).
%
%   Qiskit qubit q (0-based) becomes MATLAB qubit q+1. Measurements are not
%   added: simulate returns the full state, and the caller applies the
%   measurement map (see qcg.matlabLabelToClbits).
%
%   Requires the MATLAB Support Package for Quantum Computing.

arguments
    spec (1,1) struct
end

numQubits = double(spec.num_qubits);
if numQubits < 1 || numQubits ~= fix(numQubits)
    error("qcg:badSpec", "num_qubits must be a positive integer.");
end

gateSpecs = qcg.asCell(spec.gates);
gates = cell(numel(gateSpecs), 1);
for k = 1:numel(gateSpecs)
    gates{k} = qcg.gateFromSpec(gateSpecs{k}, numQubits);
end

name = qcg.circuitName(spec.circuit_name);
if isempty(gates)
    c = quantumCircuit(numQubits, Name=name);
else
    c = quantumCircuit(vertcat(gates{:}), numQubits, Name=name);
end
end
