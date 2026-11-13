function matlabLabels = qiskitToMatlabLabel(qiskitLabels)
%QISKITTOMATLABLABEL Convert Qiskit bitstrings to MATLAB basis labels.
%   The mapping reverses the string and is its own inverse. See
%   qcg.matlabToQiskitLabel. Same as qiskit_to_matlab_label in compare.py.

labels = string(qiskitLabels);
qcg.checkBinaryLabels(labels);
matlabLabels = reverse(labels);
end
