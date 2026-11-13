function out = valuesFor(states, values, keys)
%VALUESFOR Look up values by label, with 0 for a label that is not present.

keys = qcg.toStringColumn(keys);
[found, loc] = ismember(keys, qcg.toStringColumn(states));
out = zeros(numel(keys), 1);
out(found) = values(loc(found));
end
