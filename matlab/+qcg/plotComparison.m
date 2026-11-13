function files = plotComparison(result, data, plotDir)
%PLOTCOMPARISON Save probability and difference bar charts for one circuit.
%   files = qcg.plotComparison(result, data, plotDir) writes
%   <id>_probabilities.png and <id>_difference.png and returns their paths.
%   x-axis labels are Qiskit bitstrings (rightmost character is qubit 0).

if ~isfolder(plotDir)
    mkdir(plotDir);
end
id = result.circuitId;
exact = result.exact;
sampled = result.sampled;
hasSamples = ~sampled.skipped;

fig = figure(Visible="off", Position=[100 100 1000 700]);
cleanup = onCleanup(@() close(fig));
layout = tiledlayout(fig, 2, 1, TileSpacing="compact");
title(layout, sprintf("%s: MATLAB vs Qiskit probabilities", result.circuitName), Interpreter="none");

ax = nexttile(layout);
groupedBars(ax, exact.states, [exact.reference exact.candidate], ...
    ["Qiskit Statevector", "MATLAB simulate"]);
title(ax, sprintf("Exact statevector (max |diff| = %.3g)", exact.maxAbsError));
xlabel(ax, "Qiskit bitstring (rightmost = qubit 0)");

ax = nexttile(layout);
if hasSamples
    states = unique([sampled.vsExact.states; sampled.vsAer.states]);
    values = [ ...
        qcg.valuesFor(sampled.vsExact.states, sampled.vsExact.reference, states), ...
        qcg.valuesFor(sampled.vsAer.states, sampled.vsAer.reference, states), ...
        qcg.valuesFor(sampled.vsAer.states, sampled.vsAer.candidate, states)];
    groupedBars(ax, states, values, ...
        ["Qiskit exact (measured)", sprintf("Aer, %d shots", data.shots), ...
         sprintf("MATLAB randsample, %d shots", sampled.shots)]);
    title(ax, sprintf("Sampled (TVD vs Aer = %.4f, homogeneity p = %.3g)", ...
        sampled.vsAer.totalVariation, sampled.homogeneity.pValue));
else
    title(ax, "Sampling skipped");
end
xlabel(ax, "Qiskit clbit string (rightmost = clbit 0)");

probabilitiesFile = fullfile(plotDir, id + "_probabilities.png");
exportgraphics(fig, probabilitiesFile, Resolution=150);
clear cleanup

fig = figure(Visible="off", Position=[100 100 1000 700]);
cleanup = onCleanup(@() close(fig));
layout = tiledlayout(fig, 2, 1, TileSpacing="compact");
title(layout, sprintf("%s: MATLAB minus Qiskit", result.circuitName), Interpreter="none");

ax = nexttile(layout);
groupedBars(ax, exact.states, exact.candidate - exact.reference, "MATLAB - Qiskit (exact)");
yline(ax, exact.tolerance, "--r", HandleVisibility="off");
yline(ax, -exact.tolerance, "--r", HandleVisibility="off");
title(ax, sprintf("Exact difference, tolerance %.0e", exact.tolerance));
ylabel(ax, "Probability difference");
xlabel(ax, "Qiskit bitstring (rightmost = qubit 0)");

ax = nexttile(layout);
if hasSamples
    states = unique([sampled.vsExact.states; sampled.vsAer.states]);
    matlabSampled = qcg.valuesFor(sampled.vsAer.states, sampled.vsAer.candidate, states);
    values = [ ...
        matlabSampled - qcg.valuesFor(sampled.vsAer.states, sampled.vsAer.reference, states), ...
        matlabSampled - qcg.valuesFor(sampled.vsExact.states, sampled.vsExact.reference, states)];
    groupedBars(ax, states, values, ["MATLAB sampled - Aer sampled", "MATLAB sampled - exact"]);
    title(ax, "Sampled differences (shot noise expected)");
else
    title(ax, "Sampling skipped");
end
ylabel(ax, "Probability difference");
xlabel(ax, "Qiskit clbit string (rightmost = clbit 0)");

differenceFile = fullfile(plotDir, id + "_difference.png");
exportgraphics(fig, differenceFile, Resolution=150);
clear cleanup

files = [probabilitiesFile; differenceFile];
end

function groupedBars(ax, labels, values, legendNames)
labels = qcg.toStringColumn(labels);
n = numel(labels);
if n == 1
    % bar treats a single row as one group per column; pad so each series is one bar.
    values = [values; nan(1, size(values, 2))];
end
bar(ax, values, "grouped");
xticks(ax, 1:n);
xticklabels(ax, labels);
xlim(ax, [0.5 n + 0.5]);
grid(ax, "on");
ylabel(ax, "Probability");
legend(ax, legendNames, Location="bestoutside", Interpreter="none");
end
