classdef LoadExportTest < matlab.unittest.TestCase
    %LOADEXPORTTEST Reading the committed Qiskit exports. Needs only base MATLAB.

    properties
        DataDir
    end

    methods (TestClassSetup)
        function addSource(testCase)
            here = fileparts(mfilename("fullpath"));
            testCase.applyFixture(matlab.unittest.fixtures.PathFixture(fullfile(here, "..")));
            testCase.DataDir = fullfile(here, "..", "data", "qiskit_results");
        end
    end

    methods (Test)
        function loadsEveryExport(testCase)
            files = dir(fullfile(testCase.DataDir, "*.json"));
            files = files(~strcmp({files.name}, "manifest.json"));
            testCase.verifyGreaterThanOrEqual(numel(files), 4);
            for k = 1:numel(files)
                data = qcg.loadQiskitExport(fullfile(files(k).folder, files(k).name));
                testCase.verifyEqual(sum(data.exactProbabilities), 1, AbsTol=1e-12);
                testCase.verifyEqual(sum(data.sampledCounts), data.shots);
                testCase.verifyEqual(numel(data.measurements), numel(qcg.asCell(data.spec.measurements)));
            end
        end

        function bellHasHalfOnZeroZeroAndOneOne(testCase)
            data = qcg.loadQiskitExport(fullfile(testCase.DataDir, "bell.json"));
            p = qcg.valuesFor(data.exactStates, data.exactProbabilities, ["00"; "01"; "10"; "11"]);
            testCase.verifyEqual(p, [0.5; 0; 0; 0.5], AbsTol=1e-12);
            testCase.verifyEqual(data.gateSequence, ["h"; "cx"]);
        end

        function bitFlipKeepsSingleElementLists(testCase)
            % One-element JSON lists decode to scalars or 1x1 cells; the loader keeps them as vectors.
            data = qcg.loadQiskitExport(fullfile(testCase.DataDir, "bit_flip.json"));
            testCase.verifyEqual(data.sampledStates, "1");
            testCase.verifyEqual(data.sampledCounts, data.shots);
            testCase.verifyEqual(data.measurements, struct("qubit", 0, "clbit", 0));
        end

        function rejectsUnknownSchema(testCase)
            file = string(tempname) + ".json";
            fid = fopen(file, "w");
            fprintf(fid, '{"schema_version": 99}');
            fclose(fid);
            testCase.addTeardown(@() delete(file));
            testCase.verifyError(@() qcg.loadQiskitExport(file), "qcg:unsupportedSchema");
        end

        function circuitNameIsSanitised(testCase)
            testCase.verifyEqual(qcg.circuitName("Bell State"), "Bell_State");
            testCase.verifyEqual(qcg.circuitName("3-qubit GHZ"), "c_3_qubit_GHZ");
        end
    end
end
