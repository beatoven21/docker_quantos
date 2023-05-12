import dask
import math
import os
import time
import import_data 
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
from flask_session import Session
import requests, json, getpass
from datetime import datetime
import pandas as pd
import dask.dataframe as dd
from distributed import Client, LocalCluster
from prob_re_par import compute_probabilities, get_combinations_num
from auxiliary_functions import calculations, top_columns, qar_steps
from plots import plot_hist, plot_extremes_hist, plot_distinct_bar, plot_steps, \
    plot_steps_entr, plot_GPD_fit, plot_POT_logit
from anonymize import anonymize2
from platform import system as get_system_type

UPLOAD_FOLDER = './static/data'

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

PROCESSED_DATA_FOLDER = './static/processed_data'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = 'mySecretKey'
Session(app)

progress = 0


def get_extension(filename: str) -> str:
    """
    Returns: The extension of the uploaded file
    """
    file_extension = filename.rsplit('.', 1)[1].lower()
    return file_extension


def allowed_file(file_extension: str) -> bool:
    """
    Returns: True if the file extension is xlsx or csv
    """
    return file_extension in ALLOWED_EXTENSIONS


def get_num_rows_cols(pandas_data):
    """
    Returns: Number of rows and columns of the dataset
    """
    num_of_rows = pandas_data.shape[0].compute()  # number of rows in the dask dataframe
    num_of_cols = pandas_data.shape[1]  # number of columns in the dask dataframe
    return num_of_rows, num_of_cols


def get_file_size(filepath: str) -> str:
    """
    Returns: Size of the file in a human-readable format
    """
    return convert_size(os.stat(filepath).st_size)


