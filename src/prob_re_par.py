import pandas as pd
from datetime import datetime
import math
import itertools
import dask
from auxiliary_functions import top_tuples


def get_combinations_num(num_of_cols: int, size_of_tuple: int) -> int:
    """
    Returns the number of all possible combinations
    """
    return math.comb(num_of_cols, size_of_tuple)


def compute_probabilities(data, size_of_tuple: int, alpha: float):
    start_time = datetime.now()
    cols_risk = ['risk']
    cols_var_ind = [f'var_ind.{i+1}' for i in range(size_of_tuple)]
    cols_var_name = [f'vars.{i+1}' for i in range(size_of_tuple)]
    num_of_rows = data.shape[0]  # number of rows in the dataframe
    num_of_cols = data.shape[1]  # number of columns in the dataframe
    combinations = itertools.combinations(range(0, num_of_cols), size_of_tuple)  # all possible combinations
    if size_of_tuple == 2:
        delayed_list = [dask.delayed(compute_distinct_combinations)(data, (i, j), size_of_tuple, num_of_rows)
                        for i, j in combinations]
    elif size_of_tuple == 3:
        delayed_list = [dask.delayed(compute_distinct_combinations)(data, (i, j, k), size_of_tuple, num_of_rows)
                        for i, j, k in combinations]
    elif size_of_tuple == 4:
        delayed_list = [dask.delayed(compute_distinct_combinations)(data, (i, j, k, l), size_of_tuple, num_of_rows)
                        for i, j, k, l in combinations]
    results = dask.compute(*delayed_list)
    results_df = pd.DataFrame(results, columns=cols_risk + cols_var_ind + cols_var_name)
    # sorted dataframe in descending order based on 'risk' column, if column's risks are equal then sort ascending based
    # on the var.ind column
    results_df = results_df.sort_values(by=cols_risk + cols_var_ind, ascending=[False] + [True]*len(cols_var_ind),
                                        ignore_index=True)
    top_results = top_tuples(results_df, alpha)
    end_time = datetime.now()
    print(f'Prob_re_par time elapsed: {end_time-start_time}')
    return results_df, top_results


def compute_distinct_combinations(data, combinations, size_of_tuple, num_of_rows):
    distinct_tuples = data[[data.columns[combinations[i]] for i in range(size_of_tuple)]].drop_duplicates()\
                                        .shape[0]
    return distinct_tuples/num_of_rows, *combinations, *[*[data.columns[combinations[i]] for i in range(size_of_tuple)]]
