import numpy as np
import pandas as pd
import math
import dask.array as da
import dask.dataframe as dd
from scipy.stats import genpareto
from datetime import datetime


def num_extremes(x, alpha):
    """
    Inputs
        x: all risks computed by compute_probabilities
        alpha: desired alpha %

    Returns
        a list which contains the risks that are greater than threshold, the number of extreme values and the threshold
    """
    threshold_u = np.quantile(x, 1-alpha, method="median_unbiased")  # threshold u
    x_ex = x[x > threshold_u]  # pandas.Series with the risks that are > u
    number_of_extremes = len(x_ex)  # number of extreme values
    return [x_ex, number_of_extremes, threshold_u]


def id_danger(x, v, alpha):
    """
    Inputs
        x: all risks computed by compute_probabilities
        v: 0.99
        alpha: desired alpha %

    Returns
        a list which contains the extreme values, threshold, shape, scale and x hat
    """
    res = num_extremes(x, alpha/100)
    x_ex = res[0]
    nu = res[1]
    u = res[2]
    #  print(f'x ex - u = {x_ex-u}')
    xi, beta = fit_gpd_pwm(x_ex - u)
    try:
        x_hat = u + beta / xi * ((len(x) / nu * (1 - v)) ** (-xi) - 1)
    except ZeroDivisionError:
        x_hat = float('inf')
    #  extreme values: x_ex
    #  threshold: u
    #  shape: xi
    #  scale: beta
    #  POT: x_hat
    r1 = [x_ex, u, xi, beta, x_hat]
    return r1


def fit_gpd_pwm(x):
    """
    Inputs
        x: all risks computed by compute_probabilities

    Returns
        Shape and Scale of GPD
    """
    if np.sum(x) == 0:
        sd = np.float64(np.format_float_scientific(np.finfo(float).eps, precision=6))
        x = np.abs(np.random.normal(loc=0, scale=sd, size=len(x)))  # loc is mean and scale is standard deviation
    x_sorted = np.sort(x)  # xs is R
    n = x_sorted.size
    k = np.arange(1, n+1)  # create a numpy array [1,n]
    a0 = np.mean(x)
    a1 = np.mean(x_sorted * (n - k)/(n - 1))
    shape = 2 - a0/(a0 - 2 * a1)
    scale = max((2*a0*a1)/(a0-2 * a1), np.float64(np.format_float_scientific(np.finfo(float).eps, precision=6)))
    return shape, scale


def calculations(x, v1=0.99, v2=0.999, alpha=5):
    """
    Inputs
        x: all risks computed by compute_probabilities
        v1: 0.99
        v2: 0.999
        alpha: desired alpha % (default = 5)

    Returns
        a list which contains p99, p999, extreme values, z, shape, scale, shape with x logit, scale with x logit,
                              threshold, POT estimate with v1 and logit, POT estimate with v2 and logit
    """
    # calling id_danger with v1
    tms = id_danger(x, v1, alpha)
    xi = round(tms[2], ndigits=4)  # xi: shape
    beta = round(tms[3], ndigits=4)  # beta: scale
    u = tms[1]  # u: threshold with v1, alpha
    ex = tms[0]  # ex: value_extreme
    p99 = tms[4]  # the temperature: 1% of size-h pseudo-identifiers
    # calling id_danger with v2
    tms = id_danger(x, v2, alpha)
    p999 = tms[4]
    # calling id_danger with logit and v1
    tms = id_danger(np.log(x/(1-x)), v1, alpha)
    xi_logit = round(tms[2], ndigits=4)  # xi_logit: shape with logit
    beta_logit = round(tms[3], ndigits=4)  # beta: scale with logit
    if len(ex) < 10 & len(x) < 70:
        x_hat_logit_v1 = np.max(x)
    elif len(ex) < 30:
        x_hat_logit_v1 = np.quantile(x, 0.99, method="median_unbiased")
    else:
        x_hat_logit_v1 = (np.exp(tms[4])/(1+np.exp(tms[4])))  # POT estimate with v1 and logit
    #  calling id_danger with logit and v2
    tms = id_danger(np.log(x / (1 - x)), v2, alpha)
    x_hat_logit_v2 = (np.exp(tms[4]) / (1 + np.exp(tms[4])))  # POT estimate with v2 and logit
    z = genpareto.ppf(ppoints(1000), xi_logit, np.log(u/(1-u)), beta_logit)
    z = np.exp(z) / (1 + np.exp(z))  # bring the quantiles from logit to proper scale
    res = [p99, p999, ex, z, xi, beta, xi_logit, beta_logit, u, x_hat_logit_v1, x_hat_logit_v2]
    return res


