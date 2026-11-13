function checkBinaryLabels(labels)
%CHECKBINARYLABELS Error unless every label contains only '0' and '1'.

labels = string(labels);
if any(ismissing(labels), "all")
    error("qcg:badLabel", "Bitstring labels must not be missing.");
end
bad = strlength(regexprep(labels(:), "[01]", "")) > 0;
if any(bad)
    error("qcg:badLabel", "Bitstring must contain only '0' and '1': ""%s"".", labels(find(bad, 1)));
end
end
