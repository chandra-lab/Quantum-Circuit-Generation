function [labels, counts] = sampleState(state, shots)
%SAMPLESTATE Sample a quantumState with randsample.
%   [labels, counts] = qcg.sampleState(s, shots) returns the measured MATLAB
%   basis labels (qubit 1 first) and their counts. randsample uses the global
%   random number generator, so call rng first for repeatable counts.

m = randsample(state, shots);
labels = qcg.toStringColumn(m.MeasuredStates);
counts = double(m.Counts(:));
end