def ppoints(n: int):
    """
    Numpy analogue of `R`'s `ppoints` function
    """
    a = 3/8 if n < 10 else 1./2
    return (np.arange(n) + 1 - a)/(n + 1 - 2*a)


def top_tuples(results, alpha: float):
    """
    Inputs
        results: sorted risks of all the combination
        alpha: desired alpha %

    Returns
        the alpha % of tuples with the highest probabilities
    """
    num_of_extremes = num_extremes(results['risk'], alpha)[1]
    riskiest_results = results.head(num_of_extremes)
    return riskiest_results


def top_columns(top_probs, ddf, unique_counts):
    """
    Input:
        top_probs: the alpha % of tuples with the highest probabilities (pandas)
        ddf: the whole dataset (dask)

    Returns
        a Dataframe with the statistics (Count, Distinct, Entropy, Min Risk, Median Risk, Max Risk) on the variables
        participating in the - alpha % - riskiest combinations.
    """
    start_time = datetime.now()
    np.seterr(divide='ignore')

    # Get the columns from top_tuples that start with var_ind
    cols_ind = [col for col in top_probs.columns if col.startswith('var_ind')]

    # Melt the pivot to convert it from wide to long, using the risk columns as an id
    # and the values of the var_ind columns (index of the columns names) as value columns
    long_df = pd.melt(top_probs, id_vars=['risk'], value_vars=cols_ind)

    # start_time = datetime.now()
    # Find the min and max risk for every variable that's included in the top tuple table
    min_risk = long_df.groupby(['value']).aggregate({'risk': 'min'})
    max_risk = long_df.groupby(['value']).aggregate({'risk': 'max'})
    # end_time = datetime.now()
    # print(f'min-max risk time elapsed: {end_time-start_time}')
    def calculate_median(group):
        return group.median()

    # start_time = datetime.now()
    median_risk = long_df.groupby('value')['risk'].apply(calculate_median).to_frame()
    median_risk.index = median_risk.index.rename("value1")
    median_risk['value'] = median_risk.index
    median_risk = median_risk[['value', 'risk']]
    median_risk = median_risk.rename(columns={'risk': 'median'})
    # end_time = datetime.now()
    # print(f'median risk time elapsed: {end_time-start_time}')

    # Count the times each variable appears in the combinations (of 2ples, 3ples)
    value_count = long_df.groupby('value').size()
    value_count = value_count.to_frame()

    # start_time = datetime.now()
    # Count the unique values in each column of the dataset
    unique_df = pd.DataFrame({'Distincts': unique_counts.values}, index=unique_counts.index)
    unique_df['value'] = unique_df.reset_index().index
    unique_df = unique_df[['value', 'Distincts']]
    # end_time = datetime.now()
    # print(f'unique df time elapsed: {end_time-start_time}')

    # Get variable names
    col_names = ddf.columns.tolist()
    variables = pd.DataFrame(col_names, columns=['Variables'])
    variables['value'] = variables.reset_index().index
    variables = variables[['value', 'Variables']]

    # start_time = datetime.now()
    entropy = {}
    for column in ddf.columns:
        pis = ddf[column].value_counts() / len(ddf[column])
        # Calculate the entropy of the column
        entropy[column] = -np.sum(pis * np.log2(pis)).compute()
    entropy = pd.DataFrame(entropy.values(), columns=['Entropy'])
    entropy['value'] = entropy.reset_index().index
    entropy = entropy[['value', 'Entropy']]
    # end_time = datetime.now()
    # print(f'entropy time elapsed: {end_time-start_time}')

    # Merge all the above calculations to create the final table for top_column
    df = pd.merge(variables, value_count, on='value')
    df = pd.merge(df, unique_df, on='value')
    df = pd.merge(df, entropy, on='value')
    df = pd.merge(df, min_risk, on='value')
    df = pd.merge(df, median_risk, on='value')
    df = pd.merge(df, max_risk, on='value')
    cols = ['Index', 'Variable', 'Count', 'Distincts', 'Entropy', 'min_risk', 'median risk', 'max_risk']
    df = df.rename(columns=dict(zip(df.columns, cols)))
    df = df.sort_values(by=['Count', 'Index'], ascending=[False, True])
    end_time = datetime.now()
    print(f'Top_columns time elapsed: {end_time-start_time}')
    return df


