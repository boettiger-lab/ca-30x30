import streamlit as st
import streamlit.components.v1 as components
import base64
import leafmap.maplibregl as leafmap
import altair as alt
import ibis
from ibis import _
import ibis.selectors as s
import os
import pandas as pd 
import geopandas as gpd
from shapely import wkb  
import sqlalchemy
import pathlib
from typing import Optional
from functools import reduce

from variables import *

def get_summary(ca, combined_filter, column, colors=None): #summary stats, based on filtered data 
    df = ca.filter(combined_filter)
    df = (df
            .group_by(*column)  # unpack the list for grouping
            .aggregate(percent_protected=100 * _.acres.sum() / ca_area_acres,
                       mean_richness = (_.richness * _.acres).sum() / _.acres.sum(),
                       mean_rsr = (_.rsr * _.acres).sum() / _.acres.sum(),
                       mean_irrecoverable_carbon = (_.irrecoverable_carbon * _.acres).sum() / _.acres.sum(),
                       mean_manageable_carbon = (_.manageable_carbon * _.acres).sum() / _.acres.sum(),
                       mean_fire = (_.fire *_.acres).sum()/_.acres.sum(),
                       mean_rxburn = (_.rxburn *_.acres).sum()/_.acres.sum(),
                       mean_disadvantaged_communities =  (_.disadvantaged_communities * _.acres).sum() / _.acres.sum(),
                       mean_svi =  (_.svi * _.acres).sum() / _.acres.sum(),
                      )
            .mutate(percent_protected=_.percent_protected.round(1))
         )
    if colors is not None and not colors.empty: #only the df will have colors, df_tab doesn't since we are printing it.
        df = df.inner_join(colors, column) 
    df = df.cast({col: "string" for col in column})
    df = df.to_pandas()
    return df


def summary_table(ca, column, colors, filter_cols, filter_vals,colorby_vals): # get df for charts + df_tab for printed table
    filters = [] 
    if filter_cols and filter_vals: #if a filter is selected, add to list of filters 
        for filter_col, filter_val in zip(filter_cols, filter_vals):
            if len(filter_val) > 1:
                filters.append(getattr(_, filter_col).isin(filter_val))
            else:
                filters.append(getattr(_, filter_col) == filter_val[0])
    if column not in filter_cols: #show color_by column in table by adding it as a filter (if it's not already a filter)
        filter_cols.append(column)
        filters.append(getattr(_, column).isin(colorby_vals[column])) 
    combined_filter = reduce(lambda x, y: x & y, filters) #combining all the filters into ibis filter expression 
    if column == "status":
        combined_filter = (combined_filter) | (_.status.isin(['30x30-conserved','other-conserved','non-conserved']))
    df = get_summary(ca, combined_filter, [column], colors) # df used for charts 
    df_tab = get_summary(ca, combined_filter, filter_cols, colors = None) #df used for printed table
    return df, df_tab 



def area_plot(df, column): #percent protected pie chart 
    base = alt.Chart(df).encode(
        alt.Theta("percent_protected:Q").stack(True),
    )
    pie = ( base
           .mark_arc(innerRadius= 40, outerRadius=100)
           .encode(alt.Color("color:N").scale(None).legend(None),
                   tooltip=['percent_protected', column])
    )
    text = ( base
            .mark_text(radius=80, size=14, color="white")
            .encode(text = column + ":N")
    )
    plot = pie # pie + text
    return plot.properties(width="container", height=290)


def bar_chart(df, x, y, title): #display summary stats for color_by column 

    #axis label angles / chart size
    if x in ["manager_type", 'ecoregion','status']: #labels are too long, making vertical 
        angle = 270
        height = 373
        if x == 'ecoregion':
            height = 430

    else: #other labels are horizontal
        angle = 0
        height = 310

    # order of bars 
    if x == "established": # order labels in chronological order, not alphabetic. 
        sort = '-x'
    elif x == "access_type": #order based on levels of openness 
        sort=['Open', 'Restricted', 'No Public', "Unknown"] 
    elif x == "manager_type": 
        sort = ["Federal","Tribal","State","Special District", "County", "City", "HOA","Joint","Non Profit","Private","Unknown"]
    else: 
        sort = 'x'

    x_title = next(key for key, value in select_column.items() if value == x)
    chart = alt.Chart(df).mark_bar().transform_calculate(
        access_label=f"replace(datum.{x}, ' Access', '')"  #omit access from access_type labels so it fits in frame
        ).encode(
        x=alt.X("access_label:N",
                axis=alt.Axis(labelAngle=angle, title=x_title, labelLimit = 200),
                        sort=sort),  
        y=alt.Y(y, axis=alt.Axis()), 
        color=alt.Color('color').scale(None)
        ).properties(width="container", height=height, title = title
        )
    # sizing for poster 
    # ).configure_title(
    # fontSize=40  
    # ).configure_axis(
    # labelFontSize=24,  
    # titleFontSize=34   
    # )
    return chart



