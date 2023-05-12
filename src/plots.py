import json
import dask.dataframe as dd
import plotly.express as px
import plotly
import pandas as pd
import import_data
from auxiliary_functions import ppoints


def plot_distinct_bar(unique_df):
    """
    Implement the bar plot with the number of distinct values as a proportion of the number of observations
    on the "Data Upload & Processing" tab
    """
    fig = px.bar(unique_df.sort_values("distinct"), x="distinct", y="column",
                 title="Number of distinct values<br>as a proportion of the number of observations",
                 orientation="h")
    fig.update_layout(height=850, title_x=0.22,
                      title_font_family="Arial",
                      yaxis_title="Column",
                      xaxis_title=None,
                      xaxis={'range': [-0.05, 1.05]},
                      bargap=0.05,
                      plot_bgcolor="#eeeeee")
    fig.update_traces(marker_line_width=0.5, marker_line_color="white", marker_color="steelblue")
    fig.update_xaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def plot_hist(res, alpha, filename, num_of_rows, num_of_cols, size_of_tuple, num_of_combination, u):
    """
    Implement the first histogram plot on the "Re-Identification Risk" tab
    """
    fig = px.histogram(res, x="risk", nbins=50,
                       title=f"Histogram of the re-identification risks associated with each combination of variables"
                             f"<br>File: {filename}, L={num_of_rows} observations, N={num_of_cols} variables, "
                             f"p={size_of_tuple}, number of combinations={num_of_combination}")
    fig.update_layout(title_font_family="Arial",
                      xaxis_title="Re-identification risk",
                      yaxis_title="Number of combinations",
                      bargap=0.05,
                      plot_bgcolor="#eeeeee")
    fig.update_traces(marker_line_width=0.5, marker_line_color="white", marker_color="steelblue")
    fig.update_xaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    fig.add_vline(x=u, line_width=1, line_dash="dash", line_color="red",
                  annotation_text=f"Threshold: {round(1 - alpha, 2)}",
                  annotation_position="top left", annotation_bgcolor="white", annotation_bordercolor="#eeeeee",
                  annotation_font_size=15, annotation_font_color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def plot_extremes_hist(res, alpha, filename, num_of_riskiest_combination):
    """
    Implement the second histogram plot on the "Re-Identification Risk" tab
    """
    fig = px.histogram(res, x='risk', nbins=50,
                       title=f"Histogram of the re-identification risks associated with each combination of variables"
                             f"<br>File: {filename}, number of {alpha}% riskiest combinations = "
                             f"{num_of_riskiest_combination}")
    fig.update_layout(title_font_family="Arial",
                      xaxis_title="Re-identification risk",
                      yaxis_title="Number of combinations",
                      bargap=0.05,
                      plot_bgcolor="#eeeeee")
    fig.update_traces(marker_line_width=0.5, marker_line_color="white", marker_color="steelblue")
    fig.update_xaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def plot_steps(qar_df):
    fig = px.line(qar_df, x='id2', y='QaR',
                  title=f'Change of re-identification risk by backward elimination of the riskiest variables'
                        f"<br>by dropping the riskiest variable at each step")
    fig.update_layout(title_font_family="Arial",
                      xaxis_title="Step",
                      xaxis={'range': [-0.0, 11.5]},
                      yaxis_title="Re-identification risk",
                      plot_bgcolor="#eeeeee")
    fig.add_scatter(x=qar_df.id2, y=qar_df.QaR, mode="markers+text", text=qar_df.id,
                    marker=dict(symbol="square", size=17))

    fig.update_traces(marker_line_width=0.5, marker_line_color="black", marker_color="white",
                      line_color='#4682b4', line_width=3, showlegend=False)
    fig.update_xaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', dtick=1, color="black", )
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def plot_steps_entr(qar_df):
    fig = px.line(qar_df, x='Mean_entropy', y='QaR',
                  title=f'Change of re-identification risk and of mean entropy'
                        f' by backward elimination of the riskiest variables'
                        f"<br>'by dropping the riskiest variable at each step'")
    fig.update_layout(title_font_family="Arial",
                      xaxis_title="Mean entropy",
                      yaxis_title="Re-identification risk",
                      plot_bgcolor="#eeeeee")
    fig.add_scatter(x=qar_df.Mean_entropy, y=qar_df.QaR, mode="markers+text", text=qar_df.id,
                    marker=dict(symbol="square", size=17))

    fig.update_traces(marker_line_width=0.5, marker_line_color="black", marker_color="white",
                      line_color='#4682b4', line_width=3, showlegend=False)
    fig.update_xaxes(autorange="reversed", fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', dtick=0.5,
                     color="black", )
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', dtick=0.2, color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def plot_GPD_fit(x, alpha, res, v1=0.99, v2=0.999):
    ex = res[2]
    y = ppoints(1000)
    z = res[3]
    df = pd.DataFrame({'Empirical CDF': ex})

    fig = px.ecdf(df)
    fig.update_traces(line_color="black", line_width=0.7)
    fig.add_scatter(x=z, y=y, mode="lines", line=dict(color="red", width=2), name="Theoretical CDF")
    fig.update_layout(title="Empirical and theoretical cumulative probabilities - Generalised Pareto Distribution",
                      xaxis_title="Re-identification risk",
                      yaxis_title="Cumulative probability",
                      plot_bgcolor="#eeeeee")
    fig.update_traces(showlegend=False)
    fig.update_xaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black", )
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', dtick=0.25, color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def plot_POT_logit(x, alpha, res, v1=0.99, v2=0.999):
    xhat1 = res[9]
    xhat2 = res[10]

    df = pd.DataFrame({'xx': x})

    fig = px.ecdf(df)
    fig.update_traces(line_color="black", line_width=0.7)

    fig.add_shape(type='line', x0=xhat1, y0=0, x1=xhat1, y1=v1, line=dict(color='#104e8b', width=1.5))
    fig.add_shape(type='line', x0=xhat1, y0=v1, x1=0, y1=v1, line=dict(color='#104e8b', width=1.5))
    fig.add_shape(type='line', x0=xhat2, y0=0, x1=xhat2, y1=v2, line=dict(color='forestgreen', width=1.5))
    fig.add_shape(type='line', x0=xhat2, y0=v2, x1=0, y1=v2, line=dict(color='forestgreen', width=1.5))
    fig.add_annotation(x=0, xanchor='left', y=0.8, text=f"<b>id_99% = {round(xhat1, 4)}<b>", showarrow=False,
                       font=dict(size=11, color="#104e8b"))
    fig.add_annotation(x=0, xanchor='left', y=0.75, text=f"<b>id_99.9% = {round(xhat2, 4)}</b>", showarrow=False,
                       font=dict(size=11, color="forestgreen"))
    fig.update_layout(title="Observed re-identification risk and estimated QaR",
                      xaxis_title="Observed re-identification risk",
                      yaxis_title="Cumulative probability",
                      plot_bgcolor="#eeeeee")
    fig.update_traces(showlegend=False)
    fig.update_xaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', color="black", )
    fig.update_yaxes(fixedrange=True, showgrid=True, gridwidth=1.5, ticks='outside', dtick=0.25, color="black")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

