function r = chiSquareHomogeneity(statesA, countsA, statesB, countsB, options)
%CHISQUAREHOMOGENEITY Two-sample chi-square test that two count tables share one distribution.
%   Used for MATLAB randsample counts against Qiskit Aer counts. The two
%   samplers use different random number generators, so the counts never
%   match exactly; the test asks whether the difference is larger than shot
%   noise explains. Same as chi_square_homogeneity in compare.py.

arguments
    statesA
    countsA double
    statesB
    countsB double
    options.Alpha (1,1) double = 1e-3
end

[statesA, countsA] = qcg.accumulateLabels(statesA, countsA);
[statesB, countsB] = qcg.accumulateLabels(statesB, countsB);
keys = unique([statesA; statesB]);
a = qcg.valuesFor(statesA, countsA, keys);
b = qcg.valuesFor(statesB, countsB, keys);
keep = (a + b) > 0;
a = a(keep);
b = b(keep);

nA = sum(a);
nB = sum(b);
statistic = 0;
if nA > 0 && nB > 0
    column = a + b;
    expectedA = nA * column / (nA + nB);
    expectedB = nB * column / (nA + nB);
    statistic = sum((a - expectedA).^2 ./ expectedA) + sum((b - expectedB).^2 ./ expectedB);
end
dof = max(nnz(keep) - 1, 0);

r = struct();
r.test = "chi_square_homogeneity";
r.shotsA = nA;
r.shotsB = nB;
r.statistic = statistic;
r.dof = dof;
r.pValue = qcg.chi2sf(statistic, dof);
r.alpha = options.Alpha;
r.passed = r.pValue >= options.Alpha;
end