def convert_size(size_in_bytes: float) -> str:
    """"
    Takes as input the size of the file in bytes and converts it to a human-readable format
    """
    if size_in_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_in_bytes, 1000)))
    p = math.pow(1000, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"


def cut_off_delete(columns, data, cut_off_percentage: int) -> list[str]:
    """
    Drop the columns which the number of their unique values is greater or equal than the selected percentage of the
    total row number.
    Returns a list of the columns that will be dropped
    """
    total_rows = data.shape[0].compute()
    unique_counts = data.nunique().compute()
    cols_to_drop = [column for column in columns if unique_counts[column] >= (cut_off_percentage / 100) * total_rows]
    session["msg"] = f"Deleted due to cut off {len(cols_to_drop)} variable: {'; '.join(cols_to_drop)}" \
        if len(cols_to_drop) == 1 \
        else f"Deleted due to cut off {len(cols_to_drop)} variables: {'; '.join(cols_to_drop)}"
    return cols_to_drop


class Global:
    """Global variables to create the temporary file and delete it after use"""
    os_type = 'Windows' if get_system_type() == 'Windows' else 'Unix'
    sep = os.sep
    user = getpass.getuser()
    temp_dir = './static/data'
    tmp_session_data = ""
    # temp_dir = f'{sep}users{sep}' + user + f'{sep}Documents{sep}' if os_type == 'Windows' else f'{sep}tmp'


def user_validation(key):
    res = requests.post(
        "https://api.keygen.sh/v1/accounts/09bb8bda-315a-438d-aecc-9fba2d7e7fdc/licenses/actions/validate-key",
        headers={
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        },
        data=json.dumps({
            "meta": {
                "key": key,
            }
        })
    ).json()
    if res['data'] is not None:
        return True
    else:
        return False


@app.route("/", methods=['GET', 'POST'])
def home_page():
    # initialize the session with null values when home page is accessed
    session['is_validated'] = False
    session["data_html"] = ""
    session["ddf"] = ""
    # session["sorted_ddf"] = None
    session["columns"] = ""
    session["df_columns"] = ""
    session["filename"] = ""
    session["filepath"] = ""
    session["file_size"] = ""
    session["num_of_rows"] = ""
    session["num_of_cols"] = ""
    session["msg"] = ""
    session["risk"] = ""
    session["shape"] = ""
    session["scale"] = ""
    session["alpha"] = ""
    session["num_of_combination"] = ""
    session["top_cols"] = pd.DataFrame()  # initialize with an empty df
    session["size_of_tuple"] = ""
    session["res"] = ""
    session["graph_json"] = ""
    session["graphJSON"] = ""
    session["graphJSON2"] = ""
    # Goodness of fit tab
    session["graphJSON4"] = ""
    session["graphJSON5"] = ""
    session["res_qar_steps"] = [""] * 3  # initialize with an empty list of size 3
    # sensitivity analysis tab
    session["qar_df"] = pd.DataFrame()
    session["graphJSON6"] = ""
    session["graphJSON7"] = ""

    if request.method == 'POST':
        activation_key = request.form['activation_key']
        if user_validation(activation_key):
            session['is_validated'] = True
            # Render the home page if the user is validated
            # empty uploaded folder every time home page is accessed
            if len(os.listdir(UPLOAD_FOLDER)) != 0:
                os.remove(f'{UPLOAD_FOLDER}/{os.listdir(UPLOAD_FOLDER)[0]}')
                filename = os.path.basename(session["filepath"]).split('.')[0]
                try:
                    os.remove(Global.temp_dir + filename + ".csv")
                except:
                    pass
            return redirect(url_for("data_upload_page"))
        else:
            # Render the activation form with an error message if the activation key is invalid
            error_message = 'Invalid activation key'
            return render_template('login.html', error_message=error_message)
    else:
        # Render the activation form if the user has not submitted the activation key
        return render_template('login.html')


@app.route("/data-upload", methods=["GET", "POST"])
def data_upload_page():
    if not session.get('is_validated'):
        # Redirect the user to the home page if they are not validated
        return redirect(url_for('home_page'))
    global progress
    progress = 0
    # enable anonymize and re-identification risk submit buttons only when data is uploaded
    anonymize_btn = '' if len(os.listdir(UPLOAD_FOLDER)) != 0 else 'disabled'
    submit_btn = '' if len(os.listdir(UPLOAD_FOLDER)) != 0 else 'disabled'
    if request.method == 'GET':
        return render_template('data-upload.html', anonymize_btn=anonymize_btn, submit_btn=submit_btn,
                               graphJSON=session["graph_json"], msg=session["msg"],
                               data=session["ddf"], columns=session["columns"], filename=session["filename"],
                               file_size=session["file_size"], num_of_rows=session["num_of_rows"],
                               num_of_cols=session["num_of_cols"], df_columns=session['df_columns'])
    if request.method == 'POST':
        if 'uploadedFile' not in request.files:
            # check if a file has already been uploaded
            if len(os.listdir(UPLOAD_FOLDER)) != 0:
                # "Submit" button is pushed
                if "submitBtn" in request.form:
                    progress += 20  # start calculating the progress for the estimation of re identification risk
                    size_of_tuple = int(request.form['tupleSize'])
                    alpha = int(request.form['riskiestPercentage'])
                    session['tup_size'] = int(request.form['tupleSize'])
                    session['alpha'] = int(request.form['riskiestPercentage'])
                    session["prob_results"], top_results = compute_probabilities(Global.tmp_session_data,
                                                                                 size_of_tuple,
                                                                                 alpha / 100)
                    top_results.index += 1  # increment index by 1
                    session["top_res"] = top_results
                    progress += 10  # update the progress after compute_probabilities function is finished
                    risk = calculations(x=session["prob_results"]['risk'].to_numpy(),
                                        alpha=alpha)  # use all the results
                    # save to the session the corresponding values
                    session["shape"] = risk[6]
                    session["scale"] = risk[7]
                    session["risk"] = round(risk[9], 4)
                    session["alpha"] = alpha
                    session["num_of_combination"] = len(session["top_res"].index)
                    session["size_of_tuple"] = size_of_tuple
                    session["res"] = top_results.to_html(float_format='{:,.6f}'.format, table_id='riskTable',
                                                         classes=['table', 'display', 'table-striped',
                                                                  'row-border', 'table-hover']
                                                         )
                    progress += 10  # update the progress after calculations function is finished
                    session["graphJSON"] = plot_hist(res=session["prob_results"], alpha=alpha / 100,
                                                     filename=os.listdir(UPLOAD_FOLDER)[0],
                                                     num_of_rows=get_num_rows_cols(session["ddf"])[0],
                                                     num_of_cols=get_num_rows_cols(session["ddf"])[1],
                                                     size_of_tuple=size_of_tuple,
                                                     u=risk[8],
                                                     num_of_combination=get_combinations_num(
                                                         num_of_cols=get_num_rows_cols(session["ddf"])[1],
                                                         size_of_tuple=size_of_tuple)
                                                     )
                    progress += 10  # update the progress after the creation of the first histogram on "risk" tab
                    session["graphJSON2"] = plot_extremes_hist(res=top_results['risk'], alpha=alpha,
                                                               filename=os.listdir(UPLOAD_FOLDER)[0],
                                                               num_of_riskiest_combination=len(session["top_res"].index)
                                                               )
                    progress += 10  # update the progress after the creation of the second histogram on "risk" tab
                    # calculate the dataframe for the statistics tab
                    top_cols = top_columns(session["top_res"], Global.tmp_session_data, session["unique_counts"]) \
                        .sort_values('Count', ascending=False, ignore_index=True)
                    top_cols.index += 1  # increment index by 1
                    top_cols.replace(-0.0, 0.0, inplace=True)
                    session["top_cols"] = top_cols
                    # calculate the dataframe for the sensitivity tab
                    session["res_qar_steps"], session["qar_df"] = qar_steps(newdata=Global.tmp_session_data,
                                                                            x=session["prob_results"][
                                                                                'risk'].to_numpy(),
                                                                            col_names=session['ddf'].columns,
                                                                            results=session["prob_results"],
                                                                            h=session["size_of_tuple"])

                    # first plot of goodness of fit tab
                    session["graphJSON4"] = plot_GPD_fit(session["prob_results"]['risk'].to_numpy(),
                                                         session['alpha'], session["res_qar_steps"])
                    progress += 10  # update the progress after the creation of the first plot on "goodness of fit" tab
                    # second plot of goodness of fit tab
                    session["graphJSON5"] = plot_POT_logit(session["prob_results"]['risk'].to_numpy(),
                                                           session['alpha'], session["res_qar_steps"])
                    progress += 10  # update the progress after the creation of the second plot on "goodness of fit" tab
                    # first plot of sensitivity tab
                    session["graphJSON6"] = plot_steps(session["qar_df"])
                    progress += 10  # update the progress after the creation of the first plot on "sensitivity" tab
                    # second plot of sensitivity tab
                    session["graphJSON7"] = plot_steps_entr(session["qar_df"])
                    progress += 10  # update the progress after the creation of the second plot on "sensitivity" tab
                    time.sleep(2.1)
                    return redirect(url_for("identification_risk"))
                # "Anonymize" button is pushed
                if "anonymizeBtn" in request.form:
                    start = datetime.now()
                    k = int(request.form.get("kAnonymization"))
                    progress += 20
                    # get the anonymized dask df and the unique counts pandas Series
                    session['ddf'] = anonymize2(session['ddf'], k)
                    Global.tmp_session_data = session['ddf'].persist()
                    end = datetime.now()
                    print(f'Anonymize2 time elapsed: {end - start}')
                    progress += 20
                    # create a df with the number of the distinct values as a proportion of the number of observations
                    start = datetime.now()
                    session["unique_counts"] = session['ddf'].nunique().compute()
                    session["columns"] = [[i + 1, col_name, session["unique_counts"][i]] for i, col_name in
                                          enumerate(session['ddf'].columns)]
                    # create a df with the number of the distinct values as a proportion of the number of observations
                    cols = [f'{i + 1}: {name}' for i, name in enumerate(session['ddf'].columns)]
                    num_of_distinct = [session["unique_counts"][column] / session["num_of_rows"]
                                       for column in session['ddf'].columns]
                    session["unique_df"] = pd.DataFrame(list(zip(cols, num_of_distinct)),
                                                        columns=["column", "distinct"])
                    progress += 40
                    session["graph_json"] = plot_distinct_bar(session["unique_df"])
                    end = datetime.now()
                    print(f'Create of bar plot time elapsed: {end - start}')
                    time.sleep(2.1)
                    progress += 20
                    time.sleep(2.1)
                    return render_template('data-upload.html', num_of_rows=session['num_of_rows'],
                                           num_of_cols=session['num_of_cols'],
                                           file_size=session["file_size"], anonymize_btn='', submit_btn='',
                                           msg=session["msg"],
                                           columns=session["columns"], graphJSON=session["graph_json"],
                                           df_columns=session['df_columns'], plets=session["p_lets"]
                                           )
            return render_template('home.html', anonymize_btn=anonymize_btn, submit_btn=submit_btn)
        uploaded_file = request.files['uploadedFile']
        # check if the input is empty
        if uploaded_file.filename == '':
            flash('Input should not be empty', 'danger')
            return render_template('home.html', anonymize_btn=anonymize_btn, submit_btn=submit_btn)
        # check if the file extension is allowed
        file_extension = get_extension(uploaded_file.filename)
        if allowed_file(file_extension):
            # delete all the files under the upload folder
            for f in list(os.listdir(UPLOAD_FOLDER)):
                os.remove(f'{UPLOAD_FOLDER}/{f}')
            # Check if file contains headers
            if request.form.get("hasHeader") != "True":  # File does not contain headers
                has_header = False
            else:  # File contains headers
                has_header = True
            filename = secure_filename(uploaded_file.filename)
            session["filename"] = filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            session["filepath"] = filepath
            progress += 10
            uploaded_file.save(filepath)  # save the uploaded file in the folder 'src/static/data/<filename>'
            session["file_size"] = get_file_size(filepath)  # size of the uploaded file
            session['cut_off_percentage'] = int(request.form.get("cutOff"))
            progress += 10
            session['ddf'] = import_data.print_final_df_unc(filepath, has_header)
            # session['uploaded_data'] = import_data.print_final_df(filepath, has_header)
            progress += 20
            # get the columns to drop
            start_time = datetime.now()
            session['df_columns'] = [col for col in session['ddf'].columns]
            session['cols_to_drop'] = cut_off_delete(session['df_columns'], session['ddf'],
                                                     session['cut_off_percentage'])
            session['df_columns'] = [col for col in session['df_columns'] if col not in session['cols_to_drop']]
            session['ddf'] = session['ddf'].drop(session['cols_to_drop'], axis=1)  # drop the columns
            session['ddf'] = session['ddf'].sort_values(session['ddf'].columns[0])
            Global.tmp_session_data = session['ddf']
            progress += 20
            session["unique_counts"] = session['ddf'].nunique().compute()
            session["num_of_rows"], session["num_of_cols"] = get_num_rows_cols(session['ddf'])
            session["columns"] = [[i + 1, col_name, session["unique_counts"][i]] for i, col_name in
                                  enumerate(session['ddf'].columns)]
            # create a df with the number of the distinct values as a proportion of the number of observations
            cols = [f'{i + 1}: {name}' for i, name in enumerate(session['ddf'].columns)]
            # num_of_distinct = [session['unique_counts']/session["num_of_rows"]
            #                    for column in session['ddf'].columns]
            num_of_distinct = [session["unique_counts"][column] / session["num_of_rows"]
                               for column in session['ddf'].columns]
            session["unique_df"] = pd.DataFrame(list(zip(cols, num_of_distinct)),
                                                columns=["column", "distinct"])
            session['p_lets'] = '{:,.0f}'.format(math.comb(get_num_rows_cols(session['ddf'])[1], 3))
            session["graph_json"] = plot_distinct_bar(session["unique_df"])
            end_time = datetime.now()
            print(f'Time in between {end_time - start_time}')
            progress += 20
            time.sleep(2.1)
            progress += 20
            time.sleep(2.1)
            flash('File successfully uploaded', 'success')
            return render_template('data-upload.html', num_of_rows=session['num_of_rows'],
                                   num_of_cols=session['num_of_cols'],
                                   file_size=session["file_size"], anonymize_btn='', submit_btn='', msg=session["msg"],
                                   columns=session["columns"], graphJSON=session["graph_json"],
                                   df_columns=session['df_columns'], plets=session["p_lets"]
                                   )
        else:
            flash('Extension must be .csv or .xlsx', 'danger')
            return render_template('home.html', anonymize_btn=anonymize_btn, submit_btn=submit_btn)


@app.route("/risk", methods=['GET', 'POST'])
def identification_risk():
    if not session.get('is_validated'):
        # Redirect the user to the home page if they are not validated
        return redirect(url_for('home_page'))
    if request.method == 'GET':
        return render_template('risk.html', risk=session["risk"], alpha=session["alpha"],
                               num_of_combination=session["num_of_combination"],
                               size_of_tuple=session["size_of_tuple"], res=session["res"],
                               graphJSON=session["graphJSON"], graphJSON2=session["graphJSON2"])


@app.route('/statistics', methods=['GET', 'POST'])
def variables_statistics():
    if not session.get('is_validated'):
        # Redirect the user to the home page if they are not validated
        return redirect(url_for('home_page'))
    if request.method == 'GET':
        return render_template('statistics.html', alpha=session["alpha"],
                               num_of_rows=session["top_cols"].shape[0],
                               stats=session["top_cols"].to_html(float_format='{:,.6f}'.format, table_id='statTable',
                                                                 classes=['table', 'display', 'table-striped',
                                                                          'row-border', 'table-hover'])
                               )


@app.route('/goodness-of-fit', methods=['GET', 'POST'])
def goodness_of_fit():
    if not session.get('is_validated'):
        # Redirect the user to the home page if they are not validated
        return redirect(url_for('home_page'))
    if request.method == 'GET':
        return render_template('goodness_of_fit.html', shape=session["shape"], scale=session["scale"],
                               alpha=session["alpha"], graphJSON4=session["graphJSON4"],
                               graphJSON5=session["graphJSON5"], xex=session["res_qar_steps"][2])


@app.route('/sensitivity-analysis', methods=['GET', 'POST'])
def sensitivity_analysis():
    if not session.get('is_validated'):
        # Redirect the user to the home page if they are not validated
        return redirect(url_for('home_page'))
    if request.method == 'GET':
        return render_template('sensitivity_analysis.html', qar_df=session["qar_df"],
                               graphJSON6=session["graphJSON6"], graphJSON7=session["graphJSON7"],
                               excluded=session["qar_df"].iloc[1:, 1:2])


@app.route("/get_page_content", methods=['GET'])
def get_page_content():
    start_time = datetime.now()

    ddf = Global.tmp_session_data  # session['ddf']
    total_rows = ddf.shape[0].compute()

    # Get the search parameter
    search = request.args.get('search[value]')
    # Filter the data based on the search parameter
    if search:
        ddf = ddf.map_partitions(
            lambda df: df[df.apply(
                lambda x: any(val.lower() in str(x[col]).lower() for val in search.split() for col in df.columns),
                axis=1
            )]
        )

    # Sorting
    sort_col = request.args.get('order[0][column]')
    sort_dir = request.args.get('order[0][dir]')

    if sort_col and sort_dir:
        # If the sort column and direction have changed, update the sorting and store the new values in the session
        if sort_col != session.get('sort_col') or sort_dir != session.get('sort_dir'):
            col_name = request.args.get(f'columns[{sort_col}][data]')
            if col_name in ddf.columns:
                ascending = sort_dir != 'desc'
                ddf = ddf.sort_values(col_name, ascending=ascending)
                Global.tmp_session_data = ddf
                session['sort_col'] = sort_col
                session['sort_dir'] = sort_dir
            else:
                print(f"Invalid column name {col_name}")
        else:
            sorted_ddf = Global.tmp_session_data
            if sorted_ddf is not None:
                ddf = sorted_ddf
    else:
        # If no sort column or direction is specified, use the previously sorted Dask dataframe from the session
        sorted_ddf = Global.tmp_session_data
        if sorted_ddf is not None:
            ddf = sorted_ddf
    Global.tmp_session_data = ddf.persist()

    # pagination
    # Get the start and length for pagination
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)

    # Filter the data based on the search parameter again to ensure that only the matching rows are returned for the current page
    if search:
        ddf = ddf.map_partitions(
            lambda df: df[df.apply(
                lambda x: any(val.lower() in str(x[col]).lower() for val in search.split() for col in df.columns),
                axis=1
            )]
        )
        total_filtered = ddf.shape[0].compute()
    else:
        total_filtered = total_rows

    data = calculate_pagination_indices(ddf, start, length)
    end_time = datetime.now()
    print(f'Time to paginate {end_time - start_time}')

    # Get the current page of data from the Dask dataframe
    return {'data': data,
            'recordsFiltered': total_filtered,
            'recordsTotal': total_rows,
            'draw': request.args.get('draw', type=int),
            }


