"""Build clean and highlighted LaTeX revisions from the submitted manuscript."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "applsci-4556799.tex"
OUT = ROOT / "revision_output"


ABSTRACT = r"""\abstract{STLC Manager is an LLM-supported pipeline for generating test scenarios and test cases from requirements, UML/XML models, and source code, followed by pre-execution semantic redundancy reduction. We evaluate Serial, Bulk, and Parallel processing modes on one industrially motivated robotic benchmark. Three separately completed evaluator files contain labels for the same 1,074 generated test cases; majority voting produced 740 Unique and 334 Similar decisions. Overall inter-rater reliability was low (Fleiss' $\kappa=0.1864$), indicating substantial variability in human redundancy judgements. Item-level evaluation of a documented 72-configuration subset of the 74 non-empty archived optimization records revealed substantial variation and directly quantified the principal risk: consensus-Unique cases classified as Similar and therefore removed. A reproducible offline TF--IDF and cosine-similarity analysis, evaluated at three fixed thresholds, achieved an overall Similar-class F1 of 0.4932 and balanced accuracy of 0.6434 at threshold 0.50, with 109 false removals. The previously reported 96.52\% value is retained only as a post-hoc count-level distributional similarity and is not item-level accuracy. The study evaluates semantic redundancy reduction, scenario-level representation, compactness, and artefact traceability before execution; it does not establish executability, coverage, mutation adequacy, or fault detection. Comprehensive repeated-run analysis and execution-based validation remain future work.}"""


INTRO = r"""\section{Introduction}\label{sec1}
[REV_BEGIN]
Large Language Models (LLMs) can transform requirements, source code, and models into testing artefacts, but their outputs may be redundant, unstable, or structurally inconsistent \citep{bib1,bib2,bib3,bib4}. This study evaluates STLC Manager as an integrated pipeline for heterogeneous artefact interpretation, scenario and test-case generation, and pre-execution semantic refinement. The contribution is the integration and evaluation workflow, not a claim that Smart Selection is a fundamentally new semantic-similarity algorithm.

The study asks four research questions. RQ1 examines how generation volume varies across artefact and model combinations. RQ2 describes semantic redundancy reduction and scenario representation under the archived Serial, Bulk, and Parallel configurations; it does not treat mode as an isolated causal factor. RQ3 measures how item-level optimizer decisions compare with a three-evaluator majority consensus, including the false-removal risk in which a consensus-Unique case is classified as Similar. RQ4 compares the LLM-mediated decisions with a reproducible TF--IDF and cosine-similarity baseline.

The contributions are: (1) a unified LLM-supported pipeline linking heterogeneous software artefacts to structured pre-execution test artefacts; (2) a descriptive analysis of archived Serial, Bulk, and Parallel configurations, including their incomplete strategy--optimizer crossing; (3) item-level analysis against three separately completed evaluator files, including agreement coefficients, confusion matrices, precision, recall, F1, balanced accuracy, and false-removal counts; (4) an offline lexical baseline that uses the archived test cases; and (5) an explicit separation between semantic suite refinement and downstream execution-based validation. All claims are restricted to the evaluated industrially motivated robotic benchmark. Section~\ref{sec2} reviews related work, Section~\ref{sec3} describes the framework, Sections 4 and 5 present the method and results, and the final sections discuss limitations and conclusions.
[REV_END]
"""


LITERATURE = r"""\section{Literature}\label{sec2}
[REV_BEGIN]
STLC organizes requirements analysis, planning, test design, execution, and reporting; the present work addresses only artefact analysis, test generation, and pre-execution refinement \citep{bib5,bib6}. Research on model-driven engineering and digital twins shows why structured requirements, behavioural models, and source artefacts can provide complementary testing context \citep{bib11,bib16,bib19,bib23}. These studies motivate traceable artefact transformation but do not by themselves validate generated tests.

LLM-based software-testing studies report useful generation capabilities together with limitations in stability, structural consistency, and redundancy \citep{bib3,bib32,bib33}. Search-based, coverage-guided, and mutation-oriented approaches address downstream execution properties \citep{bib34,bib35,bib39}; those outcomes are outside the evidence available in the present archive. Our evaluation therefore avoids treating semantic similarity as a proxy for executable correctness or fault detection.

Semantic deduplication can be implemented at several levels. Lexical methods such as TF--IDF provide inexpensive and deterministic similarity scores; embedding retrieval can improve semantic candidate discovery; reranking or LLM comparison can then apply more detailed criteria to a smaller candidate set. A retrieval--reranking separation has been shown to improve efficiency and traceability in another high-stakes document-matching setting \citep{bib70}; we cite it as an architectural analogy rather than direct evidence for test optimization. This staged design is relevant because unrestricted pairwise comparison grows quadratically.

The research gap addressed here is consequently narrow: an integrated, traceable evaluation of heterogeneous artefact-to-test generation followed by alternative LLM-mediated processing modes and item-level human-referenced redundancy analysis. The study does not claim a new trained classifier, state-of-the-art superiority, or general effectiveness across software domains.
[REV_END]
"""


OPTIMIZATION = r"""\subsubsection{Test Case Optimization}\label{subsubsec-test-case-optimization}
[REV_BEGIN]
Each test case is represented by its Title, Description, and Objective, $x_i=(t_i,d_i,o_i)$. The stored comparison prompt instructs the LLM to prioritize Description, then Objective, then Title; two cases are considered equivalent only when their validation intent and scenario are substantially the same. The required response is a JSON object containing one Boolean field, \texttt{is\_same}. The archived logs preserve parsed Boolean decisions, prompts, model identifiers, and timestamps. The supplied revision package does not include the production parser, so malformed-response handling and terminal retry behaviour cannot be independently verified.

The function $S(x_i,x_j)\in\{0,1\}$ is therefore an LLM-mediated prompted classification, not a trained deterministic classifier. In Serial mode, cases are processed in input order. A candidate is compared with previously retained representatives and is removed after the first positive match; otherwise it becomes a new representative. The stopping condition is exhaustion of the ordered list. Because the representative set depends on earlier decisions, changing input order can change the result.

Bulk mode asks the model to classify a group of cases jointly. Every supplied Bulk comparison log labels the evaluated operation as \texttt{Single LLM Call for All Test Cases}, including the 169-case records. No production implementation was supplied, so behaviour when a larger suite exceeds a model context window, including any sequential partitioning or cross-batch reconciliation, cannot be verified. Bulk should therefore not be defined intrinsically as either a single-prompt or an API-only method beyond the archived runs. Parallel records preserve explicit pairwise comparisons and are labelled \texttt{GeminiBatchAPI\_Adaptive}; however, the archive does not expose exact request scheduling, concurrency limits, contradictory-decision handling, transitive closure, or representative reconciliation after merging.

The archived design is not a fully crossed strategy--optimizer experiment. Serial contains 45 archived records across 11 model identifiers. This set includes two Gemini Serial records. The study-aligned Bulk subset contains 14 records. Seven use Gemini-2.5 Flash and seven use Gemini-2.5 Pro. Parallel contains 14 records, all using Gemini-2.5 Flash or Pro. One additional Bulk artifact remains in the archive-wide audit. It is excluded from this design summary because its backend and role in the study cannot be verified. Model identifiers are recorded, but a provider/backend field, local hardware, GPU memory, and exact context or request limits are not. A separate end-to-end harness defaults to an LM Studio endpoint, but it does not prove which backend served the archived records. Consequently, mode, optimizer, provider, and run configuration cannot generally be separated as causal factors.
[REV_END]

\begin{table}[H]
\caption{Study-aligned optimization design and available execution metadata}
\label{tab:optimization-design}
\centering
\begin{tabular}{p{0.11\linewidth}p{0.28\linewidth}p{0.24\linewidth}p{0.27\linewidth}}
\toprule
\textbf{Mode} & \textbf{Optimizer records} & \textbf{Recorded organization} & \textbf{Deployment evidence and limitation} \\
\midrule
[HROW]Serial & 45 records; 11 model identifiers, including Gemini-2.5 Flash and Pro & Ordered pairwise comparison against retained representatives & Provider/backend not stored; order-dependent \\
[HROW]Bulk & 14 study-aligned records: Flash (7), Pro (7) & Logs state \texttt{Single LLM Call for All Test Cases} & Provider/backend and over-context behaviour not stored \\
[HROW]Parallel & 14 records: Flash (7), Pro (7) & Logs state \texttt{GeminiBatchAPI\_Adaptive} & Exact scheduling, concurrency limits, and merge policy not stored \\
\bottomrule
\end{tabular}
\end{table}

\begin{algorithm}[H]
\caption{Order-dependent Serial representative selection}
\label{alg:smart-selection}
\begin{algorithmic}[1]
\Require Ordered test suite $T=\langle t_1,\ldots,t_n\rangle$
\Ensure Retained representatives $U$ and removed cases $R$
\State $U\gets\emptyset$; $R\gets\emptyset$
\ForAll{$t_i$ in input order}
  \State $\mathit{removed}\gets\textbf{false}$
  \ForAll{$u_j\in U$ in retention order}
    \If{$S(t_i,u_j)=1$}
      \State $R\gets R\cup\{t_i\}$; $\mathit{removed}\gets\textbf{true}$; \textbf{break}
    \EndIf
  \EndFor
  \If{\textbf{not} $\mathit{removed}$} \State $U\gets U\cup\{t_i\}$ \EndIf
\EndFor
\State \Return $(U,R)$
\end{algorithmic}
\end{algorithm}
"""


HUMAN_METHODS = r"""\subsection{Human-in-the-Loop Oracle}
[REV_BEGIN]
Three separately completed evaluator files (Human 1, Human 2, and Human 3) contain binary labels for the same 1,074 test cases from seven source-model suites. Each evaluator labelled a case Unique when it represented a distinct testing objective within its suite and Similar when its validation intent overlapped another case. The interface presented complete suites rather than isolated pairs. The files document separate completion artefacts, but they do not record whether evaluators worked without interaction or could see one another's labels. Evaluator names, experience, blinding, adjudication, and completion timestamps were not stored; independence is therefore not claimed.

For each item, majority vote defines the consensus reference. With three complete binary ratings, no tie is possible. Fleiss' kappa measures three-rater agreement, and pairwise Cohen's kappa is also reported. The optimizer comparison treats Similar as the positive class because it triggers removal. Thus, a consensus-Unique case classified as Similar is a false positive and the principal false-removal risk. For every matched configuration we compute the confusion matrix, Similar-class precision, recall, F1, balanced accuracy, Cohen's kappa, and false-positive and false-negative counts.

The offline baseline concatenates Title, Description, and Objective, uses lowercase word unigrams and bigrams with sublinear TF--IDF weighting, and applies cosine similarity in the same order-dependent representative-building pattern as Serial mode. Three fixed analysis thresholds (0.30, 0.50, and 0.70) are reported. The supplied archive does not establish that they were selected before Human Oracle results were examined, so no preregistration or prospective-selection claim is made. The complete implementation and item-level outputs are included in \texttt{revision\_analysis/}.
[REV_END]
"""


HUMAN_RESULTS = r"""\subsection{Item-Level Human Oracle and Baseline Results}
[REV_BEGIN]
All three evaluator files contain labels for the same 1,074 items. Majority voting yielded 740 Unique and 334 Similar cases. Overall Fleiss' kappa was 0.1864; pairwise Cohen kappas were 0.1638, 0.1446, and 0.2671. The low overall agreement and source-suite variation indicate substantial variability in human redundancy judgements. Majority consensus is used as a transparent comparator, not as objective ground truth or an error-free gold standard.
[REV_END]

\begin{table}[H]
\caption{Three-evaluator consensus and inter-rater agreement}
\label{tab:consensus-agreement}
\centering
\begin{tabular}{lrrrr}
\toprule
\textbf{Source model} & \textbf{Items} & \textbf{Unique} & \textbf{Similar} & \textbf{Fleiss' $\kappa$} \\
\midrule
[HROW]Codestral-22B & 123 & 88 & 35 & 0.2134 \\
[HROW]Gemini2.5-Flash & 139 & 110 & 29 & -0.0312 \\
[HROW]Gemini2.5-Pro & 152 & 105 & 47 & 0.1228 \\
[HROW]GPT-OSS-20B & 137 & 83 & 54 & 0.6564 \\
[HROW]LLaMa3.2-3B & 169 & 121 & 48 & -0.0252 \\
[HROW]LLaMa3.3-70B & 177 & 124 & 53 & 0.0965 \\
[HROW]Qwen3-Coder-30B & 177 & 109 & 68 & 0.2462 \\
[HROW]\textbf{Overall} & \textbf{1,074} & \textbf{740} & \textbf{334} & \textbf{0.1864} \\
\bottomrule
\end{tabular}
\end{table}

[REV_BEGIN]
The archive contains 74 non-empty optimization records. Seventy-two form the item-level analysis set and could be matched under the documented configuration rule using normalized Title, Description, and Objective. Record 0 is an auxiliary 49-case partial suite rather than any complete Human Oracle suite. Record 18 contains the 137 GPT-OSS-20B items but is an earlier auxiliary GPT-OSS/GPT-OSS Serial result; the later systematically named record 39 represents that same source--optimizer--mode configuration in the benchmark, so record 18 is retained in the archive count but not counted as a separate benchmark configuration. Serial F1 ranged from 0.00 to 0.72, Bulk from 0.00 to 0.66, and Parallel from 0.06 to 0.57. The number of consensus-Unique cases incorrectly removed ranged from 0 to 65 for Serial, 0 to 57 for Bulk, and 10 to 41 for Parallel. These ranges summarize heterogeneous source/optimizer combinations and are not paired causal comparisons. The complete configuration-level confusion matrices and metrics are supplied in \texttt{optimizer\_item\_level\_metrics.csv}; item decisions are supplied in \texttt{optimizer\_item\_level\_decisions.csv}.

Tables~\ref{tab:serial-optimization}--\ref{tab:parallel-flash} report the core matrices: 35 Serial source--optimizer cells, 14 Gemini Bulk cells, and 14 Gemini Parallel cells. The 72-configuration item-level file also contains eight mapped auxiliary Serial configurations and one auxiliary Bulk configuration. These auxiliary records are retained in the archive-wide diagnostic outputs. They are not treated as evidence about the study's deployment design. The file excludes records 0 and 18 for the reasons above. Thus, archive size, main-table scope, and item-level scope are related but not identical.
[REV_END]

\begin{table}[H]
\caption{Item-level metric ranges across archived optimizer configurations}
\label{tab:optimizer-item-ranges}
\centering
\begin{tabular}{lrrrrr}
\toprule
\textbf{Mode} & \textbf{Configurations} & \textbf{F1 range} & \textbf{Balanced accuracy range} & \textbf{False-removal range} \\
\midrule
[HROW]Serial & 43 & 0.00--0.72 & 0.50--0.76 & 0--65 \\
[HROW]Bulk & 15 & 0.00--0.66 & 0.49--0.75 & 0--57 \\
[HROW]Parallel & 14 & 0.06--0.57 & 0.39--0.70 & 10--41 \\
\bottomrule
\end{tabular}
\end{table}

[REV_BEGIN]
The TF--IDF baseline provides a non-LLM reference. At threshold 0.50 it produced 631 correct Unique retentions, 145 correct Similar removals, 109 false removals, and 189 missed redundancies. Its Similar-class precision was 0.5709, recall 0.4341, F1 0.4932, and balanced accuracy 0.6434. Lowering the threshold increased recall and false removals; raising it reduced false removals but missed more redundant cases. This trade-off illustrates why deployment thresholds require an independent loss function rather than post-hoc selection on the same Human Oracle.
[REV_END]

\begin{table}[H]
\caption{TF--IDF and cosine-similarity baseline against majority consensus}
\label{tab:tfidf-baseline}
\centering
\begin{tabular}{rrrrrr}
\toprule
\textbf{Threshold} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} & \textbf{Balanced accuracy} & \textbf{False removals} \\
\midrule
[HROW]0.30 & 0.4753 & 0.6916 & 0.5634 & 0.6735 & 255 \\
[HROW]0.50 & 0.5709 & 0.4341 & 0.4932 & 0.6434 & 109 \\
[HROW]0.70 & 0.6224 & 0.1826 & 0.2824 & 0.5663 & 37 \\
\bottomrule
\end{tabular}
\end{table}

[REV_BEGIN]
The earlier 96.52\% value compared only aggregate Unique/Similar counts after choosing the closest serial optimizer separately for each source. It is therefore a post-hoc count-level distributional similarity, not item-level accuracy and not a deployment selection rule. Identical class totals can conceal different item decisions. The new item-level analysis above is the primary evaluation; the count-level value is retained only to explain the earlier report.
[REV_END]

[REV_BEGIN]
A limited same-source comparison is available for the 169-case LLaMa3.2-3B suite because both Gemini-2.5 Flash and Gemini-2.5 Pro appear under all three archived modes. Table~\ref{tab:common-optimizer} reports the resulting counts and TRR values. These are single archived records, not repeated or provider-controlled trials, and therefore provide a descriptive common-optimizer check rather than a causal estimate of strategy effect.
[REV_END]

\begin{table}[H]
\caption{Limited same-source common-optimizer comparison for LLaMa3.2-3B}
\label{tab:common-optimizer}
\centering
\begin{tabular}{llrrrr}
\toprule
\textbf{Optimizer} & \textbf{Mode} & \textbf{Total} & \textbf{Unique} & \textbf{Similar} & \textbf{TRR} \\
\midrule
[HROW]Gemini-2.5 Flash & Serial & 169 & 123 & 46 & 0.272 \\
[HROW]Gemini-2.5 Flash & Bulk & 169 & 135 & 34 & 0.201 \\
[HROW]Gemini-2.5 Flash & Parallel & 169 & 104 & 65 & 0.385 \\
[HROW]Gemini-2.5 Pro & Serial & 169 & 117 & 52 & 0.308 \\
[HROW]Gemini-2.5 Pro & Bulk & 169 & 73 & 96 & 0.568 \\
[HROW]Gemini-2.5 Pro & Parallel & 169 & 126 & 43 & 0.254 \\
\bottomrule
\end{tabular}
\end{table}
"""


PRACTICAL_RESULTS = r"""\subsection{Practical Time and Cost Results}
[REV_BEGIN]
The time comparison is a scenario analysis, not an observed human-timing experiment. For 169 cases, exhaustive review contains $169\times168/2=14{,}196$ unordered pairs. At the assumed 20 seconds per pair, this gives 78.9 hours and should be interpreted only as a theoretical upper bound. The previously stated 13-minute Bulk estimate is withdrawn: the archived Bulk logs contain no elapsed-time field and identify the evaluated operation as a single LLM call, not 13 sequential batches. The archive also contains no measured annotation-time distribution or controlled mode-level runtime study, so no empirical human time saving, labour-productivity effect, or strategy speed ranking is claimed.
[REV_END]

\begin{table}[H]
\caption{Scope of the practical time comparison}
\label{tab:practical-time-analysis}
\centering
\begin{tabular}{p{0.30\linewidth}p{0.25\linewidth}p{0.35\linewidth}}
\toprule
\textbf{Quantity} & \textbf{Reported value} & \textbf{Interpretation} \\
\midrule
[HROW]Exhaustive manual pair review & 78.9 h & Theoretical upper bound from 14,196 pairs at an assumed 20 s per pair; not observed workflow \\
[HROW]Bulk computation & Not reproducibly available & No elapsed-time field; prior 13-batch estimate withdrawn \\
[HROW]Human annotation duration & Not available & No measured timing study was supplied \\
\bottomrule
\end{tabular}
\end{table}
"""


DISCUSSION = r"""\section{Discussion}
[REV_BEGIN]
The results support a limited conclusion: heterogeneous requirements, UML/XML, and source code from the evaluated robotic benchmark can be transformed into traceable, structured pre-execution test artefacts and then filtered for semantic overlap. Reduction magnitude alone is insufficient because it can conceal scenario loss or false removal. SCP should therefore be read with TRR, and the composite SRG should be used only as a compact trade-off summary.

The item-level analysis changes the interpretation of optimizer agreement. Low human inter-rater agreement shows that binary semantic redundancy is not an unambiguous target. Optimizer configurations also vary substantially, and a configuration that matches aggregate counts may still remove different items. The earlier closest-count comparison is thus post-hoc descriptive analysis, not an independently validated optimizer-selection policy. A deployment policy would require a separate validation set and an explicit cost for false removals versus retained redundancy.

Serial, Bulk, and Parallel are operational processing modes with different evidence gaps. Serial provides traceable comparisons but is order-sensitive. The archived Bulk logs describe single-call operations, while over-context partitioning and reconciliation are not documented. Parallel distributes pair evaluations but lacks verified scheduling, conflict, and transitivity handling. The archive is incompletely crossed: mode, optimizer, provider, and run configuration cannot generally be isolated. The LLaMa3.2-3B subset supplies a limited same-source comparison for Gemini Flash and Pro across all three modes, but its single archived records and missing provider settings permit only descriptive comparison. The proposed local-versus-API deployment rationale is likewise not verifiable from the records. The TF--IDF baseline provides a deterministic lexical reference; a future staged system could use lexical or embedding retrieval to generate candidates and reserve an LLM for reranking or adjudication. None of these pre-execution decisions establishes whether a retained or removed test would exercise different code paths or reveal a fault.
[REV_END]
"""


THREATS = r"""\subsection{Threats to Validity}
[REV_BEGIN]
\textbf{Human reference.} Three evaluators labelled the same items, but overall Fleiss' kappa was only 0.1864 and several suites showed near-zero or negative agreement. This ambiguity is part of the empirical result. Majority consensus reduces dependence on one evaluator but remains a reference comparator rather than objective ground truth. Evaluator experience, blinding, and adjudication were not archived.

\textbf{Stochastic validity and reproducibility.} Comprehensive repeated-run experiments are not available. The archive preserves prompts, model identifiers, timestamps, and outputs, but temperatures, seeds, decoding parameters, hardware details, concurrency limits, and model snapshot hashes are not consistently recorded. The results therefore describe single archived outputs rather than robustness distributions; no repeated-run means, variances, confidence intervals, or significance tests are claimed.

\textbf{Experimental-design validity.} Strategy and optimizer are not fully crossed, and provider/backend is not recorded. Serial includes Gemini records. The study-aligned Bulk and Parallel subsets contain only Gemini Flash and Pro. An auxiliary Bulk artifact is not used to infer deployment capability because its backend and role in the study cannot be verified. The limited LLaMa3.2-3B common-optimizer subset reduces, but does not eliminate, confounding because it contains one archived result per configuration and lacks controlled provider and inference settings. Mode-level differences are therefore descriptive rather than causal.

\textbf{Benchmark and external validity.} The evidence comes from one industrially motivated robotic benchmark represented by requirements, UML/XML, and source code. Additional domains, programming languages, system sizes, architectures, and testing contexts are required before broader generalization.

\textbf{Execution validity.} The generated cases were not executed. The study therefore does not establish execution success, code or branch coverage, mutation adequacy, fault detection, behavioural adequacy, or overall test-suite effectiveness. Scenario representation is a property of generated identifiers and descriptions, not executed behaviour. Execution-based validation is a downstream stage outside the present study.

\textbf{Schema and optimization validity.} Title, Description, and Objective form an intermediate pre-execution schema; preconditions, steps, data, expected results, and executable oracles may be embedded in prose rather than mandatory fields. Direct executability is not claimed. Serial selection is order-sensitive. Cross-batch reconciliation for Bulk and conflict/transitivity handling for Parallel could not be verified from the supplied implementation evidence.
[REV_END]
"""


CONCLUSIONS = r"""\section{Conclusions}
[REV_BEGIN]
STLC Manager integrates heterogeneous artefact-to-test generation with pre-execution semantic suite refinement. On the evaluated robotic benchmark, the archived data support conclusions about generation volume, redundancy decisions, scenario-level representation, traceability, and compactness. They do not support claims about executable correctness, coverage, mutation score, fault detection, or general industrial effectiveness.

The revised human-reference analysis is the principal validation result. Three separately completed evaluator files cover the same 1,074 items, but overall inter-rater agreement was low, indicating substantial variability in human redundancy judgements. Majority consensus enabled item-level confusion analysis for the documented 72-configuration subset and exposed false removal directly, while remaining a comparator rather than ground truth. A reproducible offline TF--IDF analysis provides a non-LLM reference; its threshold-dependent false-removal trade-off cautions against selecting a deployment rule on the same reference used for evaluation.

A limited common-optimizer subset for LLaMa3.2-3B compares Gemini-2.5 Flash and Pro under all three archived modes. Because the broader archive is not fully crossed and the subset lacks repeated, provider-controlled runs, it does not support a causal ranking of Serial, Bulk, and Parallel.

Future work should preregister independent optimizer-selection criteria, repeat every model--strategy configuration under recorded inference settings, randomize input order, add cross-batch and transitive reconciliation, and evaluate additional domains and languages. Most importantly, retained and removed tests should be operationalized and executed so that coverage, mutation adequacy, fault detection, invalid-test frequency, and traceability can be compared. Until then, the defensible contribution is a documented pre-execution refinement workflow with reproducible offline analysis components for the evaluated benchmark.
[REV_END]
"""


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement.rstrip() + "\n\n" + text[b:]


def build_marked() -> str:
    text = SOURCE.read_text(encoding="utf-8")
    text = re.sub(
        r"\\abstract\{.*?\}\s*\n\s*% Keywords",
        lambda _m: ABSTRACT + "\n\n% Keywords",
        text,
        count=1,
        flags=re.S,
    )
    text = replace_between(text, r"\section{Introduction}\label{sec1}", r"\section{Literature}\label{sec2}", INTRO)
    text = replace_between(text, r"\section{Literature}\label{sec2}", r"\section{STLC Manager}\label{sec3}", LITERATURE)
    text = replace_between(text, r"\subsubsection{Test Case Optimization}\label{subsubsec-test-case-optimization}", r"\section{Materials and Methods}\label{sec4}", OPTIMIZATION)
    text = replace_between(text, r"\subsection{Human-in-the-Loop Oracle}", r"\subsection{Practical Time and Cost Estimation Method}", HUMAN_METHODS)
    text = replace_between(text, r"\subsection{Human Oracle Results}", r"\subsection{Practical Time and Cost Results}", HUMAN_RESULTS)
    text = replace_between(text, r"\subsection{Practical Time and Cost Results}", r"\section{Discussion}", PRACTICAL_RESULTS)
    text = replace_between(text, r"\section{Discussion}", r"\subsection{Threats to Validity}", DISCUSSION)
    text = replace_between(text, r"\subsection{Threats to Validity}", r"\section{Conclusions}", THREATS)
    text = replace_between(text, r"\section{Conclusions}", r"\authorcontributions", CONCLUSIONS)

    # Correct reviewer-identified numerical/textual inconsistencies without guessing.
    text = text.replace("GPT-OSS-20B      & GPT-OSS-20B      & 137 & 88  & 57", "GPT-OSS-20B      & GPT-OSS-20B      & 137 & 80  & 57")
    text = text.replace("for most source models", "for three of the seven source models in the Bulk comparison")
    text = text.replace(
        "Its \\(TRR\\) values are higher for three of the seven source models in the Bulk comparison (Table~\\ref{tab:parallel-flash}).",
        "Its \\(TRR\\) values are higher for all seven source models in the Parallel comparison (Table~\\ref{tab:parallel-flash}).",
    )
    text = text.replace("in most scenarios", "in several stored configurations")
    text = text.replace("implements a sophisticated analytical framework", "implements a comparison workflow")
    text = text.replace("The system generates a comprehensive comparison report", "The system generates a comparison report")
    text = text.replace(
        "The proportional gain shows how much a model improves when its test set is optimized. This metric compares the highest and lowest comparison counts of each model and expresses the reduction as a ratio. The gain is calculated using the following formula, which measures how strongly an optimizer reduces redundant comparisons.",
        "[REV_BEGIN]\nThe cross-configuration comparison-count spread compares the highest and lowest archived comparison counts associated with each source model. Because these extrema may come from different optimizer configurations and source-suite conditions, the ratio is a descriptive heterogeneity measure; it is not a within-test-set causal gain, cost reduction, or effectiveness estimate. The spread is calculated as follows.\n[REV_END]",
    )
    text = text.replace(r"\mathrm{Gain}", r"\mathrm{Spread}")
    text = text.replace(
        "Table~\\ref{tab:serial-gain} presents the proportional gain for each model, showing the relative improvement after optimization. These values help identify which models benefit the most from external optimization and which ones maintain more stable internal behavior.",
        "[REV_BEGIN]\nTable~\\ref{tab:serial-gain} presents this cross-configuration spread. The values indicate variation among archived comparison counts only and should not be used to rank optimizer effectiveness.\n[REV_END]",
    )
    text = text.replace("Gain Calculation Table for Serial Optimization Method", "Cross-Configuration Comparison-Count Spread for Serial Optimization")
    text = text.replace("Gain (\\%)", "Spread (\\%)")
    text = text.replace(
        "The results indicate clear differences among the models. Qwen3-Coder-30B achieves the highest proportional gain (57\\%), meaning it shows the strongest cost reduction and the greatest response to optimization. LLaMa3.2-3B and Codestral-22B follow with gains of 52\\%, which suggests that they also receive substantial improvement. In contrast, LLaMa3.3-70B and GPT-OSS-20B present smaller gains of 49\\% and 47\\%. These observations show that models with high internal redundancy demonstrate larger relative improvements, while more consistent models show lower proportional gains because they begin with fewer redundant structures.",
        "[REV_BEGIN]\nThe archived comparison-count spread ranges from 47\\% to 57\\%. Qwen3-Coder-30B has the largest spread (57\\%), followed by LLaMa3.2-3B and Codestral-22B (52\\%); LLaMa3.3-70B and GPT-OSS-20B have spreads of 49\\% and 47\\%. Since each maximum and minimum may arise from different optimizer configurations, these values describe cross-configuration variability and do not establish that one model benefits more from optimization.\n[REV_END]",
    )
    text = re.sub(r"[Tt]he experiments were repeated[^.]*\.", "The archived results represent the stored outputs available for each configuration.", text)

    # Remove legacy product-capability language that does not describe the
    # evaluated Smart Selection archive.
    text = re.sub(
        r"The test case optimization behavior of different large language models is examined under the same testing conditions\..*?continuous improvement of test case generation processes\.",
        lambda _m: "[REV_BEGIN]\nThis section reports the archived semantic optimization results. The evaluated Smart Selection configurations classify generated test cases as retained (Unique) or removed (Similar) using the semantic comparison procedure described in Section~\\ref{subsubsec-test-case-optimization}. The decision uses Title, Description, and Objective and the stored Boolean \\texttt{is\\_same} output. Reported quantities are Total, Unique, Similar, TRR, recorded Serial comparison count, and scenario-identifier representation metrics. The experiment did not compute completeness, expected-result, precondition, test-step, post-condition, quality-index, or execution-adequacy scores.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        "This structure allows a fair comparison because each model works on the same inputs and the same workflow. The main metric in this scenario is the Test Redundancy Ratio (TRR).",
        "[REV_BEGIN]\nWhere a table row shares a source suite, its total input set is the same; however, the broader archive is not fully crossed and does not establish a controlled strategy comparison. The principal descriptive metric is the Test Redundancy Ratio (TRR).\n[REV_END]",
    )
    text = text.replace(
        "This section describes the experimental methodology used to evaluate the proposed framework. The evaluation assesses prompt-guided model-to-test transformation and LLM-based test case optimization across heterogeneous software artefacts under a controlled experimental setting.",
        "[REV_BEGIN]\nThis section describes the archived evaluation of prompt-guided artefact-to-test transformation and LLM-mediated test case optimization. Inputs and outputs are traceable within the supplied archive, but incomplete strategy crossing and missing inference metadata preclude a claim of full experimental control.\n[REV_END]",
    )
    text = text.replace(
        "The benchmark examines how large language models perform test case optimization under a strict serial method. In this strategy, each test case is evaluated sequentially through explicit pairwise semantic comparisons against previously retained representative cases. The procedure follows the Smart Selection algorithm and may terminate comparisons early when a semantic match is identified; therefore, the realized comparison count can be lower than the theoretical pairwise maximum. This sequential comparison process enables detailed analysis of how redundancy is detected, how representative test cases are retained, and how different optimizers behave under a controlled pairwise evaluation setting. The evaluation uses multiple source test sets and several optimizers, providing structured measurements that include the numbers of unique cases, similar cases, and realized semantic comparisons. Because the serial method preserves explicit pairwise reasoning while processing comparisons sequentially, it provides a traceable reference for analysing redundancy-reduction behaviour and computational cost in LLM-based test optimization.",
        "[REV_BEGIN]\nThe Serial records process each test case in input order through explicit semantic comparisons against previously retained representatives. The procedure may stop after the first positive match, so the realized comparison count can be below the exhaustive pairwise maximum. The archive supports analysis of retained and removed counts and recorded comparisons, but not a controlled estimate of computational cost or intrinsic optimizer capability.\n[REV_END]",
    )
    text = text.replace(
        "Table~\\ref{tab:serial-optimization} presents the raw optimization results for each Source--Optimizer pair. Each row shows Total (\\(T\\)), Unique (\\(U\\)), Similar (\\(S\\)), and Comparison Count (\\(C\\)), enabling direct observation of how many test cases were preserved, how many were removed, and how many comparisons were required. Since all optimizers run in Individual mode, comparison counts remain high, reflecting deep pairwise exploration. This table forms the structural backbone of the analysis.",
        "[REV_BEGIN]\nTable~\\ref{tab:serial-optimization} presents the 35-cell core Serial matrix. Each cell shows Total, Unique, Similar, and recorded Comparison Count. Eight additional mapped auxiliary Serial configurations are included only in the item-level analysis files.\n[REV_END]",
    )

    # Bound architectural descriptions and standards language to what was
    # actually archived or evaluated.
    text = text.replace("under a unified and controlled testing workflow", "within one archived workflow")
    text = text.replace("the controlled execution of analysis, generation, and optimization stages", "the coordinated execution of analysis, generation, and optimization stages")
    text = text.replace("different reasoning strengths in a controlled and traceable manner", "different configured models within a traceable workflow")
    text = text.replace("to ensure the systematic verification and validation of software systems", "to organize systematic verification and validation activities")
    text = text.replace("aims to improve traceability between requirements and tests, enable early defect detection, and support structured quality assurance", "is designed to support traceability between requirements and tests and structured review")
    text = text.replace("correctness, quality, and compliance with defined rules", "potential correctness issues, maintainability concerns, and alignment with user-supplied rules")
    text = text.replace("quality concerns, and standard violations", "maintainability concerns, and potential deviations from supplied rules")
    text = text.replace("in alignment with international quality standards such as ISTQB and Model-Based Systems Engineering principles", "using terminology and concepts informed by ISTQB-oriented testing practice and model-based systems engineering")
    text = text.replace("which promotes both high modularity and scalable performance", "which separates routing, service logic, and utility layers")
    text = text.replace("offers significant operational benefits. The robust prompt management infrastructure", "supports configurable operation. The prompt management infrastructure")
    text = text.replace("to ensure broad interoperability", "to support multiple documented input and output formats")
    text = text.replace("to ensure simplicity, flexibility, and ease of reuse", "to support downstream reuse")
    text = text.replace("while maintaining compliance with ISTQB standards", "while using ISTQB-oriented testing terminology")
    text = text.replace("to improve test accuracy and depth", "to encourage more structured prompt content")
    text = text.replace("construction of precise and effective prompts while preserving methodological consistency", "construction of structured prompts while retaining their configuration metadata")
    text = text.replace("ensures consistency, traceability, and compliance with international testing standards", "supports structured representation and identifier-level traceability")
    text = text.replace("automated generation of comprehensive test cases", "automated generation of test-case descriptions")
    text = text.replace(
        "By optimizing the generated test cases before execution, the framework aims to reduce review effort and potential downstream testing cost while maintaining representation of the generated scenarios and artefact-derived testing objectives.",
        "The pre-execution step reduces the number of retained cases and records scenario-identifier representation; the archive does not measure review effort, downstream cost, or execution outcomes.",
    )
    text = text.replace(
        "These models were selected to cover complementary requirements related to long-context processing, code-aware reasoning, semantic depth, and stable optimization rather than relying on a single general-purpose LLM.",
        "The configured pool spans several model families and includes models described for long-context or code-oriented use; the present archive does not validate comparative reasoning depth or optimization stability.",
    )
    text = text.replace(
        "This design improves maintainability and extensibility while enabling shared services, multi-LLM orchestration, and standardized prompt frameworks to support a coherent end-to-end testing environment. All experimental artefacts, including the prompting materials, are available in the project's public GitHub repository \\citep{bib68}.",
        "This design separates services, model configuration, and prompt handling within the application. The supplied study archive contains the prompts and experimental records used for the reported analyses \\citep{bib68}.",
    )
    text = text.replace(
        "The Environment Setup module of the STLC Manager systematically derives clear and consistent test environments from existing project information by treating environment-related artefacts as structured inputs rather than relying on informal notes or manual setup steps. It analyzes configuration details, requirements, and technology descriptions to identify required tools, libraries, and compatibility conditions, and produces a comprehensive, well-structured environment specification in JSON format that supports documentation and automated testing workflows.",
        "The Environment Setup module prompts the selected model to derive a structured environment description from project information, configuration details, requirements, and technology descriptions. Its JSON output can document proposed tools, libraries, and compatibility conditions; environment correctness or automated deployment was not evaluated in this study.",
    )
    text = text.replace(
        "Its implementation utilizes a transformation pipeline architecture that maintains the separation of routing, service logic, and utility layers, which separates routing, service logic, and utility layers.",
        "Its transformation pipeline separates routing, service logic, and utility layers.",
    )
    text = text.replace(
        "A defining feature of the module's methodology is the systematic application of formal test design techniques.",
        "The prompt templates reference established test design concepts, but adherence to a formal test-design standard was not independently validated.",
    )
    text = text.replace(
        "The Test Scenario Generation tab presents a complete and structured process for generating software test scenarios. This process uses an intelligent workflow that combines automated prompt generation with user-controlled customization.",
        "The Test Scenario Generation tab combines automated prompt construction with user-configurable fields for generating software test-scenario descriptions.",
    )
    text = text.replace(
        "Because the XML document exceeded the context capacity configured for the smaller generation model, Qwen2.5-1M was selected to process the complete artefact without truncation.",
        "The archived XML result used Qwen2.5-1M. The original XML file and production switching configuration are not included in the supplied revision package; therefore, the exact context threshold, fallback rule, truncation behaviour, and previously stated structural element counts cannot be independently verified.",
    )
    text = text.replace(
        "The XML artefact represents the structurally richest input used in the evaluation, containing 11 classes, 10 associations, more than 30 attributes, and 6 operations.",
        "The XML artefact provides a structured model input for the archived generation workflow.",
    )
    text = text.replace(
        "The requirements specification represents the behavioural and quality expectations of the system and contains 16 requirements, consisting of 8 functional and 8 non-functional requirements. Requirement-based generation was analysed according to the number of scenarios and test cases produced from the same requirements document.",
        "The requirements specification represents behavioural and non-functional expectations. Because the original requirements file is not included in the supplied revision package, the analysis reports only the archived scenario and test-case counts generated from that common document.",
    )
    text = text.replace(
        "For the XML artefact specifically, Qwen2.5-1M generated 49 test cases from a model containing 11 classes, 10 associations, more than 30 attributes, and 6 operations. These structural characteristics are reported to contextualize the complexity of the input rather than to establish a deterministic relationship between model size and the expected number of generated test cases.",
        "For the XML artefact specifically, the archived Qwen2.5-1M result contains 7 scenarios and 49 test cases. No deterministic relationship between input structure and the expected number of generated cases is claimed.",
    )
    text = text.replace(
        "The ProductDetection source code contains two distance-sensor inputs, one gripper-state condition, and three possible output classifications: NONE, SODA, and WATER. These elements define a compact but non-trivial decision structure that enables different LLMs to generate multiple test variations from the same implementation logic. Across the evaluated models, the number of source-code-derived test cases ranged from 38 to 64. This range is treated as an empirical observation of model-dependent generation behaviour rather than as evidence of a predefined theoretical adequacy interval.",
        "Across the archived ProductDetection source-code configurations, the number of generated test cases ranged from 35 to 64. The original source file is not included in the supplied revision package, so previously stated counts of inputs, conditions, and output classes are not retained as independently verified dataset characteristics. The observed case-count range is descriptive and is not an execution-coverage measure.",
    )
    text = text.replace(
        "The requirements document contains 8 functional and 8 non-functional requirements covering both behavioural functionality and quality-related constraints. The evaluated models generated between 36 and 64 test cases from this common requirements specification. The variation in test-suite size reflects differences in how the models decompose requirements into individual testing objectives and behavioural variations. Because a single requirement may legitimately lead to multiple test cases, no fixed upper bound on the number of generated cases is assumed in this analysis.",
        "The archived requirements-based configurations contain between 36 and 64 generated test cases. The variation describes how the stored outputs decompose a common input into testing objectives; no fixed adequacy bound or verified requirement-to-case ratio is inferred.",
    )
    text = text.replace(
        "The requirements specification contains eight functional and eight non-functional requirements covering product detection, object handling, robot movement, collision avoidance, reliability, responsiveness, modularity, and verification support. The source code implements product detection through threshold-based interpretation of two distance sensors combined with gripper-state conditions, resulting in multiple logical decision paths and product classification rules. The UML model formally defines system components, state representations, associations, and synchronization mechanisms that coordinate interactions among modules such as RobotController, GripperTool, ProductDetection, and RobotSynch.",
        "The archived prompts describe requirements, source-code behaviour, and UML/XML structures related to product detection, object handling, robot coordination, and safety constraints. Because the original source artefacts are not included in the supplied revision package, exact requirement, sensor, branch, and structural-element counts are not asserted here.",
    )
    text = text.replace(
        "This makes the Test Redundancy Ratio a clear mathematical tool for comparing different LLMs under the same task.",
        "TRR is therefore reported as a descriptive proportion for each archived configuration.",
    )
    text = text.replace(
        "To provide a comprehensive evaluation, descriptive statistics of the SRG values obtained from all 35 optimization configurations are presented in Table~\\ref{tab:srg-stats}.",
        "Descriptive statistics of the SRG values for the 35 core Serial configurations are presented in Table~\\ref{tab:srg-stats}.",
    )
    text = text.replace(
        '"Description": "This test case ensures that the RobotController class initializes correctly using valid inputs for its attributes."',
        '"Description": "Verify RobotController initialization using valid attribute inputs."',
    )

    # Replace unsupported causal, stability, deployment, and runtime interpretations
    # with statements bounded by the archived evidence.
    text = text.replace(
        "Although comparison density is not the main metric in this scenario, it explains different behaviors among models that have similar Test Redundancy Ratio values. The process is repeated multiple times for each model in order to observe stability. If the Test Redundancy Ratio remains similar in each run, the variance is low. The final comparison focuses on how strong each model performs in optimization. A model with a high Test Redundancy Ratio removes many redundant cases and generates a cleaner final set. A model with a low Test Redundancy Ratio keeps most of the original cases, which reduces the risk of information loss but increases execution cost.",
        "[REV_BEGIN]\nComparison density and Test Redundancy Ratio describe different properties of each archived configuration. The archive contains one stored result per reported configuration rather than repeated trials. A high TRR means that a larger fraction was classified as Similar and removed; a low TRR means that a smaller fraction was removed. Neither value alone establishes test quality, information preservation, stability, or execution cost.\n[REV_END]",
    )
    text = text.replace(
        "Modern test automation systems require reliable and scalable methods for reducing large sets of generated test cases. To understand how different large language models behave under different operational constraints, this work examines three optimization strategies: Serial Optimization, Bulk Optimization, and Parallel Optimization. Each method represents a different view of how LLMs process redundancy, manage context, and perform reasoning over structured test data. Together, these three approaches create a complete benchmarking framework that shows the strengths, weaknesses, and practical limits of LLM-based test case optimization. The following sections present these methods in detail, beginning with the Serial Optimization approach.",
        "[REV_BEGIN]\nThe following results describe the Serial, Bulk, and Parallel configurations preserved in the archive. Because optimizer sets and deployment metadata differ across modes, the tables characterize stored redundancy decisions rather than a complete or causal benchmark of strategy effects.\n[REV_END]",
    )
    text = text.replace(
        "The results show that different source models generate different redundancy structures and that optimizers respond differently when operating serially. Models with large output sets, such as LLaMa3.3-70B and Qwen3-Coder-30B, naturally produce higher comparison counts, since larger sets create more pairwise combinations. The values of \\(U\\) and \\(S\\) highlight substantial differences in redundancy characteristics. LLaMa3.3-70B produces highly consistent test suites with minimal redundancy, whereas Qwen3-Coder-30B exhibits a considerably higher degree of semantic overlap among the generated test cases. An additional observation concerns the optimization characteristics of LLaMa3.2-3B during self-optimization. Although the model generates test sets with non-trivial internal similarity, it shows limited effectiveness in identifying these similarities, which leads to the retention of a larger number of redundant test cases. This behaviour becomes clearer when stronger optimizers remove considerably more redundancy from LLaMa3.2-3B outputs than the model removes from itself. These differences demonstrate that test-set size alone does not determine quality; internal structural consistency and semantic redundancy detection capability play a key role in overall optimization behaviour.",
        "[REV_BEGIN]\nThe Serial records show different Unique, Similar, and comparison counts across source/optimizer combinations. Larger input suites permit more candidate pairs, but the observed counts also depend on ordered decisions and optimizer configuration. These descriptive differences do not establish source-model consistency, optimizer strength, or test quality.\n[REV_END]",
    )
    text = re.sub(
        r"Figure~\\ref\{fig:figure10\} reports the Test Redundancy Ratio.*?distinct internal reasoning patterns when generating test behaviours\.",
        lambda _m: "[REV_BEGIN]\nFigure~\\ref{fig:figure10} reports TRR, the observed proportion classified as Similar and removed in each stored Serial configuration. Differences across configurations describe decision outcomes only; they do not establish that a suite is clean, that one optimizer reasons better, or that removed cases are behaviourally unnecessary.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"Figure~\\ref\{fig:figure11\} presents the Comparison Density.*?strict serial conditions\.",
        lambda _m: "[REV_BEGIN]\nFigure~\\ref{fig:figure11} presents Comparison Density, the fraction of the theoretical pair space represented by the recorded Serial comparisons. High or low CD reflects the archived ordered stopping behaviour; it is not evidence of model strength, convergence quality, or semantic correctness.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        "The three tables demonstrate that the Individual-Individual configuration reveals the intrinsic optimization patterns, redundancy structures, and comparison behaviours of each model. The serial method therefore serves as a clear and consistent baseline for evaluating LLM-based test case optimization, while also exposing the relative weaknesses of smaller models such as LLaMa3.2-3B, whose semantic similarity detection and redundancy classification remain limited compared with more advanced models.",
        "[REV_BEGIN]\nThe three tables summarize the archived Serial outcomes. They provide a traceable descriptive reference but do not reveal intrinsic model properties or support claims about relative model weakness.\n[REV_END]",
    )
    text = re.sub(
        r"The benchmark explores how large language models perform test case optimization when the Bulk Optimization method is used\..*?under the Bulk Optimization strategy\.",
        lambda _m: "[REV_BEGIN]\nThe Bulk tables report the proportion of cases classified as Similar in the archived grouped evaluations. Their logs label the operation as \\texttt{Single LLM Call for All Test Cases}; no pairwise comparison count is recorded. Behaviour beyond the archived input sizes, including context-window partitioning, cannot be verified.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"The Bulk Optimization results show that both Gemini-2\.5 Flash.*?avoiding input truncation for larger test suites\.",
        lambda _m: "[REV_BEGIN]\nThe archived Bulk records for Gemini Flash and Pro report grouped single-call evaluations. The supplied evidence does not document sequential batching, context-overflow behaviour, or cross-batch reconciliation. Parallel records are labelled \\texttt{GeminiBatchAPI\\_Adaptive}, but exact scheduling and concurrency limits are also unavailable.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        "Gemini-2.5 Flash exhibits different levels of redundancy reduction across the evaluated source test suites. For the test suites generated by Gemini2.5-Pro, Gemini2.5-Flash, and LLaMa3.3-70B, relatively low TRR values indicate that a smaller proportion of cases was classified as semantically redundant. In contrast, the Qwen3-Coder-30B-generated test suite exhibits a higher TRR, indicating that a larger proportion of cases was classified and removed as semantically redundant under the same Bulk Optimization configuration. The cases within each bulk batch are evaluated jointly rather than through explicit pairwise iteration, allowing the optimizer to perform context-aware semantic redundancy classification. Table~\\ref{tab:bulk-pro} presents the Bulk Optimization results obtained using Gemini-2.5 Pro.",
        "[REV_BEGIN]\nThe archived Gemini-2.5 Flash Bulk records have different TRR values across source suites. Lower values mean that a smaller fraction was classified as Similar; higher values mean that a larger fraction was so classified. The logs identify each evaluated suite as a single-call grouped operation, not a verified sequence of batches. Table~\\ref{tab:bulk-pro} reports the corresponding Gemini-2.5 Pro records.\n[REV_END]",
    )
    text = text.replace(
        "Gemini-2.5 Pro generally keeps more unique test cases compared to Flash, resulting in lower \\(TRR\\) values for three of the seven source models in the Bulk comparison (Table~\\ref{tab:bulk-pro}). This indicates a more conservative and diversity-preserving strategy. However, when a source model has very high redundancy, such as LLaMa3.2-3B, Pro also applies strong reduction, leading to a high \\(TRR\\) value. Like Flash, Pro performs Bulk Optimization by jointly evaluating groups of test cases within shared semantic contexts without explicit pairwise iteration.",
        "[REV_BEGIN]\nGemini-2.5 Pro has lower TRR than Flash for three of the seven source suites in the archived Bulk comparison (Table~\\ref{tab:bulk-pro}). The LLaMa3.2-3B record instead has a higher Pro TRR. These proportions do not establish preservation quality or optimizer strength; the logs describe grouped single-call decisions without explicit pairwise counts.\n[REV_END]",
    )
    text = re.sub(
        r"The benchmark examines how test case optimization behaves when the Parallel Optimization method is used\..*?under parallel reasoning\.",
        lambda _m: "[REV_BEGIN]\nThe Parallel tables report archived pairwise-classification outcomes labelled \\texttt{GeminiBatchAPI\\_Adaptive}. The archive preserves comparison decisions but not the exact request grouping, concurrency limit, merge rule, or transitive-conflict policy. TRR therefore describes the fraction classified as Similar under each stored configuration.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"The results show that Gemini-2\.5 Pro, when used as a parallel optimizer.*?stronger redundancy reduction observed for Gemini-2\.5 Flash\.",
        "[REV_BEGIN]\nFor the archived Parallel configurations, Gemini-2.5 Pro and Flash produce different Unique, Similar, and TRR values across source suites. These values describe classification proportions; they do not establish conservatism, optimizer strength, or retained-suite quality.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"Gemini-2\.5 Flash produces stronger reductions in parallel mode compared to Pro\..*?reduce test-suite size before downstream execution\.",
        "[REV_BEGIN]\nIn the archived Parallel records, Flash has higher TRR than Pro for all seven source suites, meaning that it classified a larger fraction as Similar. Without execution evidence, this difference should not be interpreted as better reduction or safer preparation for downstream execution.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"The parallel results show that Gemini-2\.5 Pro keeps more unique cases.*?preserves the behavioural representation of the original test suites\.",
        "[REV_BEGIN]\nAcross the archived Parallel tables, Pro retains more cases and has lower TRR, while Flash classifies more cases as Similar. The records do not expose scheduling, request-concurrency, or reconciliation details. The subsequent analysis therefore reports scenario identifiers represented after reduction without treating either mode as causally superior.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"Although redundancy reduction is a primary objective.*?scenario representation efficiency\.",
        "[REV_BEGIN]\nTRR reports the fraction removed, while Scenario Coverage Preservation (SCP) reports whether scenario identifiers represented before optimization remain represented afterward. Scenario Representation Gain (SRG) is a composite of SCP and TRR and contains no independent information. These are pre-execution representation measures, not measures of optimization quality, behavioural coverage, or fault-detection effectiveness.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"While the Test Redundancy Ratio.*?metric is calculated as follows\.",
        "[REV_BEGIN]\nTRR alone does not show whether scenario identifiers present before filtering remain represented afterward. SCP records that identifier-level representation. It does not measure executed behavioural coverage or establish that retained tests are correct or effective. SCP is calculated as follows.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"The experimental results demonstrate that the proposed Smart Selection mechanism preserves scenario-level coverage.*?Qwen3-Coder-30B\.",
        lambda _m: "[REV_BEGIN]\nAcross the archived configurations, mean SCP is 98.40\\% and the median is 100.00\\%; six configurations have partial scenario-identifier loss, with a minimum of 87.50\\%. These single archived outputs describe representation outcomes and do not establish repeated-run stability or causal dependence on the source model.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        "In the equation, \\(S_{\\mathrm{before}}\\) denotes the number of unique test scenarios represented before optimization. \\(S_{\\mathrm{after}}\\) denotes the number of unique test scenarios that remain represented after optimization. An \\(SCP\\) value of 100\\% indicates that every generated scenario is still represented by at least one optimized unique test case, whereas values below 100\\% indicate that one or more scenarios were completely removed during optimization. To evaluate the robustness of the proposed Smart Selection mechanism, \\(SCP\\) was computed for all combinations of scenario generation models and optimization models in Figure~\\ref{fig:figure12}.",
        "[REV_BEGIN]\nIn the equation, the before and after terms denote the numbers of distinct scenario identifiers represented before and after filtering. An SCP value of 100 percent means every pre-filter identifier remains represented by at least one retained case; lower values mean at least one identifier is absent afterward. Figure~\\ref{fig:figure12} reports SCP for the archived combinations, without implying repeated-run robustness or executed coverage.\n[REV_END]",
    )
    text = text.replace(
        "To provide a more comprehensive evaluation, descriptive statistics of the Scenario Coverage Preservation metric are presented in Table~\\ref{tab:scp-stats}.",
        "Descriptive statistics of SCP are presented in Table~\\ref{tab:scp-stats}.",
    )
    text = re.sub(
        r"While the Scenario Coverage Preservation \(SCP\) metric verifies whether the generated test scenarios remain represented after optimization,.*?The Scenario Representation Gain \(SRG\) is calculated as follows\.",
        lambda _m: "[REV_BEGIN]\nSCP and TRR can be combined to express the ratio of scenario identifiers per retained case relative to the corresponding pre-filter ratio. This composite is called Scenario Representation Gain (SRG). Because SRG is algebraically determined by SCP and TRR, it is a descriptive convenience rather than an independent measure, and it does not establish behavioural efficiency or quality. SRG is calculated as follows.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        "\\(SRG > 1\\) & Scenario representation becomes more efficient after optimization. \\\\",
        "\\(SRG > 1\\) & Higher scenario-identifiers-per-case ratio than before filtering. \\\\",
    )
    text = text.replace(
        "\\(SRG = 1\\) & No improvement in representation efficiency. \\\\",
        "\\(SRG = 1\\) & Same scenario-identifiers-per-case ratio as before filtering. \\\\",
    )
    text = text.replace(
        "\\(SRG < 1\\) & Optimization reduces representation efficiency. \\\\",
        "\\(SRG < 1\\) & Lower scenario-identifiers-per-case ratio than before filtering. \\\\",
    )
    text = re.sub(
        r"The results demonstrate that the optimization process consistently improves scenario representation efficiency.*?compactness of the optimized test suite\.",
        "[REV_BEGIN]\nThe archived SRG values have mean 1.5362, median 1.50, standard deviation 0.4404, minimum 0.9353, and maximum 3.1607. Because SRG is algebraically determined by SCP and TRR, it is reported only as a compact descriptive summary; it does not independently demonstrate quality, stable improvement, or behavioural effectiveness.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )

    text = re.sub(
        r"Although the previous sections evaluate the semantic quality.*?whereas Human Oracle review represents a more realistic expert screening process\.",
        "[REV_BEGIN]\nThe practical-time calculation is retained only as a hypothetical upper-bound scenario. For 169 cases, exhaustive review contains 14,196 unordered pairs; at an assumed 20 seconds per pair, this equals 78.9 hours. Neither the 20-second assumption nor annotation duration was observed. The prior 13-batch, 13-minute Bulk estimate conflicts with the archived single-call labels and lacks elapsed-time evidence, so it is withdrawn. No empirical human-effort saving or mode-level runtime comparison is claimed.\n[REV_END]",
        text,
        count=1,
        flags=re.S,
    )

    text = text.replace(
        "These inputs are combined to form a structured master prompt, which is then sent to the configured provider: LM Studio for supported locally deployed models or the Google Gemini API for supported Gemini models.",
        "These inputs are combined to form a structured master prompt and sent through a configured model route. The application description identifies LM Studio and Google Gemini routes, but the archived experiment records do not preserve a provider/backend field; this architecture description therefore does not establish which route served any particular reported run.",
    )

    # Clarify that token switching cannot be reproduced from the supplied archive.
    text = text.replace(
        "Selected services may apply a context-length-based fallback when the configured model cannot accommodate the input, but the current implementation does not perform general-purpose automatic model selection based on task suitability or output stability.",
        "The supplied revision archive does not contain the production configuration needed to verify an exact context threshold, fallback model, or switching scope. Accordingly, no token-aware switching result is evaluated here, and model-dependent effects of any deployment-specific fallback remain a reproducibility limitation.",
    )
    text = text.replace(
        "The system employs a token-aware architecture, meaning that when document content becomes large (more than 4,000 tokens), it dynamically switches to a high-capacity model to maintain performance and reliability. Users can upload and select relevant files, and the system automatically analyzes them to generate context-aware prompts tailored to the project’s requirements.",
        "The supplied archive does not contain production configuration evidence for the previously described 4,000-token switching rule. The revised study therefore does not claim a verified automatic threshold or fallback model; any deployment-specific model switching may introduce consistency effects that require separate evaluation.",
    )

    # Insert the algebraic interpretation and worked examples immediately after the SRG equation.
    needle = r"\end{equation}" + "\n\nIn the equation, \\(S_{\\mathrm{before}}\\) denotes"
    addition = r"""\end{equation}

[REV_BEGIN]
Because $TRR=1-N_{\mathrm{unique}}/N_{\mathrm{generated}}$ and $SCP=S_{\mathrm{after}}/S_{\mathrm{before}}$, SRG is the composite $SRG=SCP/(1-TRR)$ when SCP is expressed as a fraction. It contains no information independent of SCP and TRR; its purpose is only to summarize their trade-off. For example, 10 scenarios represented by 100 tests give SRG=1.0 when all 100 tests and all scenarios remain; retaining 20 tests but only 6 scenarios gives SCP=0.60, TRR=0.80, and SRG=3.0, showing that a high SRG can conceal scenario loss; retaining 50 tests and all 10 scenarios gives SCP=1.00, TRR=0.50, and SRG=2.0, a balanced reduction with full representation.
[REV_END]

In the equation, $S_{\mathrm{before}}$ denotes"""
    if needle in text:
        text = text.replace(needle, addition, 1)
    return text


def simplify_language(text: str) -> str:
    """Use shorter sentences and avoid semicolons and em dashes in prose."""
    replacements = {
        "Three separately completed evaluator files contain labels for the same 1,074 generated test cases; majority voting produced 740 Unique and 334 Similar decisions.":
            "Three separately completed evaluator files contain labels for the same 1,074 generated test cases. Majority voting produced 740 Unique and 334 Similar decisions.",
        "The study evaluates semantic redundancy reduction, scenario-level representation, compactness, and artefact traceability before execution; it does not establish executability, coverage, mutation adequacy, or fault detection.":
            "The study evaluates semantic redundancy reduction before execution. It also evaluates scenario-level representation, compactness, and artefact traceability. It does not establish executability, coverage, mutation adequacy, or fault detection.",
        "RQ2 describes semantic redundancy reduction and scenario representation under the archived Serial, Bulk, and Parallel configurations; it does not treat mode as an isolated causal factor.":
            "RQ2 describes semantic redundancy reduction and scenario representation under the archived Serial, Bulk, and Parallel configurations. It does not treat mode as an isolated causal factor.",
        "The contributions are: (1) a unified LLM-supported pipeline linking heterogeneous software artefacts to structured pre-execution test artefacts; (2) a descriptive analysis of archived Serial, Bulk, and Parallel configurations, including their incomplete strategy--optimizer crossing; (3) item-level analysis against three separately completed evaluator files, including agreement coefficients, confusion matrices, precision, recall, F1, balanced accuracy, and false-removal counts; (4) an offline lexical baseline that uses the archived test cases; and (5) an explicit separation between semantic suite refinement and downstream execution-based validation.":
            "The study makes five contributions. First, it links different software artefacts to structured pre-execution test artefacts in one LLM-supported pipeline. Second, it describes the archived Serial, Bulk, and Parallel configurations and their incomplete strategy--optimizer crossing. Third, it compares item-level results with three separately completed evaluator files. This analysis reports agreement coefficients, confusion matrices, precision, recall, F1, balanced accuracy, and false-removal counts. Fourth, it adds an offline lexical baseline based on the archived test cases. Fifth, it separates semantic suite refinement from later execution-based validation.",
        "STLC organizes requirements analysis, planning, test design, execution, and reporting; the present work addresses only artefact analysis, test generation, and pre-execution refinement":
            "STLC organizes requirements analysis, planning, test design, execution, and reporting. The present work addresses only artefact analysis, test generation, and pre-execution refinement",
        "Search-based, coverage-guided, and mutation-oriented approaches address downstream execution properties \\citep{bib34,bib35,bib39}; those outcomes are outside the evidence available in the present archive.":
            "Search-based, coverage-guided, and mutation-oriented approaches address downstream execution properties \\citep{bib34,bib35,bib39}. The present archive does not include those outcomes.",
        "Lexical methods such as TF--IDF provide inexpensive and deterministic similarity scores; embedding retrieval can improve semantic candidate discovery; reranking or LLM comparison can then apply more detailed criteria to a smaller candidate set.":
            "Lexical methods such as TF--IDF provide inexpensive and deterministic similarity scores. Embedding retrieval can improve the search for semantic candidates. Reranking or LLM comparison can then apply more detailed criteria to a smaller candidate set.",
        "A retrieval--reranking separation has been shown to improve efficiency and traceability in another high-stakes document-matching setting \\citep{bib70}; we cite it as an architectural analogy rather than direct evidence for test optimization.":
            "A retrieval--reranking separation improved efficiency and traceability in another high-stakes document-matching setting \\citep{bib70}. We cite it as an architectural analogy, not as direct evidence for test optimization.",
        "Rather than implementing a rule-based model transformation engine, STLC Manager provides a prompt-guided artefact interpretation and test generation environment in which heterogeneous software artefacts, including requirements, UML/XML models, and source code, are supplied as contextual inputs to Large Language Models (LLMs).":
            "STLC Manager does not use a rule-based model transformation engine. It provides a prompt-guided environment for artefact interpretation and test generation. Requirements, UML/XML models, and source code serve as context for Large Language Models (LLMs).",
        "In Figure~\\ref{fig:figure2}, code review and requirement analysis are modeled as SDLC activities that are relevant for testing and are therefore shown under “SDLC (Relevant Phases for Testing),” indicating that their outputs are consumed by the STLC Manager without redefining them as STLC phases.":
            "Figure~\\ref{fig:figure2} shows code review and requirement analysis as SDLC activities that support testing. Their outputs are used by STLC Manager. The figure does not redefine them as STLC phases.",
        "The pre-execution step reduces the number of retained cases and records scenario-identifier representation; the archive does not measure review effort, downstream cost, or execution outcomes.":
            "The pre-execution step reduces the number of retained cases. It also records scenario-identifier representation. The archive does not measure review effort, downstream cost, or execution outcomes.",
        "The configured pool spans several model families and includes models described for long-context or code-oriented use; the present archive does not validate comparative reasoning depth or optimization stability.":
            "The configured pool spans several model families. Some models are designed for long-context or code-oriented use. The present archive does not compare reasoning depth or optimization stability.",
        "The Code Review module is the initial component of the STLC Manager and is designed to support the assessment of software source code in terms of potential correctness issues, maintainability concerns, and alignment with user-supplied rules by producing structured and systematic feedback.":
            "The Code Review module is the first component of STLC Manager. It assesses source code and produces structured feedback. The feedback covers possible correctness issues, maintainability concerns, and alignment with user-supplied rules.",
        "It supports Verification and Validation activities, particularly in Digital Twin-based systems, by prompting the selected LLM to assess consistency between implemented code and the supplied design or model descriptions and to identify potential deviations, redundant logic, maintainability concerns, and potential deviations from supplied rules.":
            "It supports Verification and Validation activities, especially in Digital Twin-based systems. The selected LLM compares the code with the supplied design or model descriptions. It then identifies possible differences, repeated logic, maintainability concerns, and conflicts with supplied rules.",
        "The resulting review is stored as a structured report within the STLC Manager workflow; however, the current implementation does not enforce a fixed issue-and-severity JSON schema or provide a direct continuous-integration or project-management integration.":
            "The resulting review is stored as a structured report in STLC Manager. The current implementation does not enforce a fixed JSON schema for issues and severity. It also does not provide direct integration with continuous-integration or project-management tools.",
        "The Requirement Analysis module is a foundational component of the STLC Manager that automates the interpretation, extraction, and evaluation of software and system requirements using terminology and concepts informed by ISTQB-oriented testing practice and model-based systems engineering, enabling direct interaction with structured models including SysML, UML, and XML to strengthen traceability between requirements, design, and implementation.":
            "The Requirement Analysis module interprets, extracts, and evaluates software and system requirements. It uses terms and concepts from ISTQB-oriented testing practice and model-based systems engineering. It can work with structured SysML, UML, and XML models. This supports traceability between requirements, design, and implementation.",
        "The Test Planning module serves as a structured coordination component within the STLC Manager that transforms requirements and software artefacts into clear, well-organized test plans by systematically defining scope, priorities, resources, timelines, dependencies, and risks in accordance with established testing practices.":
            "The Test Planning module turns requirements and software artefacts into structured test plans. It defines scope, priorities, resources, timelines, dependencies, and risks based on established testing practices.",
        "It analyzes input documents to produce standards-aligned planning outputs, such as professional test strategies and Gantt Chart style plans, while storing all intermediate decisions and final results in a structured form to support traceability, revision, reuse, and flexible deployment under strict data protection constraints.":
            "It analyses input documents and produces planning outputs, such as test strategies and Gantt chart plans. It stores intermediate decisions and final results in a structured form. This supports traceability, revision, reuse, and deployment under strict data protection rules.",
        "Its JSON output can document proposed tools, libraries, and compatibility conditions; environment correctness or automated deployment was not evaluated in this study.":
            "Its JSON output can document proposed tools, libraries, and compatibility conditions. This study did not evaluate environment correctness or automated deployment.",
        "Depending on the selected upload route and file-processing service, the inputs may include plain-text documents, supported source-code files, UML/XML artefacts, and extracted content from PDF or DOCX documents, together with the user-selected test category, test type, prompt template, and additional contextual options.":
            "The inputs depend on the upload route and file-processing service. They may include plain-text documents, source-code files, UML/XML artefacts, and content extracted from PDF or DOCX files. The user also selects the test category, test type, prompt template, and other context options.",
        "The application description identifies LM Studio and Google Gemini routes, but the archived experiment records do not preserve a provider/backend field; this architecture description therefore does not establish which route served any particular reported run.":
            "The application description identifies LM Studio and Google Gemini routes. The archived records do not preserve a provider or backend field. The architecture description therefore cannot show which route served a reported run.",
        "By reusing this validated engineering model as the benchmark artefact, the present study evaluates LLM-driven model-to-test transformation and test case optimization on an industrially motivated system with established behavioural semantics rather than on an artificially simplified example.":
            "The study reuses this validated engineering model as the benchmark artefact. It evaluates LLM-driven model-to-test transformation and test case optimization on an industrially motivated system. The system has established behavioural semantics and is not an artificial example.",
        "The expected outputs include structured JSON scenarios, automatic generation of core scenario fields such as ScenarioID, Title, Description, and Objective, proper alignment with the selected test category and type, and a traceable linkage between each scenario and the original artefact.":
            "The expected outputs are structured JSON scenarios. The system generates core fields such as ScenarioID, Title, Description, and Objective. It also links the selected test category and type to each scenario and to the original artefact.",
        "The stored comparison prompt instructs the LLM to prioritize Description, then Objective, then Title; two cases are considered equivalent only when their validation intent and scenario are substantially the same.":
            "The stored comparison prompt tells the LLM to prioritize Description, then Objective, and then Title. Two cases are equivalent only when their validation intent and scenario are substantially the same.",
        "A candidate is compared with previously retained representatives and is removed after the first positive match; otherwise it becomes a new representative.":
            "A candidate is compared with previously retained representatives. It is removed after the first positive match. If there is no positive match, it becomes a new representative.",
        "Parallel records preserve explicit pairwise comparisons and are labelled \\texttt{GeminiBatchAPI\\_Adaptive}; however, the archive does not expose exact request scheduling, concurrency limits, contradictory-decision handling, transitive closure, or representative reconciliation after merging.":
            "Parallel records preserve explicit pairwise comparisons and are labelled \\texttt{GeminiBatchAPI\\_Adaptive}. The archive does not show exact request scheduling or concurrency limits. It also does not show how the system handles conflicting decisions, transitive closure, or merged representatives.",
        "Serial contains 45 records across 11 model identifiers, including two Gemini Serial records; Bulk contains 15 records (seven Gemini-2.5 Flash, seven Gemini-2.5 Pro, and one GPT-OSS-20B); and Parallel contains 14 records, all using Gemini-2.5 Flash or Pro.":
            "Serial contains 45 records across 11 model identifiers, including two Gemini Serial records. Bulk contains 15 records. These include seven Gemini-2.5 Flash records, seven Gemini-2.5 Pro records, and one GPT-OSS-20B record. Parallel contains 14 records, all using Gemini-2.5 Flash or Pro.",
        "The revised study therefore does not claim a verified automatic threshold or fallback model; any deployment-specific model switching may introduce consistency effects that require separate evaluation.":
            "The revised study therefore does not claim a verified automatic threshold or fallback model. Any deployment-specific model switching may affect consistency and requires separate evaluation.",
        "Evaluator names, experience, blinding, adjudication, and completion timestamps were not stored; independence is therefore not claimed.":
            "Evaluator names, experience, blinding, adjudication, and completion timestamps were not stored. The study therefore does not claim evaluator independence.",
        "For 169 cases, exhaustive review contains 14,196 unordered pairs; at an assumed 20 seconds per pair, this equals 78.9 hours.":
            "For 169 cases, exhaustive review contains 14,196 unordered pairs. At an assumed 20 seconds per pair, this equals 78.9 hours.",
        "The original XML file and production switching configuration are not included in the supplied revision package; therefore, the exact context threshold, fallback rule, truncation behaviour, and previously stated structural element counts cannot be independently verified.":
            "The supplied revision package does not include the original XML file or the production switching configuration. Therefore, the exact context threshold, fallback rule, truncation behaviour, and earlier structural element counts cannot be verified.",
        "These results indicate model-dependent differences in generation breadth and test-suite size; however, they should not be interpreted as direct evidence of execution-path coverage because the generated tests were not executed against the target software in this study.":
            "These results show model-dependent differences in generation breadth and test-suite size. They do not provide direct evidence of execution-path coverage because this study did not execute the generated tests.",
        "The variation describes how the stored outputs decompose a common input into testing objectives; no fixed adequacy bound or verified requirement-to-case ratio is inferred.":
            "The variation shows how the stored outputs divide a common input into testing objectives. We do not infer a fixed adequacy bound or a verified requirement-to-case ratio.",
        "Where a table row shares a source suite, its total input set is the same; however, the broader archive is not fully crossed and does not establish a controlled strategy comparison.":
            "Rows that share a source suite also share the same total input set. However, the broader archive is not fully crossed. It does not support a controlled comparison of strategies.",
        "A high TRR means that a larger fraction was classified as Similar and removed; a low TRR means that a smaller fraction was removed.":
            "A high TRR means that a larger fraction was classified as Similar and removed. A low TRR means that a smaller fraction was removed.",
        "Because these extrema may come from different optimizer configurations and source-suite conditions, the ratio is a descriptive heterogeneity measure; it is not a within-test-set causal gain, cost reduction, or effectiveness estimate.":
            "These extrema may come from different optimizer configurations and source-suite conditions. The ratio is therefore a descriptive measure of variation. It is not a causal gain, cost reduction, or effectiveness estimate within one test set.",
        "Qwen3-Coder-30B has the largest spread (57\\%), followed by LLaMa3.2-3B and Codestral-22B (52\\%); LLaMa3.3-70B and GPT-OSS-20B have spreads of 49\\% and 47\\%.":
            "Qwen3-Coder-30B has the largest spread at 57\\%. LLaMa3.2-3B and Codestral-22B follow at 52\\%. LLaMa3.3-70B and GPT-OSS-20B have spreads of 49\\% and 47\\%.",
        "Differences across configurations describe decision outcomes only; they do not establish that a suite is clean, that one optimizer reasons better, or that removed cases are behaviourally unnecessary.":
            "Differences across configurations describe decision outcomes only. They do not show that a suite is clean or that one optimizer reasons better. They also do not show that removed cases are unnecessary.",
        "High or low CD reflects the archived ordered stopping behaviour; it is not evidence of model strength, convergence quality, or semantic correctness.":
            "High or low CD reflects the archived ordered stopping behaviour. It is not evidence of model strength, convergence quality, or semantic correctness.",
        "Their logs label the operation as \\texttt{Single LLM Call for All Test Cases}; no pairwise comparison count is recorded.":
            "Their logs label the operation as \\texttt{Single LLM Call for All Test Cases}. No pairwise comparison count is recorded.",
        "Lower values mean that a smaller fraction was classified as Similar; higher values mean that a larger fraction was so classified.":
            "Lower values mean that a smaller fraction was classified as Similar. Higher values mean that a larger fraction was classified as Similar.",
        "These proportions do not establish preservation quality or optimizer strength; the logs describe grouped single-call decisions without explicit pairwise counts.":
            "These proportions do not establish preservation quality or optimizer strength. The logs describe grouped single-call decisions without explicit pairwise counts.",
        "These values describe classification proportions; they do not establish conservatism, optimizer strength, or retained-suite quality.":
            "These values describe classification proportions. They do not establish conservatism, optimizer strength, or retained-suite quality.",
        "An SCP value of 100 percent means every pre-filter identifier remains represented by at least one retained case; lower values mean at least one identifier is absent afterward.":
            "An SCP value of 100 percent means that every pre-filter identifier remains in at least one retained case. Lower values mean that at least one identifier is absent after filtering.",
        "Across the archived configurations, mean SCP is 98.40\\% and the median is 100.00\\%; six configurations have partial scenario-identifier loss, with a minimum of 87.50\\%.":
            "Across the archived configurations, mean SCP is 98.40\\%, and the median is 100.00\\%. Six configurations have partial scenario-identifier loss. The minimum is 87.50\\%.",
        "It contains no information independent of SCP and TRR; its purpose is only to summarize their trade-off.":
            "It contains no information beyond SCP and TRR. Its only purpose is to summarize their trade-off.",
        "For example, 10 scenarios represented by 100 tests give SRG=1.0 when all 100 tests and all scenarios remain; retaining 20 tests but only 6 scenarios gives SCP=0.60, TRR=0.80, and SRG=3.0, showing that a high SRG can conceal scenario loss; retaining 50 tests and all 10 scenarios gives SCP=1.00, TRR=0.50, and SRG=2.0, a balanced reduction with full representation.":
            "For example, 10 scenarios represented by 100 tests give SRG=1.0 when all tests and scenarios remain. If 20 tests and only 6 scenarios remain, SCP=0.60, TRR=0.80, and SRG=3.0. This example shows that a high SRG can hide scenario loss. If 50 tests and all 10 scenarios remain, SCP=1.00, TRR=0.50, and SRG=2.0. This result shows reduction with full representation.",
        "Because SRG is algebraically determined by SCP and TRR, it is reported only as a compact descriptive summary; it does not independently demonstrate quality, stable improvement, or behavioural effectiveness.":
            "SRG is determined by SCP and TRR. It is therefore reported only as a short descriptive summary. It does not independently show quality, stable improvement, or behavioural effectiveness.",
        "Overall Fleiss' kappa was 0.1864; pairwise Cohen kappas were 0.1638, 0.1446, and 0.2671.":
            "Overall Fleiss' kappa was 0.1864. Pairwise Cohen kappas were 0.1638, 0.1446, and 0.2671.",
        "Record 18 contains the 137 GPT-OSS-20B items but is an earlier auxiliary GPT-OSS/GPT-OSS Serial result; the later systematically named record 39 represents that same source--optimizer--mode configuration in the benchmark, so record 18 is retained in the archive count but not counted as a separate benchmark configuration.":
            "Record 18 contains the 137 GPT-OSS-20B items. It is an earlier auxiliary GPT-OSS/GPT-OSS Serial result. The later and systematically named record 39 represents the same source--optimizer--mode configuration. Therefore, record 18 remains in the archive count but is not a separate benchmark configuration.",
        "The complete configuration-level confusion matrices and metrics are supplied in \\texttt{optimizer\\_item\\_level\\_metrics.csv}; item decisions are supplied in \\texttt{optimizer\\_item\\_level\\_decisions.csv}.":
            "The file \\texttt{optimizer\\_item\\_level\\_metrics.csv} contains the complete configuration-level confusion matrices and metrics. The file \\texttt{optimizer\\_item\\_level\\_decisions.csv} contains the item decisions.",
        "The 72-configuration item-level file additionally contains eight mapped auxiliary Serial configurations and the archived GPT-OSS Bulk configuration; it excludes records 0 and 18 for the reasons above.":
            "The 72-configuration item-level file also contains eight mapped auxiliary Serial configurations and the archived GPT-OSS Bulk configuration. It excludes records 0 and 18 for the reasons above.",
        "Lowering the threshold increased recall and false removals; raising it reduced false removals but missed more redundant cases.":
            "Lowering the threshold increased recall and false removals. Raising the threshold reduced false removals but missed more redundant cases.",
        "The new item-level analysis above is the primary evaluation; the count-level value is retained only to explain the earlier report.":
            "The new item-level analysis is the primary evaluation. The count-level value remains only to explain the earlier report.",
        "The TF--IDF baseline provides a deterministic lexical reference; a future staged system could use lexical or embedding retrieval to generate candidates and reserve an LLM for reranking or adjudication.":
            "The TF--IDF baseline provides a deterministic lexical reference. A future system could use lexical or embedding retrieval to find candidates. It could then use an LLM for reranking or adjudication.",
        "The results therefore describe single archived outputs rather than robustness distributions; no repeated-run means, variances, confidence intervals, or significance tests are claimed.":
            "The results therefore describe single archived outputs, not robustness distributions. We do not claim repeated-run means, variances, confidence intervals, or significance tests.",
        "Title, Description, and Objective form an intermediate pre-execution schema; preconditions, steps, data, expected results, and executable oracles may be embedded in prose rather than mandatory fields.":
            "Title, Description, and Objective form an intermediate pre-execution schema. Preconditions, steps, data, expected results, and executable oracles may appear in prose instead of mandatory fields.",
        "A reproducible offline TF--IDF analysis provides a non-LLM reference; its threshold-dependent false-removal trade-off cautions against selecting a deployment rule on the same reference used for evaluation.":
            "A reproducible offline TF--IDF analysis provides a non-LLM reference. Its false-removal results depend on the threshold. This trade-off shows why the evaluation reference should not also define the deployment rule.",
        "The STLC Manager organizes the entire testing workflow into a set of modular and tightly integrated components that operate within a unified and sequential testing pipeline, as illustrated in Figure~\\ref{fig:figure4}.":
            "STLC Manager organizes the testing workflow into connected modules. These modules operate in one sequence, as shown in Figure~\\ref{fig:figure4}.",
        "The evaluation was designed to benchmark two main capabilities of the proposed framework: (i) test scenario and test case generation from heterogeneous software artefacts and (ii) semantic test case optimization using different LLMs and optimization strategies.":
            "The evaluation covers two main capabilities. The first is test scenario and test case generation from different software artefacts. The second is semantic test case optimization with different LLMs and optimization strategies.",
        "The process starts when the user defines important parameters such as the process title, test category (Functional or Non-Functional), specific test type (e.g., Integration Testing, Security Testing, or Performance Testing), and the selected AI model.":
            "The process starts when the user defines the main parameters. These include the process title, test category, test type, and selected AI model. The test category can be Functional or Non-Functional. Example test types include Integration Testing, Security Testing, and Performance Testing.",
        "The Test Case Generation module is an advanced phase of the STLC Manager where previously generated test scenarios are automatically transformed into structured and traceable test cases that can be adapted for subsequent execution.":
            "The Test Case Generation module transforms earlier scenarios into structured and traceable test cases. These test cases can later be adapted for execution.",
        "Rather than interpreting the value of 49 against a predefined theoretical bound, this result is treated as an empirical generation outcome for the XML-based transformation and as a reference point for comparing generation behaviour across the heterogeneous artefact types.":
            "The study does not compare the value of 49 with a predefined theoretical bound. It treats the value as an observed result of the XML-based transformation. The value also provides a reference for comparing generation across different artefact types.",
        "These differences demonstrate that the evaluated models generate test suites of substantially different sizes under the same experimental workflow, which in turn affects the amount of semantic redundancy that must be handled during the subsequent optimization stage.":
            "The evaluated models generated test suites of different sizes under the same workflow. Suite size affects how much semantic redundancy the later optimization stage must process.",
        "This work was supported by the Chips Joint Undertaking (Chips JU) under Grant Agreement No.~101140216 and its members, including top-up funding from Vinnova (Sweden), Österreichische Forschungsförderungsgesellschaft mbH (FFG, Austria), Business Finland (Finland), the Ministry of Universities and Research (Italy), Fundação para a Ciência e a Tecnologia (Portugal), and TÜBİTAK (Türkiye) under Grant No.~124N448.":
            "This work was supported by the Chips Joint Undertaking (Chips JU) under Grant Agreement No.~101140216 and its members. Top-up funding came from Vinnova (Sweden), Österreichische Forschungsförderungsgesellschaft mbH (FFG, Austria), Business Finland (Finland), the Ministry of Universities and Research (Italy), Fundação para a Ciência e a Tecnologia (Portugal), and TÜBİTAK (Türkiye) under Grant No.~124N448.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace(
        r"\keyword{Software Testing; Large Language Models; STLC; Test Scenario Generation; Test Case Generation; Test Case Optimization}",
        r"\keyword{Software Testing, Large Language Models, STLC, Test Scenario Generation, Test Case Generation, Test Case Optimization}",
    )
    text = text.replace(r"\State $U\gets\emptyset$; $R\gets\emptyset$", "\\State $U\\gets\\emptyset$\n\\State $R\\gets\\emptyset$")
    text = text.replace(
        r"\State $R\gets R\cup\{t_i\}$; $\mathit{removed}\gets\textbf{true}$; \textbf{break}",
        "\\State $R\\gets R\\cup\\{t_i\\}$\n      \\State $\\mathit{removed}\\gets\\textbf{true}$\n      \\State \\textbf{break}",
    )
    text = text.replace("45 records; 11 model identifiers", "45 records, 11 model identifiers")
    text = text.replace("Provider/backend not stored; order-dependent", "Provider/backend not stored, order-dependent")
    text = text.replace("per pair; not observed workflow", "per pair, not observed workflow")
    text = text.replace("No elapsed-time field; prior 13-batch estimate withdrawn", "No elapsed-time field. Prior 13-batch estimate withdrawn")
    text = text.replace("writing---original draft preparation", "writing original draft preparation")
    text = text.replace("writing---review and editing", "writing review and editing")
    text = text.replace("{The authors declare no conflicts of interest. The funders had no role in the design of the study; in the collection, analyses, or interpretation of data; in the writing of the manuscript; or in the decision to publish the results.}",
                        "{The authors declare no conflicts of interest. The funders had no role in the study design, data collection, data analysis, data interpretation, manuscript writing, or publication decision.}")
    text = re.sub(r";\s+([a-z])", lambda match: ". " + match.group(1).upper(), text)
    text = text.replace("; ", ". ").replace(";", ".")
    text = text.replace("—", ". ")
    return text


def prepare_final_minor_pass(text: str) -> str:
    """Apply only the final requested copy-edits and mark only this pass."""
    # Earlier reviewer-driven changes remain in the text, but their old
    # highlight markers must not appear in this final minor-edit variant.
    text = text.replace("[REV_BEGIN]\n", "").replace("\n[REV_END]", "")
    text = text.replace("[HROW]", "")

    edits = (
        (
            "This structured representation supports structured representation and identifier-level traceability while enabling the automated generation of test-case descriptions, as illustrated in Listing~\\ref{lst:generated-case}.",
            "This structured representation supports identifier-level traceability while enabling the automated generation of test-case descriptions, as illustrated in Listing~\\ref{lst:generated-case}.",
        ),
        (
            "Suite size affects how much semantic redundancy the later optimization stage must process.",
            "Suite size determines the number of cases presented to the later semantic optimization stage.",
        ),
        (
            "distinguishes between functional and non-functional testing needs to ensure consistent scenario classification",
            "distinguishes between functional and non-functional testing needs to support consistent scenario classification",
        ),
        (
            "The study-aligned Bulk subset contains 14 records. Seven use Gemini-2.5 Flash and seven use Gemini-2.5 Pro. Parallel contains 14 records, all using Gemini-2.5 Flash or Pro. One additional Bulk artifact remains in the archive-wide audit. It is excluded from this design summary because its backend and role in the study cannot be verified.",
            "The study-aligned Bulk subset contains 14 records. Seven use Gemini-2.5 Flash and seven use Gemini-2.5 Pro. Parallel contains 14 records, all using Gemini-2.5 Flash or Pro. One additional Bulk artifact remains in the archive-wide audit. It is excluded from this design summary because its backend and role in the study cannot be verified.",
        ),
        (
            "Study-aligned optimization design and available execution metadata",
            "Study-aligned optimization design and available execution metadata",
        ),
        (
            "14 study-aligned records: Flash (7), Pro (7)",
            "14 study-aligned records: Flash (7), Pro (7)",
        ),
        (
            "The 72-configuration item-level file also contains eight mapped auxiliary Serial configurations and one auxiliary Bulk configuration. These auxiliary records are retained in the archive-wide diagnostic outputs. They are not treated as evidence about the study's deployment design.",
            "The 72-configuration item-level file also contains eight mapped auxiliary Serial configurations and one auxiliary Bulk configuration. These auxiliary records are retained in the archive-wide diagnostic outputs. They are not treated as evidence about the study's deployment design.",
        ),
        (
            "The study-aligned Bulk and Parallel subsets contain only Gemini Flash and Pro. An auxiliary Bulk artifact is not used to infer deployment capability because its backend and role in the study cannot be verified.",
            "The study-aligned Bulk and Parallel subsets contain only Gemini Flash and Pro. An auxiliary Bulk artifact is not used to infer deployment capability because its backend and role in the study cannot be verified.",
        ),
    )
    for old, new in edits:
        if text.count(old) != 1:
            raise ValueError(f"Expected one final-copy-edit match for: {old}")
        text = text.replace(old, f"[REV_BEGIN]\n{new}\n[REV_END]", 1)

    # The earlier semicolon-to-period conversion left a duplicated full stop
    # after the final author initials in each contribution statement.
    if text.count("A.Y..") != 12:
        raise ValueError("Expected 12 duplicated author-contribution full stops")
    text = text.replace("A.Y..", "[TYPO_BEGIN]A.Y.[TYPO_END]")
    return text


def render_variant(marked: str, highlighted: bool) -> str:
    if highlighted:
        def highlight_block(match: re.Match) -> str:
            block = match.group(1).strip()
            paragraphs = re.split(r"\n\s*\n", block)
            return "\n\n".join(r"\hl{" + paragraph.replace("\n", " ") + "}" for paragraph in paragraphs)

        marked = re.sub(r"\[REV_BEGIN\]\s*(.*?)\s*\[REV_END\]", highlight_block, marked, flags=re.S)
        marked = re.sub(r"\[TYPO_BEGIN\](.*?)\[TYPO_END\]", r"\\hl{\1}", marked)
        marked = marked.replace("[HROW]", r"\rowcolor{yellow!28}")
        preamble = r"""
\sethlcolor{yellow}
\soulregister\citep7
\soulregister\ref7
\soulregister\texttt7
\soulregister\textbf7
\soulregister\emph7
\soulregister\mathrm1
"""
        marked = re.sub(
            r"(?m)^\\begin\{document\}$",
            lambda _m: preamble + "\n" + r"\begin{document}",
            marked,
            count=1,
        )
    else:
        marked = marked.replace("[REV_BEGIN]\n", "").replace("\n[REV_END]", "")
        marked = marked.replace("[TYPO_BEGIN]", "").replace("[TYPO_END]", "")
        marked = marked.replace("[HROW]", "")
    return marked


def add_reference(bbl: str) -> str:
    # These entries were either incomplete, whole-proceedings citations, or
    # misaligned with the claims they previously supported. The revised text
    # does not cite them, so remove them instead of inventing metadata.
    rejected = {"bib26", "bib27", "bib43", "bib44", "bib45", "bib48", "bib60", "bib64"}

    def retain_supported_entry(match: re.Match) -> str:
        block = match.group(0)
        return "" if any("{" + key + "}" in block for key in rejected) else block

    bbl = re.sub(
        r"\\bibitem.*?(?=\\bibitem|\\end\{thebibliography\})",
        retain_supported_entry,
        bbl,
        flags=re.S,
    )
    entry = r"""
\bibitem[Meng et~al.(2026)Meng, He, Hussain, Zhou, Xu, Zhao, and Xiong]{bib70}
Meng, Q.; He, Y.; Hussain, S.; Zhou, F.; Xu, J.; Zhao, G.; Xiong, D.
\newblock Dense retrieval and reranking for referenced provisions in electric power audit systems.
\newblock {\em PLOS ONE} {\bf 2026}, {\em 21}, e0344683.
\newblock {\url{https://doi.org/10.1371/journal.pone.0344683}}.

"""
    return bbl.replace(r"\end{thebibliography}", entry + r"\end{thebibliography}")


def main() -> None:
    marked = prepare_final_minor_pass(simplify_language(build_marked()))
    for name, highlighted in (("clean", False), ("highlighted", True)):
        dest = OUT / name
        dest.mkdir(parents=True, exist_ok=True)
        for path in ROOT.glob("figure*.png"):
            shutil.copy2(path, dest / path.name)
        if not (dest / "Definitions").exists():
            shutil.copytree(ROOT / "Definitions", dest / "Definitions")
        (dest / "applsci-4556799-revised.tex").write_text(render_variant(marked, highlighted), encoding="utf-8")
        bbl = (ROOT / "applsci-4556799.bbl").read_text(encoding="utf-8")
        (dest / "applsci-4556799-revised.bbl").write_text(add_reference(bbl), encoding="utf-8")
    print("Built clean and highlighted LaTeX sources")


if __name__ == "__main__":
    main()
