import pandas as pd
import json
import unicodedata
import os, getpass
import dask.dataframe as dd
from datetime import datetime
from platform import system as get_system_type

pd.options.mode.chained_assignment = None


class Global:
    """Global variables to create the temporary file and delete it after use"""
    os_type = 'Windows' if get_system_type() == 'Windows' else 'Unix'
    sep = os.sep
    user = getpass.getuser()
    temp_dir = './static/data'
    # temp_dir = f'{sep}users{sep}' + user + f'{sep}Documents{sep}' if os_type == 'Windows' else f'{sep}tmp'


def convert_excel_to_csv(has_header, filepath):
    """Read excel with pandas and convert it to csv using a temporary file.
    Csv file is deleted after use.

    Temporary csv file is created using the Global class variables.
    """
    df = pd.read_excel(filepath, dtype=object)
    filename = os.path.basename(filepath).split('.')[0]
    df.to_csv(Global.temp_dir + f"{filename}.csv", index=False, date_format='%d/%m/%Y')
    # print(f'DEBUG > {filename}')
    if has_header:
        data = pd.read_csv(Global.temp_dir + filename + ".csv", sep=None, engine='python', dtype=str)
    else:
        data = pd.read_csv(Global.temp_dir + filename + ".csv", sep=None, header=None,
                           engine='python', dtype=str)
        data.columns = [f'X{i+1}' for i in data.columns]
    data = data.fillna('NA')
    return data


def get_extension(filepath):
    """Check if the extension of the file is in the approved extensions list
    Get the extensions to read the file accordingly
    """
    whitelist = ['csv', 'xlsx']
    file_extension = filepath.split('.')[-1].lower()
    # print("extension:", file_extension)
    if file_extension in whitelist:
        if file_extension == 'csv':
            extension_csv = True
            return extension_csv
    elif file_extension == 'xlsx':
        extension_csv = False
        return extension_csv
    else:
        return ("Extension must be .csv or .xlsx")


def read_data(has_header, filepath):
    """In case of csv file, read the data with Dask Dataframe and use blocksize to create partitions
        In case of Excel file, convert the Excel to csv using the function convert_excel_to_csv
        and then read Dask Dataframe"""
    try:
        with open("../config/dask_config.json") as f:
            config = json.load(f)
            n_partitions = config["n_partitions"]
    except FileNotFoundError:
        print("File dask_config.json not found")
        n_partitions = 1
    if get_extension(filepath):
        if has_header:
            data = pd.read_csv(filepath, na_values="-", sep=None, engine='python', dtype=str)
        else:
            data = pd.read_csv(filepath, header=None, na_values="-",
                               sep=None, engine='python', dtype=str)
            data.columns = [f'V{i+1}' for i in data.columns]
        data = data.fillna('NA')
        return dd.from_pandas(data, npartitions=n_partitions)
    else:
        # print("excel")
        if has_header:
            data = convert_excel_to_csv(has_header, filepath)
        else:
            data = convert_excel_to_csv(has_header, filepath)
        return dd.from_pandas(data, npartitions=n_partitions)


# unicode normalization
def norm_s(data):
    """Unicode normalize each cell of the dataframe"""
    return unicodedata.normalize('NFKD', str(data))


# Function that computes the final df to be displayed to the user
def print_final_df(filepath, has_header):
    """Read the data and unicode normalize them using map_partition
    Map_partition suns the normalization in parallel for each partition

    Finally, use .compute() to actually get the results and delete the temporary file if it exists
    """
    ddf = read_data(has_header, filepath)
    final_ddf = ddf.applymap(norm_s).compute()
    # print(ddf.map_partitions(len).compute())
    filename = os.path.basename(filepath).split('.')[0]
    try:
        os.remove(Global.temp_dir + filename + ".csv")
    except:
        pass
    return final_ddf


def print_final_df_unc(filepath, has_header):
    """Read the data and unicode normalize them using map_partition
    Map_partition suns the normalization in parallel for each partition

    Finally, use .compute() to actually get the results and delete the temporary file if it exists
    """
    start_time = datetime.now()
    ddf = read_data(has_header, filepath)
    final_ddf = ddf.applymap(norm_s)

    # print(ddf.map_partitions(len).compute())

    filename = os.path.basename(filepath).split('.')[0]
    # try:
    #     os.remove(Global.temp_dir + filename + ".csv")
    # except:
    #     pass
    end_time = datetime.now()
    print(f'Time to read data {end_time-start_time}')
    return final_ddf


def get_distinct_vals(filepath):
    ddf = read_data(True, filepath)
    meta = pd.DataFrame(columns=ddf.columns, dtype='object')
    final_ddf = ddf.map_partitions(norm_s, meta=meta)
    distinct_vals = {}
    for col in ddf.columns:
        #         unique_counts[col] = ddf[col].unique().compute().size
        distinct_vals[col] = ddf[col].nunique().compute()
    unique_df = pd.DataFrame(distinct_vals.values(), columns=['Distinct'])
    filename = os.path.basename(filepath).split('.')[0]
    try:
        os.remove(Global.temp_dir + filename + ".csv")
    except:
        pass
    return unique_df