def QaR(x, v1, alpha):
    """
    Inputs
        x: all risks computed by compute_probabilities
        v1: 0.99
        alpha: desired alpha %

    Returns
        POT estimate with v1 and logit
    """
    tms = id_danger(np.log(x / (1 - x)), v1, alpha)
    ex = tms[0]  # ex: value_extreme
    # calculate QaR
    if len(ex) < 10 & len(x) < 70:
        # print("Method: max")
        x_hat_logit_v1 = np.max(x)
    elif len(ex) < 30:
        # print("Method: quantile")
        x_hat_logit_v1 = np.quantile(x, 0.99, method="median_unbiased")
    else:
        # print("Method: GPD")
        x_hat_logit_v1 = (np.exp(tms[4])/(1+np.exp(tms[4])))
    return x_hat_logit_v1


def qar_steps(newdata, x, col_names, results, h, v1=0.99, v2=0.999, alpha=5):
    """
    Inputs:
        newdata: the whole dataset as a Dask Dataframe
        x: all risks computed by compute_probabilities
        col_names: list which contains the column names
        results: the dataframe which is computed by compute_probabilities
        h: size of tuple
        v1: default 0.99
        v2: default 0.999
        alpha: desired alpha % (default 5%)

    Returns:
        res: a list which contains p99, p999, extreme values, z, shape, scale, shape with x logit, scale with x logit,
                              threshold, POT estimate with v1 and logit, POT estimate with v2 and logit
        qar_df: a Dataframe which contains the following columns - qar, excluded, mean entropy, id2
    """
    start_time = datetime.now()

    # ddf = dd.from_pandas(newdata, npartitions=9)
    ddf = newdata
    entropy = {}
    n_rows = ddf.index.size.compute()
    for column in ddf.columns:
        pis = ddf[column].value_counts() / n_rows  # a series with the proportion of each value of the column
        # Calculate the entropy of the column
        entropy[column] = -da.sum(pis * da.log2(pis))
    entropy = pd.DataFrame(entropy.values(), columns=['Entropy'])

    num_of_cols = ddf.shape[1]
    x_copy = x
    max_it = min(num_of_cols - 1, 10)  # max iterations - check if columns are few
    qar_df = pd.DataFrame({'id': list(range(max_it + 1)), 'excluded': '', 'QaR': np.nan, 'Mean_entropy': np.nan})
    allowed_cols = list(range(0, num_of_cols))
    cols_ind = [col for col in results.columns if col.startswith('var_ind')]
    ind_values = results[cols_ind].values

    q = QaR(x_copy, v1, alpha)
    qar_df.loc[0, 'QaR'] = q
    qar_df['Mean_entropy'].at[0] = entropy.mean()

    j_min = -1
    for it in range(0, max_it + 1):
        q_min = float('inf')
        for j_col in allowed_cols:
            rows_keep = [not j_col in row for row in ind_values]
            x_keep = x_copy[rows_keep]
            q = QaR(x_keep, v1, alpha)
            if pd.isna(q):
                continue
            if q < q_min:
                q_min = q
                j_min = j_col

        if q_min == float('inf'):
            continue
        allowed_cols = [col for col in allowed_cols if col != j_min]
        # calculate mean entropy of remaining columns
        cur_entropy = entropy['Entropy'][allowed_cols]
        cur_mean_entropy = cur_entropy.mean()

        # fill next row in dataframe qar_df
        qar_df['QaR'].at[it + 1] = round(q_min, 4)
        qar_df['excluded'].at[it + 1] = col_names[j_min]
        qar_df['Mean_entropy'].at[it + 1] = cur_mean_entropy

        # update for next iteration
        rows_keep = [j_min not in row for row in ind_values]
        ind_values = ind_values[rows_keep]
        x_copy = x_copy[rows_keep]
    qar_df['id2'] = list(range(1, max_it + 2))
    res = calculations(x, v1, v2, alpha)
    # print(qar_df)
    end_time = datetime.now()
    print(f'QaR steps time elapsed: {end_time - start_time}')
    return res, qar_df
