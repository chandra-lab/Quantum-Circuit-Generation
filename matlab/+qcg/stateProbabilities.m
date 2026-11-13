function [labels, probabilities] = stateProbabilities(state)
%STATEPROBABILITIES Exact measurement probabilities of a quantumState.
%   [labels, probabilities] = qcg.stateProbabilities(s) where s comes from
%   simulate. labels are MATLAB basis labels (qubit 1 first) for all 2^n
%   basis states, and probabilities = abs(s.Amplitudes).^2.
%
%   This reads the state directly instead of querystates, whose default
%   threshold drops near-zero states.

labels = qcg.toStringColumn(state.BasisStates);
probabilities = abs(state.Amplitudes(:)).^2;
end
