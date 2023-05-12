import locale
import pandas as pd
import numpy as np
from datetime import datetime
import dask.dataframe as dd
from collections import Counter


def anonymize2(data, k=3):
    """
    Takes as input the dask dataframe and the desired k and returns a dask dataframe which is k-anonymized.
    """
    locale.setlocale(category=locale.LC_ALL, locale="en_US.UTF-8")
    data_copy = data.copy()
    # for column in data.columns:
    for column in data.columns:
        print(f'Column processed: {column}')
        values_per_col = data[column].value_counts().compute()
        sorted_values_per_col = values_per_col.sort_index(ascending=True,
                                                          key=lambda col: col.map(str))
        anonymize_dict = process_col_3(sorted_values_per_col, k)
        data_copy[column] = data[column].replace(to_replace=anonymize_dict)
    return data_copy


def process_col_3(column, k):
    """
    Takes as input the column and the desired k and returns a python dictionary with the mapping of each value to an
    integer.
    """
    start = datetime.now()
    d = {}
    cum_sum = 0
    group = 1
    for i, (index, value) in enumerate(column.items()):
        cum_sum += value
        if cum_sum >= k:
            d[index] = group
            cum_sum = 0
            group += 1
        else:
            d[index] = group
    # the last value of data
    end = datetime.now()
    print(f'Process col time elapsed: {end - start}')
    return d
