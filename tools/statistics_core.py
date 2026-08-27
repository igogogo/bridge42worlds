# -*- coding: utf-8 -*-
"""Раздел статистики: методы, которыми физика обрабатывает данные.

Владелец 27.08: «добавил бы отдельный раздел статистику — собрать эмпирически
все возможные используемые в физике статистические методы и приёмы, это реально
то, чего не хватает, сделать как новый раздел кроме математики».

Почему нельзя добыть из статей. Статью размечает сито дословных упоминаний: у
понятия должно быть имя, названное в тексте. Статистику же в статьях НЕ называют
— её делают. «Мы подогнали спектр» вместо «метод наименьших квадратов», «сигнал
на пяти сигма» вместо «проверка гипотезы». Из 275 кандидатов этого класса опору
хотя бы в пять статей имеют семь. Ждать, пока наберут, бесполезно: они и не
наберут никогда.

Значит источник тот же, что у констант, — канон предмета. Список ниже собран по
практике экспериментальной физики и астрономии: то, что стоит в разделе «анализ
данных» почти любой статьи. Каждое понятие получает класс statistics, короткое
определение и группу; развёрнутую карточку и вектор ему напишет обычный ночной
шаг, как всякому другому понятию.

Дубли. Часть этих имён у нас уже есть — иногда под другим классом (matched
filtering числится статистикой, а fourier transform математикой) или под другим
именем (monte carlo sampling против monte carlo simulation). Совпадение ищем по
множеству значимых слов, а не по строке, и при совпадении не создаём ничего.

  python tools/statistics_core.py            # показать, что добавится
  python tools/statistics_core.py --apply
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "data" / "concepts-live.json"
GROWN = ROOT / "data" / "concepts-grown.json"
HARVEST = ROOT / "data" / "concept-harvest.jsonl"
MENTIONS = ROOT / "data" / "concept-mentions.jsonl"

STOP = {"of", "the", "a", "an", "and", "in", "for", "to", "method", "methods",
        "analysis", "test", "testing"}

# Класс у понятия один, а принадлежность — двойная: стандартное отклонение это
# и величина, и статистика. Поэтому класс перебиваем только там, где нынешний
# ничего не говорит («понятие», «метод», «явление»), а специфичный — величину,
# математику, закон — оставляем как есть и вносим понятие в раздел меткой.
SOFT_KINDS = {"concept", "method", "phenomenon", "process", "property", "effect"}

# Разделы — чтобы страница раздела не была плоским списком из ста имён.
CORE = {
"Оценивание и подгонка": {
 "maximum_likelihood_estimation": "Choosing the parameter values that make the observed data most probable under the model; the workhorse fit of experimental physics.",
 "least_squares_fitting": "Fitting by minimising the sum of squared residuals — the special case of maximum likelihood when errors are Gaussian and equal.",
 "chi_squared_minimisation": "Fitting by minimising chi-squared, the sum of squared residuals weighted by their uncertainties; its value at the minimum also measures goodness of fit.",
 "weighted_mean": "Combining measurements of different precision by weighting each by the inverse square of its uncertainty.",
 "profile_likelihood": "Handling nuisance parameters by maximising the likelihood over them at each value of the parameter of interest.",
 "kernel_density_estimation": "Estimating a smooth probability density from samples without assuming its functional form.",
 "regularisation": "Adding a penalty term to a fit to suppress wild solutions when the data underdetermine the model.",
 "unfolding": "Correcting a measured distribution for detector smearing to recover the true one — an ill-posed inversion that needs regularisation.",
},
"Байесовский анализ": {
 "bayesian_inference": "Treating parameters as random variables: prior belief times likelihood gives the posterior, which is the full answer of the measurement.",
 "prior_distribution": "What is assumed about a parameter before the data — the input of Bayesian analysis that most often decides its output.",
 "posterior_distribution": "The distribution of a parameter after the data are folded in; its width is the Bayesian uncertainty.",
 "bayes_factor": "Ratio of the evidence of two models — the Bayesian answer to which model the data prefer.",
 "markov_chain_monte_carlo": "Sampling a posterior by a random walk that visits parameter space in proportion to probability; the standard tool of modern cosmology.",
 "metropolis_hastings_algorithm": "The basic Markov chain rule: propose a step, accept it with a probability set by the ratio of posteriors.",
 "nested_sampling": "Sampling that computes the Bayesian evidence itself, not only the posterior; standard in gravitational-wave analysis.",
 "hamiltonian_monte_carlo": "Markov chain sampling that uses gradients of the posterior to take long, well-aimed steps in many dimensions.",
 "gibbs_sampling": "Sampling a multidimensional posterior one coordinate at a time from its conditional distributions.",
 "credible_interval": "The Bayesian interval containing a stated fraction of the posterior — the answer to 'where is the parameter', unlike a confidence interval.",
 "bayesian_hierarchical_model": "A model with parameters of parameters — the way to fit a population and its individual members at once.",
 "bayesian_evidence": "The probability of the data under a model with parameters integrated out; penalises complexity automatically.",
},
"Проверка гипотез": {
 "null_hypothesis_testing": "Asking how improbable the data would be if there were no effect — the frame in which discoveries are declared.",
 "p_value": "Probability of data at least as extreme as observed if the null hypothesis holds; not the probability that the hypothesis is true.",
 "statistical_significance": "How far a result stands from the no-effect expectation, usually in standard deviations; five sigma is the discovery threshold in particle physics.",
 "confidence_interval": "The frequentist interval that would contain the true value in a stated fraction of repeated experiments.",
 "likelihood_ratio_test": "Comparing two nested models by the ratio of their maximum likelihoods; its distribution follows Wilks' theorem.",
 "wilks_theorem": "Result that twice the log likelihood ratio approaches a chi-squared distribution, which turns fits into significance.",
 "kolmogorov_smirnov_test": "Comparing two distributions by the largest gap between their cumulative curves, without binning.",
 "anderson_darling_test": "A distribution comparison weighted towards the tails, where the Kolmogorov-Smirnov test is weakest.",
 "student_t_test": "Comparing means of small samples when the variance itself is estimated from the data.",
 "look_elsewhere_effect": "The inflation of significance that comes from searching many places at once; the reason local and global significance differ.",
 "trials_factor": "The number of independent chances a search had to produce a fluctuation, by which local significance must be corrected.",
 "feldman_cousins_construction": "A unified way to build intervals that avoids empty and unphysical results near a boundary.",
 "cls_method": "The modified frequentist limit-setting used at colliders, which refuses to exclude models the experiment has no power to test.",
 "type_i_error": "Rejecting a true null hypothesis — a false discovery.",
 "type_ii_error": "Failing to reject a false null hypothesis — a missed effect.",
},
"Ресемплинг и проверка": {
 "bootstrap_method": "Estimating uncertainty by resampling the data with replacement — no model of the errors needed.",
 "jackknife_resampling": "Estimating uncertainty and bias by leaving out one observation at a time.",
 "cross_validation": "Assessing a model on data it was not fitted to, by splitting the sample repeatedly.",
 "permutation_test": "Building the null distribution by shuffling labels of the data themselves.",
 "blind_analysis": "Fixing the analysis before looking at the answer, so that the result cannot be tuned towards the expected one.",
},
"Распределения": {
 "gaussian_distribution": "The bell curve that sums of many small independent effects converge to; the default error model of physics.",
 "binomial_distribution": "The distribution of successes in a fixed number of yes-or-no trials.",
 "exponential_distribution": "The distribution of waiting times between events that happen at a constant rate; the law of radioactive decay.",
 "power_law_distribution": "A distribution with no typical scale, where rare large events dominate — from earthquakes to stellar masses.",
 "log_normal_distribution": "The distribution of a quantity whose logarithm is Gaussian; arises from multiplicative processes.",
 "chi_squared_distribution": "The distribution of a sum of squared Gaussian variables; the reference curve for goodness of fit.",
 "landau_distribution": "The strongly asymmetric distribution of energy loss by a charged particle in a thin absorber.",
 "central_limit_theorem": "Why the Gaussian is everywhere: sums of many independent contributions tend to it whatever their own shape.",
},
"Неопределённости": {
 "systematic_uncertainty": "Error that does not shrink with more data — calibration, model choice, detector response; usually the limit of a modern measurement.",
 "statistical_uncertainty": "Error from finite sample size, which falls as the square root of the number of events.",
 "error_propagation": "Carrying uncertainties through a calculation, including the correlations between inputs.",
 "covariance_matrix": "The full description of uncertainties and their correlations; ignoring its off-diagonal terms is a standard way to get a wrong error bar.",
 "correlation_coefficient": "How strongly two quantities move together, on a scale from minus one to one.",
 "standard_deviation": "The typical spread of a distribution around its mean.",
 "standard_error": "The uncertainty of an estimated quantity, such as the mean, rather than the spread of the data.",
 "pull_distribution": "The distribution of residuals divided by their uncertainties; a check that the errors themselves are right.",
 "sigma_clipping": "Discarding points beyond a chosen number of standard deviations, iteratively — the common defence against outliers.",
},
"Сигналы и временные ряды": {
 "power_spectral_density": "How the variance of a signal is distributed over frequency; the basic language of noise.",
 "lomb_scargle_periodogram": "Finding periods in unevenly sampled data, where the ordinary Fourier transform cannot be used.",
 "autocorrelation_function": "How a signal resembles itself after a delay; reveals periods and correlation times.",
 "wavelet_analysis": "Decomposing a signal in time and frequency at once, for features that come and go.",
 "kalman_filter": "Tracking a changing state by folding each new measurement into a running estimate; used to fit particle tracks.",
 "matched_filter": "Correlating data with the expected shape of the signal — the optimal detector of a known waveform in Gaussian noise.",
 "signal_to_noise_ratio": "How far a signal stands above the noise; the currency in which detectability is measured.",
 "detrending": "Removing a slow trend before analysing the variability that rides on it.",
},
"Многомерный анализ и обучение": {
 "principal_component_analysis": "Finding the directions of largest variance to describe many correlated variables by a few.",
 "independent_component_analysis": "Separating mixed signals into statistically independent sources.",
 "k_means_clustering": "Splitting data into groups around centres found iteratively.",
 "boosted_decision_tree": "A committee of simple trees, each fixing the errors of the last; long the standard classifier in particle physics.",
 "random_forest": "A committee of decorrelated decision trees, robust and hard to overfit.",
 "support_vector_machine": "A classifier that separates classes by the widest possible margin.",
 "roc_curve": "The trade-off between signal efficiency and background rejection as the cut is moved.",
 "confusion_matrix": "The table of what a classifier got right and wrong, class by class.",
 "overfitting": "Learning the noise of the training sample; the reason a model that fits perfectly can predict badly.",
 "feature_importance": "How much each input variable actually contributes to a trained model's decisions.",
},
"Моделирование и выборка": {
 "monte_carlo_simulation": "Answering a problem by simulating random draws from it — from detector response to lattice field theory.",
 "importance_sampling": "Drawing from a distribution chosen to put samples where they matter, then reweighting.",
 "rejection_sampling": "Drawing from a simple distribution and keeping points that fall under the target one.",
 "toy_monte_carlo": "Repeating the whole analysis on many simulated pseudo-experiments to learn how its answer fluctuates.",
 "information_criterion": "Model comparison that trades goodness of fit against the number of parameters, as in AIC and BIC.",
 "model_selection": "Choosing between competing descriptions of the same data, by evidence, criterion or cross-validation.",
},
}


# Те, кто уже носил класс statistics до появления раздела. Ядро их не называет,
# поэтому части им надо назначить отдельно — иначе страница раздела кончается
# свалкой «Прочее» на шестнадцать имён.
EXTRA_PARTS = {
    "linear_regression": "Оценивание и подгонка",
    "spectral_fitting": "Оценивание и подгонка",
    "gaussian_process_regression": "Оценивание и подгонка",
    "neural_network_regression": "Многомерный анализ и обучение",
    "chi_squared_test": "Проверка гипотез",
    "five_sigma": "Проверка гипотез",
    "goodness_of_fit": "Проверка гипотез",
    "model_comparison": "Проверка гипотез",
    "poisson_distribution": "Распределения",
    "matched_filtering": "Сигналы и временные ряды",
    "noise_subtraction": "Сигналы и временные ряды",
    "spectral_line_measurement": "Сигналы и временные ряды",
    "polarization_measurement": "Сигналы и временные ряды",
    "outlier_rejection": "Неопределённости",
    "binning": "Неопределённости",
    "monte_carlo_sampling": "Моделирование и выборка",
    "least_squares": "Оценивание и подгонка",
    "uncertainty_quantification": "Неопределённости",
    "bootstrap": "Ресемплинг и проверка",
}


def words(cid):
    return {w for w in cid.replace("-", "_").split("_") if w and w not in STOP}


def main():
    apply = "--apply" in sys.argv
    live = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    # карта «множество слов → существующее понятие», чтобы поймать иные написания
    by_words = {}
    for cid in live:
        by_words.setdefault(frozenset(words(cid)), cid)

    add, dup, reclass, tagged = {}, [], {}, {}

    def existing(cid, group):
        """Понятие уже есть: либо меняем общий класс, либо просто метим разделом."""
        was = live[cid].get("kind")
        if was == "statistics":
            dup.append(cid)
        elif was in SOFT_KINDS:
            reclass[cid] = was
        else:
            tagged[cid] = was
        sections[cid] = group

    sections = {}
    for group, items in CORE.items():
        for cid, card in items.items():
            if cid in live:
                existing(cid, group)
                continue
            same = by_words.get(frozenset(words(cid)))
            if same:
                dup.append(f"{cid} ≈ {same}")
                existing(same, group)
                continue
            add[cid] = {
                "kind": "statistics", "group": "other", "scope": "general",
                "card_en": card, "articles": [], "aliases": [],
                "origin": "statistics-core", "section": group,
            }

    for cid in add:
        sections[cid] = add[cid]["section"]
    for cid, part in EXTRA_PARTS.items():
        if cid in live:
            sections.setdefault(cid, part)

    print(f"ядро статистики: {sum(len(v) for v in CORE.values())} понятий")
    print(f"  добавится: {len(add)}")
    print(f"  уже есть статистикой: {len(dup)}")
    print(f"  класс сменится: {len(reclass)}")
    for cid, was in sorted(reclass.items()):
        print(f"    ~ {cid} ({was} → statistics)")
    print(f"  класс сохранён, метка раздела: {len(tagged)}")
    for cid, was in sorted(tagged.items()):
        print(f"    · {cid} остаётся {was}")
    for group in CORE:
        got = [c for c in add if add[c]["section"] == group]
        if got:
            print(f"  · {group}: {len(got)}")
    if not apply:
        print("\nсухой ход. записать: --apply")
        return 0

    g = json.loads(GROWN.read_text(encoding="utf-8")) if GROWN.exists() else {}
    g.update(add)
    GROWN.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
    kf_p = ROOT / "data" / "concept-kind-fix.json"
    kf = json.loads(kf_p.read_text(encoding="utf-8")) if kf_p.exists() else {}
    for cid in reclass:
        kf[cid] = "statistics"
    kf_p.write_text(json.dumps(kf, ensure_ascii=False, indent=1), encoding="utf-8")
    # Раздел — отдельным файлом: по нему собирается страница раздела и фильтр в
    # графе. Величина, попавшая в раздел, остаётся величиной.
    sec_p = ROOT / "data" / "concept-sections.json"
    sec = json.loads(sec_p.read_text(encoding="utf-8")) if sec_p.exists() else {}
    for cid, group in sections.items():
        sec[cid] = {"section": "statistics", "part": group}
    sec_p.write_text(json.dumps(sec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nзаписано: копилка {len(g)} · правок класса {len(kf)} "
          f"· в разделе статистики {len(sec)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