@app.route('/drop-columns', methods=['POST'])
def drop_columns():
    # retrieve the uploaded data
    data = session["ddf"]
    # get the list of columns that will be dropped
    columns = request.form.getlist("dropCols")
    # message to be display after the drop of the selected columns
    msg = f'Deleted {len(columns)} column' if len(columns) == 1 else f'Deleted {len(columns)} columns'
    session['msg'] = msg
    # drop the selected columns
    session["ddf"] = data.drop([column.split()[1] for column in columns], axis=1)
    Global.tmp_session_data = session["ddf"]
    # update the columns after the drop of the selected columns
    session["columns"] = [[i + 1, col_name, session["unique_counts"][i]]
                          for i, col_name in enumerate(session["ddf"].columns)]
    session['df_columns'] = session['ddf'].columns
    session["num_of_rows"], session["num_of_cols"] = get_num_rows_cols(session['ddf'])
    # update the unique df which is used for the distinct bar plot
    # unique_df = session["unique_df"]
    # unique_df = unique_df[~unique_df["column"].str
    #                                           .split(': ', expand=True)[1]
    #                                           .isin([col.split()[1] for col in columns])]  # filter out the dropped cols
    cols = [f'{i + 1}: {name}' for i, name in enumerate(session["ddf"].columns)]
    num_of_distinct = [session["unique_counts"][column] / session["num_of_rows"]
                       for column in session['ddf'].columns]
    session["unique_df"] = pd.DataFrame(list(zip(cols, num_of_distinct)),
                                        columns=["column", "distinct"])
    session["graph_json"] = plot_distinct_bar(session["unique_df"])
    return redirect(url_for("data_upload_page"))


