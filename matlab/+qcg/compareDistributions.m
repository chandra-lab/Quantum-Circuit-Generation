function m = compareDistributions(refStates, refValues, candStates, candValues, options)
%COMPAREDISTRIBUTIONS Per-state and summary differences between two distributions.
%   m = qcg.compareDistributions(refStates, refValues, candStates, candValues)
%   aligns both distributions on the sorted union of labels (0 where a label
%   is missing) and returns:
%
%     states, reference, candidate   aligned column vectors
%     absDiff         |candidate - reference| per state
%     maxAbsError     max(absDiff)
%     totalVariation  0.5 * sum(absDiff)
%     hellinger       sqrt(0.5 * sum((sqrt(p) - sqrt(q)).^2)), in [0, 1]
%     klDivergence    KL(reference || candidate) after adding Epsilon to every
%                     state and renormalising both sides
%
%   Both inputs must use the same label convention. Convert MATLAB labels with
%   qcg.matlabToQiskitLabel first. Same formulas as compare_distributions in
%   matlab/tools/compare.py; matlab/tests/CompareDistributionsTest.m checks
%   both against the shared fixture.

arguments
    refStates
    refValues double
    candStates
    candValues double
    options.Epsilon (1,1) double {mustBePositive} = 1e-12
end

[refStates, refValues] = qcg.accumulateLabels(refStates, refValues);
[candStates, candValues] = qcg.accumulateLabels(candStates, candValues);
states = unique([refStates; candStates]);
p = qcg.valuesFor(refStates, refValues, states);
q = qcg.valuesFor(candStates, candValues, states);

absDiff = abs(q - p);
m = struct();
m.states = states;
m.reference = p;
m.candidate = q;
m.absDiff = absDiff;
if isempty(absDiff)
    m.maxAbsError = 0;
else
    m.maxAbsError = max(absDiff);
end
m.totalVariation = 0.5 * sum(absDiff);
m.hellinger = sqrt(0.5 * sum((sqrt(max(p, 0)) - sqrt(max(q, 0))).^2));

ps = max(p, 0) + options.Epsilon;
qs = max(q, 0) + options.Epsilon;
ps = ps / sum(ps);
qs = qs / sum(qs);
m.klDivergence = max(sum(ps .* log(ps ./ qs)), 0);
m.epsilon = options.Epsilon;
end
