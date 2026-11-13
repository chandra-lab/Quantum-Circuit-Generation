function name = circuitName(raw)
%CIRCUITNAME Turn a spec circuit_name into a valid quantumCircuit Name.
%   quantumCircuit requires Name to start with a letter followed by letters,
%   digits, or underscores, so "Bell State" becomes "Bell_State".

name = regexprep(strtrim(string(raw)), "[^A-Za-z0-9_]", "_");
if isempty(regexp(name, "^[A-Za-z]", "once"))
    name = "c_" + name;
end
if strlength(name) > namelengthmax
    name = extractBefore(name, namelengthmax + 1);
end
end