def calculate_pagination_indices(df, start, length):
    """
    Calculate the partition index and row start/end for the current page of data.
    """
    # Get the length of each partition
    partition_lengths = df.map_partitions(len).compute()

    # Calculate the cumulative sum of the partition lengths to get the partition start indices
    partition_start_indices = partition_lengths.cumsum() - partition_lengths
    partition_end_indices = partition_start_indices + partition_lengths
    total_rows = partition_lengths.sum()

    # Calculate the partition index and row start/end for the current page of data
    partition_index = (partition_end_indices <= start).sum()
    row_start = start - partition_start_indices[partition_index]
    max_row_index = partition_lengths[partition_index] - 1
    row_end = min(row_start + length, max_row_index + 1)

    data = []

    # Retrieve the data from the current partition
    data.append(df.partitions[partition_index].compute().iloc[row_start:row_end].to_dict(orient='records'))

    # If there is more data to retrieve, continue with the next partition(s)
    remaining_length = length - len(data[0])
    while remaining_length > 0:
        if partition_index + 1 >= len(partition_start_indices):
            # No remaining partitions, so break out of the loop and return the data collected so far
            break

        partition_index += 1

        row_start = 0
        max_row_index = partition_lengths[partition_index] - 1

        row_end = min(remaining_length, max_row_index + 1)

        data.append(df.partitions[partition_index].compute().iloc[row_start:row_end].to_dict(orient='records'))

        remaining_length = remaining_length - len(data[-1])

    # Concatenate the data from all partitions
    data = [item for sublist in data for item in sublist]

    return data


