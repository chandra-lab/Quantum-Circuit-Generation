function c = referenceCircuit(circuitId)
%REFERENCECIRCUIT Hand-built MATLAB versions of the backend reference circuits.
%   c = qcg.referenceCircuit(id) for id "bell", "superposition", "ghz", or
%   "bit_flip". These are written directly with hGate/cxGate/xGate, not from
%   JSON, so run_validation can check them against the generic loader too.
%   Returns [] for an id without a hand-built version.
%
%   Qiskit qubit 0 is MATLAB qubit 1. Each circuit mirrors the spec in
%   backend/app/quantum/examples.py.

arguments
    circuitId (1,1) string
end

switch circuitId
    case "bell"
        % H on qubit 0, CNOT 0 -> 1
        c = quantumCircuit([hGate(1); cxGate(1, 2)], 2, Name="Bell_State");
    case "superposition"
        % H on qubit 0
        c = quantumCircuit(hGate(1), 1, Name="Superposition");
    case "ghz"
        % H on qubit 0, CNOT 0 -> 1, CNOT 0 -> 2
        c = quantumCircuit([hGate(1); cxGate(1, 2); cxGate(1, 3)], 3, Name="GHZ_State");
    case "bit_flip"
        % X on qubit 0
        c = quantumCircuit(xGate(1), 1, Name="Bit_Flip");
    otherwise
        c = [];
end
end
