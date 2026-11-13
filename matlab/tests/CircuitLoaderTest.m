classdef CircuitLoaderTest < matlab.unittest.TestCase
    %CIRCUITLOADERTEST Building and simulating circuits from exported specs.
    %   Needs the MATLAB Support Package for Quantum Computing. Without it,
    %   every test here is reported as Incomplete (assumption failed), not Failed.

    properties
        DataDir
    end

    properties (TestParameter)
        gateCase = struct( ...
            "i", {{"i", 0, [], "id", [], 1, []}}, ...
            "x", {{"x", 0, [], "x", [], 1, []}}, ...
            "y", {{"y", 1, [], "y", [], 2, []}}, ...
            "z", {{"z", 0, [], "z", [], 1, []}}, ...
            "h", {{"h", 2, [], "h", [], 3, []}}, ...
            "s", {{"s", 0, [], "s", [], 1, []}}, ...
            "t", {{"t", 0, [], "t", [], 1, []}}, ...
            "rx", {{"rx", 1, 0.3, "rx", [], 2, 0.3}}, ...
            "ry", {{"ry", 0, -1.2, "ry", [], 1, -1.2}}, ...
            "rz", {{"rz", 2, pi, "rz", [], 3, pi}}, ...
            "cx", {{"cx", [0 2], [], "cx", 1, 3, []}}, ...
            "cz", {{"cz", [2 1], [], "cz", 3, 2, []}}, ...
            "swap", {{"swap", [0 1], [], "swap", [], [1 2], []}})
    end

    methods (TestClassSetup)
        function setup(testCase)
            here = fileparts(mfilename("fullpath"));
            testCase.applyFixture(matlab.unittest.fixtures.PathFixture(fullfile(here, "..")));
            testCase.DataDir = fullfile(here, "..", "data", "qiskit_results");
            testCase.assumeFalse(isempty(which("quantumCircuit")), ...
                "MATLAB Support Package for Quantum Computing is not installed.");
        end
    end

    methods (Test)
        function mapsEachSupportedGate(testCase, gateCase)
            [name, qubits, parameter, type, control, target, angle] = gateCase{:};
            spec = struct("gate", name, "qubits", qubits);
            if ~isempty(parameter)
                spec.parameter = parameter;
            end
            g = qcg.gateFromSpec(spec, 3);
            testCase.verifyEqual(string(g.Type), string(type));
            testCase.verifyEqual(double(g.TargetQubits(:)'), double(target));
            if isempty(control)
                testCase.verifyEmpty(g.ControlQubits);
            else
                testCase.verifyEqual(double(g.ControlQubits), double(control));
            end
            if isempty(angle)
                testCase.verifyEmpty(g.Angles);
            else
                testCase.verifyEqual(double(g.Angles), angle, AbsTol=1e-15);
            end
        end

        function rejectsBadGates(testCase)
            testCase.verifyError(@() qcg.gateFromSpec(struct("gate", "u3", "qubits", 0), 2), "qcg:unsupportedGate");
            testCase.verifyError(@() qcg.gateFromSpec(struct("gate", "x", "qubits", 2), 2), "qcg:badQubit");
            testCase.verifyError(@() qcg.gateFromSpec(struct("gate", "cx", "qubits", [1 1]), 2), "qcg:badQubit");
            testCase.verifyError(@() qcg.gateFromSpec(struct("gate", "cx", "qubits", 0), 2), "qcg:badArity");
            testCase.verifyError(@() qcg.gateFromSpec(struct("gate", "rx", "qubits", 0), 2), "qcg:badParameter");
            testCase.verifyError(@() qcg.gateFromSpec( ...
                struct("gate", "h", "qubits", 0, "parameter", 1), 2), "qcg:badParameter");
        end

        function acceptsUppercaseGateNames(testCase)
            g = qcg.gateFromSpec(struct("gate", "CX", "qubits", [1 0]), 2);
            testCase.verifyEqual(string(g.Type), "cx");
            testCase.verifyEqual(double(g.ControlQubits), 2);
            testCase.verifyEqual(double(g.TargetQubits), 1);
        end

        function loaderMatchesQiskitExactProbabilities(testCase)
            files = dir(fullfile(testCase.DataDir, "*.json"));
            files = files(~strcmp({files.name}, "manifest.json"));
            for k = 1:numel(files)
                data = qcg.loadQiskitExport(fullfile(files(k).folder, files(k).name));
                c = qcg.circuitFromSpec(data.spec);
                testCase.verifyEqual(c.NumQubits, data.numQubits);
                [labels, p] = qcg.stateProbabilities(simulate(c));
                m = qcg.compareDistributions(data.exactStates, data.exactProbabilities, ...
                    qcg.matlabToQiskitLabel(labels), p);
                testCase.verifyLessThanOrEqual(m.maxAbsError, 1e-10, data.circuitId);
            end
        end

        function handBuiltCircuitsMatchLoader(testCase)
            for id = ["bell", "superposition", "ghz", "bit_flip"]
                data = qcg.loadQiskitExport(fullfile(testCase.DataDir, id + ".json"));
                [la, pa] = qcg.stateProbabilities(simulate(qcg.referenceCircuit(id)));
                [lb, pb] = qcg.stateProbabilities(simulate(qcg.circuitFromSpec(data.spec)));
                testCase.verifyEqual(la, lb, id);
                testCase.verifyEqual(pa, pb, id, AbsTol=1e-12);
            end
        end

        function bellAndGhzProbabilities(testCase)
            [labels, p] = qcg.stateProbabilities(simulate(qcg.referenceCircuit("bell")));
            testCase.verifyEqual(qcg.valuesFor(labels, p, ["00"; "11"]), [0.5; 0.5], AbsTol=1e-12);
            [labels, p] = qcg.stateProbabilities(simulate(qcg.referenceCircuit("ghz")));
            testCase.verifyEqual(qcg.valuesFor(labels, p, ["000"; "111"]), [0.5; 0.5], AbsTol=1e-12);
        end

        function probeShowsMatlabOrder(testCase)
            % Qiskit "001" (qubit 0 set) must appear in MATLAB as "100" (qubit 1 set).
            data = qcg.loadQiskitExport(fullfile(testCase.DataDir, "bit_order_probe.json"));
            [labels, p] = qcg.stateProbabilities(simulate(qcg.circuitFromSpec(data.spec)));
            testCase.verifyEqual(qcg.valuesFor(labels, p, "100"), 0.75, AbsTol=1e-12);
            testCase.verifyEqual(qcg.valuesFor(labels, p, "001"), 0, AbsTol=1e-12);
        end

        function emptyCircuitBuilds(testCase)
            spec = struct("circuit_name", "Empty", "num_qubits", 2, "gates", []);
            c = qcg.circuitFromSpec(spec);
            testCase.verifyEqual(c.NumQubits, 2);
            [labels, p] = qcg.stateProbabilities(simulate(c));
            testCase.verifyEqual(qcg.valuesFor(labels, p, "00"), 1, AbsTol=1e-15);
        end

        function validateCircuitPassesOnExports(testCase)
            rng(7, "twister");
            files = dir(fullfile(testCase.DataDir, "*.json"));
            files = files(~strcmp({files.name}, "manifest.json"));
            for k = 1:numel(files)
                data = qcg.loadQiskitExport(fullfile(files(k).folder, files(k).name));
                r = qcg.validateCircuit(data, Shots=2000);
                testCase.verifyTrue(r.exactPassed, data.circuitId);
                testCase.verifyEqual(r.stateFidelity, 1, AbsTol=1e-10);
                testCase.verifyEmpty(r.sampled.goodnessOfFit.impossibleOutcomes);
            end
        end
    end
end