@app.route('/risk/download', methods=["GET"])
def download_risk_csv():
    try:
        with open("../config/dask_config.json") as f:
            config = json.load(f)
            n_partitions = config["n_partitions"]
    except FileNotFoundError:
        print("File dask_config.json not found")
        n_partitions = 1
    # Delete all filed under the processed_data folder
    for f in list(os.listdir(PROCESSED_DATA_FOLDER)):
        os.remove(f'{PROCESSED_DATA_FOLDER}/{f}')
    filename = os.listdir(UPLOAD_FOLDER)[0]  # get the name of the uploaded file
    risk_dask = dd.from_pandas(session["top_res"], npartitions=n_partitions)
    # save the dask df as a csv in the server
    risk_dask.to_csv(PROCESSED_DATA_FOLDER + f"/{filename}_out.csv", index=False, single_file=True)
    return send_file(PROCESSED_DATA_FOLDER + f"/{filename}_out.csv", as_attachment=True)


@app.route('/statistics/download', methods=["GET"])
def download_statistics_csv():
    try:
        with open("../config/dask_config.json") as f:
            config = json.load(f)
            n_partitions = config["n_partitions"]
    except FileNotFoundError:
        print("File dask_config.json not found")
        n_partitions = 1
    # Delete all filed under the processed_data folder
    for f in list(os.listdir(PROCESSED_DATA_FOLDER)):
        os.remove(f'{PROCESSED_DATA_FOLDER}/{f}')
    filename = os.listdir(UPLOAD_FOLDER)[0]  # get the name of the uploaded file
    top_cols_dask = dd.from_pandas(session["top_cols"], npartitions=n_partitions)
    # save the dask df as a csv in the server
    top_cols_dask.to_csv(PROCESSED_DATA_FOLDER + f"/{filename}_out.csv", index=False, single_file=True)
    return send_file(PROCESSED_DATA_FOLDER + f"/{filename}_out.csv", as_attachment=True)


