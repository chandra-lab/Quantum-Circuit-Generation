function r = chiSquareGoodnessOfFit(countStates, counts, expStates, expProbabilities, options)
%CHISQUAREGOODNESSOFFIT Sampled counts against an exact distribution.
%   r = qcg.chiSquareGoodnessOfFit(countStates, counts, expStates, expProbabilities)
%
%   States with expected probability <= ZeroThreshold are impossible. Any
%   count on one fails the test. The chi-square statistic uses the remaining
%   states with dof = (number of possible states) - 1, and the test passes
%   when p >= Alpha. Same as chi_square_goodness_of_fit in compare.py.

arguments
    countStates
    counts double
    expStates
    expProbabilities double
    options.Alpha (1,1) double = 1e-3
    options.ZeroThreshold (1,1) double = 1e-10
end

[countStates, counts] = qcg.accumulateLabels(countStates, counts);
[expStates, expProbabilities] = qcg.accumulateLabels(expStates, expProbabilities);
shots = sum(counts);

isPossible = expProbabilities > options.ZeroThreshold;
possible = expStates(isPossible);
expectedAtCounts = qcg.valuesFor(expStates, expProbabilities, countStates);
impossible = countStates(counts > 0 & expectedAtCounts <= options.ZeroThreshold);

observed = qcg.valuesFor(countStates, counts, possible);
expected = shots * expProbabilities(isPossible);
statistic = sum((observed - expected).^2 ./ expected);
dof = max(numel(possible) - 1, 0);
if shots > 0
    pValue = qcg.chi2sf(statistic, dof);
else
    pValue = 1;
end

r = struct();
r.test = "chi_square_goodness_of_fit";
r.shots = shots;
r.statistic = statistic;
r.dof = dof;
r.pValue = pValue;
r.alpha = options.Alpha;
r.impossibleOutcomes = impossible;
r.passed = isempty(impossible) && pValue >= options.Alpha;
end
