function p = chi2sf(statistic, dof)
%CHI2SF Chi-square survival function P(X >= statistic) for dof degrees of freedom.
%   Uses base MATLAB gammainc, so the Statistics and Machine Learning Toolbox
%   is not needed. Returns 1 when dof is 0. Same as chi2_sf in compare.py.

if dof <= 0
    p = 1;
else
    p = gammainc(statistic / 2, dof / 2, "upper");
end
end
