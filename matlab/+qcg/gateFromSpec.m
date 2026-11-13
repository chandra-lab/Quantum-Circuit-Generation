function g = gateFromSpec(gateSpec, numQubits)
%GATEFROMSPEC Map one exported gate to a MATLAB quantum gate.
%   g = qcg.gateFromSpec(gateSpec, numQubits). gateSpec has fields "gate",
%   "qubits" (0-based, Qiskit), and "parameter" for rx/ry/rz (radians).
%
%   Spec gate   MATLAB gate                 Qubits
%   i           idGate(t)                   [t]
%   x, y, z     xGate, yGate, zGate         [t]
%   h, s, t     hGate, sGate, tGate         [t]
%   rx, ry, rz  rxGate(t,theta), ...        [t]
%   cx          cxGate(control, target)     [control, target]
%   cz          czGate(control, target)     [control, target]
%   swap        swapGate(t1, t2)            [t1, t2]
%
%   Only these names are accepted, matching backend/app/quantum/gates.py.

arguments
    gateSpec (1,1) struct
    numQubits (1,1) double
end

name = lower(strtrim(string(gateSpec.gate)));
q = double(gateSpec.qubits(:)') + 1;
if isempty(q) || any(q < 1 | q > numQubits | q ~= fix(q))
    error("qcg:badQubit", "Gate '%s' has a qubit index outside 0..%d.", name, numQubits - 1);
end
hasParameter = isfield(gateSpec, "parameter") && ~isempty(gateSpec.parameter);

switch name
    case {"rx", "ry", "rz"}
        requireArity(name, q, 1);
        if ~hasParameter || ~isnumeric(gateSpec.parameter) || ~isscalar(gateSpec.parameter) ...
                || ~isfinite(gateSpec.parameter)
            error("qcg:badParameter", "Gate '%s' requires a finite numeric parameter.", name);
        end
        theta = double(gateSpec.parameter);
        switch name
            case "rx"
                g = rxGate(q, theta);
            case "ry"
                g = ryGate(q, theta);
            otherwise
                g = rzGate(q, theta);
        end
        return
end

if hasParameter
    error("qcg:badParameter", "Gate '%s' does not take a parameter.", name);
end

switch name
    case "i"
        requireArity(name, q, 1);
        g = idGate(q);
    case "x"
        requireArity(name, q, 1);
        g = xGate(q);
    case "y"
        requireArity(name, q, 1);
        g = yGate(q);
    case "z"
        requireArity(name, q, 1);
        g = zGate(q);
    case "h"
        requireArity(name, q, 1);
        g = hGate(q);
    case "s"
        requireArity(name, q, 1);
        g = sGate(q);
    case "t"
        requireArity(name, q, 1);
        g = tGate(q);
    case "cx"
        requireArity(name, q, 2);
        g = cxGate(q(1), q(2));
    case "cz"
        requireArity(name, q, 2);
        g = czGate(q(1), q(2));
    case "swap"
        requireArity(name, q, 2);
        g = swapGate(q(1), q(2));
    otherwise
        error("qcg:unsupportedGate", "Unsupported gate '%s'.", name);
end
end

function requireArity(name, q, n)
if numel(q) ~= n
    error("qcg:badArity", "Gate '%s' expects %d qubit(s), got %d.", name, n, numel(q));
end
if n == 2 && q(1) == q(2)
    error("qcg:badQubit", "Gate '%s' requires distinct qubits.", name);
end
end
