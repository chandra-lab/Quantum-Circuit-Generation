function data = loadQiskitExport(file)
%LOADQISKITEXPORT Read one JSON file written by app.tools.export_for_matlab.
%   data = qcg.loadQiskitExport(file) returns a struct with column vectors.
%   Every bitstring in it is in Qiskit order (rightmost character is qubit 0,
%   or clbit 0 for sampled counts). Qubit and clbit indices stay 0-based, as
%   exported. qcg.circuitFromSpec adds 1 when it builds MATLAB gates.

arguments
    file (1,1) string
end

raw = jsondecode(fileread(file));
if ~isfield(raw, "schema_version") || raw.schema_version ~= 1
    error("qcg:unsupportedSchema", "%s is not a schema_version 1 Qiskit export.", file);
end

data = struct();
data.file = file;
data.circuitId = string(raw.circuit_id);
data.circuitName = string(raw.circuit_name);
data.source = string(raw.source);
data.numQubits = double(raw.num_qubits);
data.numClbits = double(raw.num_clbits);
data.spec = raw.spec;
data.gateSequence = qcg.toStringColumn(raw.gate_sequence);
data.measurements = measurementArray(raw.measurements);
data.bitOrdering = raw.bit_ordering;

data.exactStates = qcg.toStringColumn(raw.exact.bitstrings);
data.exactProbabilities = double(raw.exact.probabilities(:));
data.exactAmplitudes = complex(double(raw.exact.amplitudes_real(:)), double(raw.exact.amplitudes_imag(:)));
data.measuredStates = qcg.toStringColumn(raw.exact.measured_bitstrings);
data.measuredProbabilities = double(raw.exact.measured_probabilities(:));

data.shots = double(raw.sampled.shots);
data.seed = double(raw.sampled.seed_simulator);
data.sampledStates = qcg.toStringColumn(raw.sampled.bitstrings);
data.sampledCounts = double(raw.sampled.counts(:));
data.sampledProbabilities = double(raw.sampled.probabilities(:));

data.versions = raw.versions;

if numel(data.exactStates) ~= 2^data.numQubits || numel(data.exactProbabilities) ~= 2^data.numQubits
    error("qcg:badExport", "%s: exact results must list all 2^%d basis states.", file, data.numQubits);
end
end

function m = measurementArray(raw)
m = struct("qubit", {}, "clbit", {});
items = qcg.asCell(raw);
for k = 1:numel(items)
    m(k, 1).qubit = double(items{k}.qubit);
    m(k, 1).clbit = double(items{k}.clbit);
end
end
