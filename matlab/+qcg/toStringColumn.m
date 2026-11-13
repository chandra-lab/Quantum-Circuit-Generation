function s = toStringColumn(x)
%TOSTRINGCOLUMN Column string array from a string, char vector, cellstr, or [].
%   Converts before reshaping, so a char vector such as '001' stays one label.

s = reshape(string(x), [], 1);
end