@app.route("/progress", methods=["GET"])
def get_progress():
    global progress
    return jsonify({"progress": progress})


if __name__ == '__main__':
    # create the required directories
    if not os.path.exists(UPLOAD_FOLDER):
        print(f'File \"{UPLOAD_FOLDER}\" does not exist.\nCreating...')
        os.mkdir(UPLOAD_FOLDER)
    if not os.path.exists(PROCESSED_DATA_FOLDER):
        print(f'File \"{PROCESSED_DATA_FOLDER}\" does not exist.\nCreating...')
        os.mkdir(PROCESSED_DATA_FOLDER)
    try:
        with open("../config/dask_config.json") as f:
            config = json.load(f)
            scheduler_ip = config["scheduler_ip"]
            scheduler_port = config["scheduler_port"]
    except FileNotFoundError:
        print("File dask_config.json not found")
    # cluster = LocalCluster(scheduler_port=8786)
    client = Client(scheduler_ip+":"+str(scheduler_port))
    client.upload_file("import_data.py")
    client.upload_file("auxiliary_functions.py")
    client.upload_file("prob_re_par.py")
    client.upload_file("anonymize.py")
    client.upload_file("plots.py")
    # client = Client(cluster)
    print(client)
    app.run(host="0.0.0.0", port=5000)
