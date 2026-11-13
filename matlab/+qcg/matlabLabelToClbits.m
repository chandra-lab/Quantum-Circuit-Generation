function clbits = matlabLabelToClbits(matlabLabels, measurements, numClbits)
%MATLABLABELTOCLBITS Map MATLAB qubit labels to Qiskit clbit bitstrings.
%   clbits = qcg.matlabLabelToClbits(labels, measurements, numClbits)
%
%   measurements is a struct array with 0-based Qiskit fields "qubit" and
%   "clbit" (as loaded by qcg.loadQiskitExport). For each measurement, clbit
%   c takes the value of Qiskit qubit q, which is character q+1 of the MATLAB
%   label. Unmeasured clbits read 0, as in Aer. The result is in Qiskit order
%   (rightmost character is clbit 0), so it can be compared with Aer counts.
%   Same as matlab_label_to_clbits in matlab/tools/compare.py.

labels = string(matlabLabels);
qcg.checkBinaryLabels(labels);
clbits = strings(size(labels));
for k = 1:numel(labels)
    label = char(labels(k));
    bits = repmat('0', 1, numClbits);
    for m = 1:numel(measurements)
        bits(measurements(m).clbit + 1) = label(measurements(m).qubit + 1);
    end
    clbits(k) = string(fliplr(bits));
end
end
