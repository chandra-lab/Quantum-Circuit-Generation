classdef CompareDistributionsTest < matlab.unittest.TestCase
    %COMPAREDISTRIBUTIONSTEST Metrics and chi-square tests. Needs only base MATLAB.
    %   Expected values come from fixtures/metric_cases.json, which
    %   matlab/tools/compare.py generates, so a pass here means the MATLAB and
    %   Python implementations agree.

    properties
        Fixture
    end

    properties (Constant)
        RelTol = 1e-10
        AbsTol = 1e-14
    end

    methods (TestClassSetup)
        function addSourceAndFixture(testCase)
            here = fileparts(mfilename("fullpath"));
            testCase.applyFixture(matlab.unittest.fixtures.PathFixture(fullfile(here, "..")));
            testCase.Fixture = jsondecode(fileread(fullfile(here, "fixtures", "metric_cases.json")));
        end
    end

    methods (Test)
        function metricsMatchPython(testCase)
            cases = qcg.asCell(testCase.Fixture.metric_cases);
            for k = 1:numel(cases)
                c = cases{k};
                m = qcg.compareDistributions(c.reference.states, c.reference.values, ...
                    c.candidate.states, c.candidate.values, Epsilon=testCase.Fixture.epsilon);
                e = c.expected;
                label = "case " + string(c.name);
                testCase.verifyEqual(m.states, qcg.toStringColumn(e.states), label);
                testCase.verifyEqual(m.absDiff, e.abs_diff(:), RelTol=testCase.RelTol, AbsTol=testCase.AbsTol);
                testCase.verifyEqual(m.maxAbsError, e.max_abs_error, RelTol=testCase.RelTol, AbsTol=testCase.AbsTol);
                testCase.verifyEqual(m.totalVariation, e.total_variation, RelTol=testCase.RelTol, AbsTol=testCase.AbsTol);
                testCase.verifyEqual(m.hellinger, e.hellinger, RelTol=testCase.RelTol, AbsTol=testCase.AbsTol);
                testCase.verifyEqual(m.klDivergence, e.kl_divergence, RelTol=1e-8, AbsTol=1e-12);
            end
        end

        function identicalDistributionsHaveZeroDistance(testCase)
            m = qcg.compareDistributions(["00"; "11"], [0.5; 0.5], ["11"; "00"], [0.5; 0.5]);
            testCase.verifyEqual(m.maxAbsError, 0);
            testCase.verifyEqual(m.totalVariation, 0);
            testCase.verifyEqual(m.hellinger, 0);
            testCase.verifyEqual(m.klDivergence, 0, AbsTol=1e-15);
        end

        function disjointDistributionsHaveMaximumDistance(testCase)
            m = qcg.compareDistributions("0", 1, "1", 1);
            testCase.verifyEqual(m.totalVariation, 1, AbsTol=1e-15);
            testCase.verifyEqual(m.hellinger, 1, AbsTol=1e-15);
            testCase.verifyTrue(isfinite(m.klDivergence));
        end

        function duplicateLabelsAreSummed(testCase)
            m = qcg.compareDistributions(["0"; "1"], [0.5; 0.5], ["1"; "0"; "1"], [0.25; 0.5; 0.25]);
            testCase.verifyEqual(m.maxAbsError, 0, AbsTol=1e-15);
        end

        function chi2sfMatchesPython(testCase)
            cases = qcg.asCell(testCase.Fixture.chi2_sf_cases);
            for k = 1:numel(cases)
                c = cases{k};
                testCase.verifyEqual(qcg.chi2sf(c.statistic, c.dof), c.p_value, RelTol=1e-9, AbsTol=1e-14);
            end
        end

        function goodnessOfFitMatchesPython(testCase)
            cases = qcg.asCell(testCase.Fixture.goodness_of_fit_cases);
            for k = 1:numel(cases)
                c = cases{k};
                r = qcg.chiSquareGoodnessOfFit(c.counts.states, c.counts.values, ...
                    c.expected_probabilities.states, c.expected_probabilities.values);
                e = c.expected;
                testCase.verifyEqual(r.statistic, e.statistic, RelTol=testCase.RelTol, AbsTol=testCase.AbsTol);
                testCase.verifyEqual(r.dof, e.dof);
                testCase.verifyEqual(r.pValue, e.p_value, RelTol=1e-9, AbsTol=1e-14);
                testCase.verifyEqual(r.impossibleOutcomes, qcg.toStringColumn(e.impossible_outcomes));
                testCase.verifyEqual(r.passed, e.passed);
            end
        end

        function homogeneityMatchesPython(testCase)
            cases = qcg.asCell(testCase.Fixture.homogeneity_cases);
            for k = 1:numel(cases)
                c = cases{k};
                r = qcg.chiSquareHomogeneity(c.counts_a.states, c.counts_a.values, ...
                    c.counts_b.states, c.counts_b.values);
                e = c.expected;
                testCase.verifyEqual(r.statistic, e.statistic, RelTol=testCase.RelTol, AbsTol=testCase.AbsTol);
                testCase.verifyEqual(r.dof, e.dof);
                testCase.verifyEqual(r.pValue, e.p_value, RelTol=1e-9, AbsTol=1e-14);
                testCase.verifyEqual(r.passed, e.passed);
            end
        end

        function impossibleOutcomeFailsGoodnessOfFit(testCase)
            r = qcg.chiSquareGoodnessOfFit(["00"; "01"; "11"], [499; 1; 500], ["00"; "11"], [0.5; 0.5]);
            testCase.verifyEqual(r.impossibleOutcomes, "01");
            testCase.verifyFalse(r.passed);
        end
    end
end
