classdef BitOrderTest < matlab.unittest.TestCase
    %BITORDERTEST Qiskit <-> MATLAB label mapping. Needs only base MATLAB.

    properties
        Fixture
    end

    methods (TestClassSetup)
        function addSourceAndFixture(testCase)
            here = fileparts(mfilename("fullpath"));
            testCase.applyFixture(matlab.unittest.fixtures.PathFixture(fullfile(here, "..")));
            testCase.Fixture = jsondecode(fileread(fullfile(here, "fixtures", "metric_cases.json")));
        end
    end

    methods (Test)
        function qubitOneIsQiskitQubitZero(testCase)
            testCase.verifyEqual(qcg.matlabToQiskitLabel("100"), "001");
            testCase.verifyEqual(qcg.qiskitToMatlabLabel("001"), "100");
        end

        function mapsArraysElementwise(testCase)
            labels = ["00"; "01"; "10"; "11"];
            testCase.verifyEqual(qcg.matlabToQiskitLabel(labels), ["00"; "10"; "01"; "11"]);
            testCase.verifyEqual(qcg.matlabToQiskitLabel({'110', '0'}), ["011", "0"]);
        end

        function mappingIsAnInvolution(testCase)
            labels = string(dec2bin(0:15, 4));
            testCase.verifyEqual(qcg.qiskitToMatlabLabel(qcg.matlabToQiskitLabel(labels)), labels);
        end

        function rejectsNonBinaryLabels(testCase)
            testCase.verifyError(@() qcg.matlabToQiskitLabel("012"), "qcg:badLabel");
            testCase.verifyError(@() qcg.matlabToQiskitLabel("|01>"), "qcg:badLabel");
        end

        function matchesSharedFixtureLabels(testCase)
            cases = qcg.asCell(testCase.Fixture.label_cases);
            for k = 1:numel(cases)
                testCase.verifyEqual(qcg.matlabToQiskitLabel(cases{k}.matlab), string(cases{k}.qiskit));
            end
        end

        function matchesSharedFixtureClbits(testCase)
            cases = qcg.asCell(testCase.Fixture.clbit_cases);
            for k = 1:numel(cases)
                c = cases{k};
                measurements = struct("qubit", {}, "clbit", {});
                items = qcg.asCell(c.measurements);
                for m = 1:numel(items)
                    measurements(m).qubit = items{m}.qubit;
                    measurements(m).clbit = items{m}.clbit;
                end
                actual = qcg.matlabLabelToClbits(c.matlab, measurements, c.num_clbits);
                testCase.verifyEqual(actual, string(c.qiskit_clbits));
            end
        end

        function reversedProbeOnlyMatchesAfterMapping(testCase)
            % Qiskit: qubit 0 always 1 -> "001" (0.75) and "111" (0.25).
            qiskitStates = ["001"; "111"];
            p = [0.75; 0.25];
            matlabStates = ["100"; "111"];

            unmapped = qcg.compareDistributions(qiskitStates, p, matlabStates, p);
            testCase.verifyEqual(unmapped.maxAbsError, 0.75, AbsTol=1e-15);

            mapped = qcg.compareDistributions(qiskitStates, p, qcg.matlabToQiskitLabel(matlabStates), p);
            testCase.verifyEqual(mapped.maxAbsError, 0);
        end
    end
end
