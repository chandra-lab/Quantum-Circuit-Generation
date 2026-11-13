function qiskit = matlabToQiskitLabel(matlabLabels)
%MATLABTOQISKITLABEL Convert MATLAB basis labels to Qiskit bitstrings.
%   qiskit = qcg.matlabToQiskitLabel(labels)
%
%   MATLAB quantumState.BasisStates put qubit 1 first (leftmost). Qiskit
%   bitstrings put qubit 0 last (rightmost), and MATLAB qubit k is Qiskit
%   qubit k-1. The same basis state is therefore the reversed string:
%
%       MATLAB "100" (qubit 1 is |1>)  ->  Qiskit "001" (qubit 0 is |1>)
%
%   Accepts a string array, char vector, or cellstr; returns a string array of
%   the same size. Same as matlab_to_qiskit_label in matlab/tools/compare.py.

labels = string(matlabLabels);
qcg.checkBinaryLabels(labels);
qiskit = reverse(labels);
end