def getButtons(style_options, style_choice, default_gap=None): #finding the buttons selected to use as filters 
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]   
    default_gap = default_gap or {}  
    buttons = {
        name: st.checkbox(f"{name}", value=default_gap.get(name, True), key=column + str(name))
        for name in opts
    }
    filter_choice = [key for key, value in buttons.items() if value]  # return only selected
    d = {}
    d[column] = filter_choice
    return d



def getColorVals(style_options, style_choice): 
    #df_tab only includes filters selected, we need to manually add "color_by" column (if it's not already a filter). 
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]   
    d = {}
    d[column] = opts
    return d



def fire_style(layer):
    return {"version": 8,
    "sources": {
        "source1": {
            "type": "vector",
            "url": "pmtiles://" + url_calfire,
            "attribution": "CAL FIRE"
        }
    },
    "layers": [
        {
            "id": "fire",
            "source": "source1",
            "source-layer": layer,
            "type": "fill",
            "paint": {
                "fill-color": "#D22B2B",
            }
        }
    ]
}
def rx_style(layer):
    return{
    "version": 8,
    "sources": {
        "source2": {
            "type": "vector",
            "url": "pmtiles://" + url_rxburn,
            "attribution": "CAL FIRE"
        }
    },
    "layers": [
        {
            "id": "fire",
            "source": "source2",
            "source-layer": layer,
            # "filter": [">=", ["get", "YEAR_"], year],
            "type": "fill",
            "paint": {
                "fill-color": "#702963",
            }
        }
    ]
}

def get_sv_style(column):
    return {
        "layers": [
            {
                "id": "SVI",
                "source": column, #need different "source" for multiple pmtiles layers w/ same file 
                "source-layer": "SVI2020_US_county",
                "filter": ["match", ["get", "STATE"], "California", True, False],
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "interpolate", ["linear"], ["get", column],
                        0, white,
                        1, svi_color
                    ]
                }
            }
        ]
    }


def get_pmtiles_style(paint, alpha, filter_cols, filter_vals):
    filters = []
    for col, val in zip(filter_cols, filter_vals):
        filters.append(["match", ["get", col], val, True, False])
    combined_filters = ["all"] + filters
    if paint['property'] == "status": #show non-conserved and other-conserved areas 
        conserved = ['match', ['get', 'status'], ['30x30-conserved', 'other-conserved', 'non-conserved'], True, False]
        combined_filters = ['any']+ [combined_filters] + [conserved]
    style = {
        "version": 8,
        "sources": {
            "ca": {
                "type": "vector",
                "url": "pmtiles://" + ca_pmtiles,
            }
        },
        "layers": [
            {
                "id": "ca30x30",
                "source": "ca",
                "source-layer": "ca_30x30_stats",
                "type": "fill",
                "filter": combined_filters,
                "paint": {
                    "fill-color": paint,
                    "fill-opacity": alpha
                }
            }
        ]
    }
    return style

def get_pmtiles_style_llm(paint, ids):
    combined_filters = ["all", ["match", ["get", "id"], ids, True, False]]
    style = {
        "version": 8,
        "sources": {
            "ca": {
                "type": "vector",
                "url": "pmtiles://" + ca_pmtiles,
            }
        },
        "layers": [
            {
                "id": "ca30x30",
                "source": "ca",
                "source-layer": "ca_30x30_stats",
                "type": "fill",
                "filter": combined_filters,
                "paint": {
                    "fill-color": paint,
                    "fill-opacity": 1,
                    # "fill-extrusion-height": 1000
                }
            }
        ]
    }
    return style
