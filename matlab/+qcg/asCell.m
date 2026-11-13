function c = asCell(x)
%ASCELL Column cell array from a jsondecode list.
%   jsondecode returns a struct array when every object in a JSON list has the
%   same fields, and a cell array when they differ (for example, gates where only
%   rx/ry/rz carry "parameter"). An empty JSON list decodes to [].

if isempty(x)
    c = cell(0, 1);
elseif iscell(x)
    c = x(:);
elseif isstruct(x)
    c = num2cell(x(:));
else
    error("qcg:badList", "Expected a JSON list of objects.");
end
end
