function [states, values] = accumulateLabels(states, values)
%ACCUMULATELABELS Sort labels and sum the values of duplicates.
%   Returns column vectors. Sorting matches Python sorted() for '0'/'1' labels.

states = qcg.toStringColumn(states);
values = double(values(:));
if numel(states) ~= numel(values)
    error("qcg:sizeMismatch", "states and values must have the same number of elements.");
end
if isempty(states)
    states = strings(0, 1);
    values = zeros(0, 1);
    return
end
[states, ~, idx] = unique(states);
values = accumarray(idx, values, [numel(states) 1]);
end
