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
from itertools import chain

from variables import *

def colorTable(select_colors,color_choice,column):
    colors = (ibis
              .memtable(select_colors[color_choice], columns=[column, "color"])
              .to_pandas()
             )
    return colors 




def get_summary(ca, combined_filter, column, main_group, colors=None):
    df = ca.filter(combined_filter)
    #total acres for each group 
    # if colors is not None and not colors.empty:
    group_totals = df.group_by(main_group).aggregate(total_acres=_.acres.sum())
    df = ca.filter(combined_filter)
    df = (df
            .group_by(*column)  # unpack the list for grouping
            .aggregate(percent_CA= _.acres.sum() / ca_area_acres,
                       acres = _.acres.sum(),
                       mean_richness = (_.richness * _.acres).sum() / _.acres.sum(),
                       mean_rsr = (_.rsr * _.acres).sum() / _.acres.sum(),
                       mean_irrecoverable_carbon = (_.irrecoverable_carbon * _.acres).sum() / _.acres.sum(),
                       mean_manageable_carbon = (_.manageable_carbon * _.acres).sum() / _.acres.sum(),
                       mean_fire = (_.fire *_.acres).sum()/_.acres.sum(),
                       mean_rxburn = (_.rxburn *_.acres).sum()/_.acres.sum(),
                       mean_disadvantaged =  (_.disadvantaged_communities * _.acres).sum() / _.acres.sum(),
                       mean_svi =  (_.svi * _.acres).sum() / _.acres.sum(),
                      )
            .mutate(percent_CA=_.percent_CA.round(3),
                    acres=_.acres.round(0))
         )
    # if colors is not None and not colors.empty:
    df = df.inner_join(group_totals, main_group)    
    df = df.mutate(percent_group=( _.acres / _.total_acres).round(3)) 
    if colors is not None and not colors.empty: #only the df will have colors, df_tab doesn't since we are printing it.
        df = df.inner_join(colors, column[-1]) 
    df = df.cast({col: "string" for col in column})
    df = df.to_pandas()
    return df
    

def summary_table(ca, column, select_colors, color_choice, filter_cols, filter_vals,colorby_vals): # get df for charts + df_tab for printed table
    colors = colorTable(select_colors,color_choice,column)
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
    
    only_conserved = (combined_filter) & (_.status.isin(['30x30-conserved']))
    df_percent = get_summary(ca, only_conserved, [column],column, colors) # df used for percentage, excludes non-conserved. 

    df_tab = get_summary(ca, combined_filter, filter_cols, column, colors = None) #df used for printed table

    if "non-conserved" in list(chain.from_iterable(filter_vals)):
       combined_filter = (combined_filter) | (_.status.isin(['non-conserved']))
        
    df = get_summary(ca, combined_filter, [column], column, colors) # df used for charts 

    df_bar_30x30 = None # no stacked charts if we have status/gap_code
    if column not in ["status","gap_code"]: # df for stacked 30x30 status bar chart 
        colors = colorTable(select_colors,"30x30 Status",'status')
        df_bar_30x30 = get_summary(ca, combined_filter, [column, 'status'], column, colors) # df used for charts 
    

    return df, df_tab, df_percent, df_bar_30x30



        
def summary_table_sql(ca, column, colors, ids): # get df for charts + df_tab for printed table 
    filters = [_.id.isin(ids)]
    combined_filter = reduce(lambda x, y: x & y, filters) #combining all the filters into ibis filter expression 
    df = get_summary(ca, combined_filter, [column], column, colors) # df used for charts 
    return df


def get_hex(df, color,sort_order):
    return list(df.drop_duplicates(subset=color, keep="first")
                .set_index(color)
                .reindex(sort_order)
                .dropna()["color"])

def transform_label(label, x_field):
    # converting labels for that gnarly stacked bar chart 
    if x_field == "access_type":
        return label.replace(" Access", "")
    elif x_field == "ecoregion":
        label = label.replace("Northern California", "NorCal")
        label = label.replace("Southern California", "SoCal")
        label = label.replace("Southeastern", "SE.")
        label = label.replace("Northwestern", "NW.")
        label = label.replace("and", "&")
        label = label.replace("California", "CA")
        return label
    else:
        return label

            
def stacked_bar(df, x, y, color, title, colors):
    label_colors = colors['color'].to_list()
    # bar order 
    if x == "established":  # order labels in chronological order, not alphabetic.
        sort = '-x'
    elif x == "access_type":  # order based on levels of openness 
        sort = ['Open', 'Restricted', 'No Public', "Unknown"]
    elif x == "easement":
        sort = ['True', 'False']
    elif x == "manager_type":
        sort = ["Federal", "Tribal", "State", "Special District", "County", "City", "HOA",
                "Joint", "Non Profit", "Private", "Unknown"]
    elif x == "status":
        sort = ["30x30-conserved", "other-conserved", "unknown", "non-conserved"]
    elif x == "ecoregion":
        sort = ['SE. Great Basin', 'Mojave Desert', 'Sonoran Desert', 'Sierra Nevada',
                'SoCal Mountains & Valleys', 'Mono', 'Central CA Coast', 'Klamath Mountains',
                'NorCal Coast', 'NorCal Coast Ranges', 'NW. Basin & Range', 'Colorado Desert',
                'Central Valley Coast Ranges', 'SoCal Coast', 'Sierra Nevada Foothills',
                'Southern Cascades', 'Modoc Plateau', 'Great Valley (North)',
                'NorCal Interior Coast Ranges', 'Great Valley (South)']
    else:
        sort = 'x'

    if x == "manager_type":
        angle = 270
        height = 350

    elif x == 'ecoregion':
        angle = 270
        height = 430
    else:
        angle = 0
        height = 310

    # stacked bar order
    sort_order = ['30x30-conserved', 'other-conserved', 'unknown', 'non-conserved']
    y_titles = {
        'ecoregion': 'Ecoregion (%)',
        'established': 'Year (%)',
        'manager_type': 'Manager Type (%)',
        'easement': 'Easement (%)',
        'access_type': 'Access (%)'
    }
    ytitle = y_titles.get(x, y)
    color_hex = get_hex(df[[color, 'color']], color, sort_order)
    sort_order = sort_order[0:len(color_hex)]
    df["stack_order"] = df[color].apply(lambda val: sort_order.index(val) if val in sort_order else len(sort_order))
            
    # shorten labels to fit on chart  
    label_transform = f"datum.{x}"
    if x == "access_type":
        label_transform = f"replace(datum.{x}, ' Access', '')"
    elif x == "ecoregion":
        label_transform = (
            "replace("
            "replace("
            "replace("
            "replace("
            "replace("
            "replace(datum.ecoregion, 'Northern California', 'NorCal'),"
            "'Southern California', 'SoCal'),"
            "'Southeastern', 'SE.'),"
            "'Northwestern', 'NW.'),"
            "'and', '&'),"
            "'California', 'CA')"
        )

    # to match the colors in the map to each label, need to write some ugly code..
    #  bar chart w/ xlabels hidden
    chart = alt.Chart(df).mark_bar(height = 500).transform_calculate(
        xlabel=label_transform
    ).encode(
        x=alt.X("xlabel:N", sort=sort, title=None,
                axis=alt.Axis(labelLimit=150, labelAngle=angle, labelColor="transparent")),
        y=alt.Y(y, title=ytitle, axis=alt.Axis(labelPadding=5)).scale(domain=(0, 1)),
        color=alt.Color(
            color,
            sort=sort_order,
            scale=alt.Scale(domain=sort_order, range=color_hex)
        ),
        order=alt.Order("stack_order:Q", sort="ascending"),
        tooltip=[
            alt.Tooltip(x, type="nominal"),
            alt.Tooltip(color, type="nominal"),
            alt.Tooltip("percent_group", type="quantitative", format=",.1%"),
            alt.Tooltip("acres", type="quantitative", format=",.0f"),
        ]
    )
    transformed_labels = [transform_label(str(lab), x) for lab in colors[x]]    
    labels_df = colors 
    labels_df['xlabel'] = transformed_labels
    # 2 layers, 1 for the symbol and 1 for the text
    if angle == 0:
        symbol_layer = alt.Chart(labels_df).mark_point(
            filled=True,
            shape="circle",
            size=100,
            xOffset = 0,
            yOffset=130,
            align = 'left',
            tooltip = False
        ).encode(
            x=alt.X("xlabel:N", sort=sort),
            color=alt.Color("color:N", scale=None)
        )
        text_layer = alt.Chart(labels_df).mark_text(
            dy=115,  # shifts the text to the right of the symbol
            dx = 0,
            yOffset=0, 
            xOffset = 0,
            align='center',
            color="black",
            tooltip = False
        ).encode(
            x=alt.X("xlabel:N", sort=sort),
            text=alt.Text("xlabel:N")
        )
    # vertical labels 
    elif angle == 270:
        symbol_layer = alt.Chart(labels_df).mark_point(
            xOffset = 0, 
            yOffset= 100,
            filled=True,
            shape="circle",
            size=100,
            tooltip = False
        ).encode(
            x=alt.X("xlabel:N", sort=sort),
            color=alt.Color("color:N", scale=None)
        )
        text_layer = alt.Chart(labels_df).mark_text(
            dy=0,
            dx = -110,
            angle=270,
            align='right',
            color="black",
            tooltip = False
        ).encode(
            x=alt.X("xlabel:N", sort=sort),
            text=alt.Text("xlabel:N")
        )
        
    custom_labels = alt.layer(symbol_layer, text_layer)
    final_chart = alt.layer(chart, custom_labels)

    # put it all together 
    final_chart = final_chart.properties(
        width="container",
        height=height,
        title=title
    ).configure_legend(
        direction='horizontal',
        orient='top',
        columns=3,
        title=None,
        labelOffset=2,
        offset=10,
        symbolType = 'square'
    ).configure_title(
        fontSize=18, align="center", anchor='middle', offset=10
    )
    return final_chart

def area_plot(df, column):  # Percent protected pie chart
    base = alt.Chart(df).encode(
        alt.Theta("percent_CA:Q").stack(True),
    )
    pie = (
        base
        .mark_arc(innerRadius=40, outerRadius=100, stroke="black", strokeWidth=0.5)
        .encode(
            alt.Color("color:N").scale(None).legend(None),
            tooltip=[
                alt.Tooltip(column, type="nominal"),
                alt.Tooltip("percent_CA", type="quantitative", format=",.1%"),
                alt.Tooltip("acres", type="quantitative", format=",.0f"),
            ]
        )
    )
    text = (
        base
        .mark_text(radius=80, size=14, color="white")
        .encode(text=column + ":N")
    )
    plot = pie  # pie + text
    return plot.properties(width="container", height=290)



def bar_chart(df, x, y, title): #display summary stats for color_by column 
    #axis label angles / chart size
    if x == "manager_type": #labels are too long, making vertical 
        angle = 270
        height = 373
    elif x == 'ecoregion': # make labels vertical and figure taller  
        angle = 270
        height = 430
    else: #other labels are horizontal
        angle = 0
        height = 310

    # order of bars 
    sort = 'x'
    lineBreak = ''
    if x == "established": # order labels in chronological order, not alphabetic. 
        sort = '-x'
    elif x == "access_type": #order based on levels of openness 
        sort=['Open', 'Restricted', 'No Public', "Unknown"] 
    elif x == "easement": 
        sort=['True','False'] 
    elif x == "manager_type": 
        sort = ["Federal","Tribal","State","Special District", "County", "City", "HOA","Joint","Non Profit","Private","Unknown"]
    elif x == "ecoregion": 
       sort = ['SE. Great Basin','Mojave Desert','Sonoran Desert','Sierra Nevada','SoCal Mountains & Valleys','Mono',
                'Central CA Coast','Klamath Mountains','NorCal Coast','NorCal Coast Ranges',
                'NW. Basin & Range','Colorado Desert','Central Valley Coast Ranges','SoCal Coast',
                'Sierra Nevada Foothills','Southern Cascades','Modoc Plateau','Great Valley (North)','NorCal Interior Coast Ranges',
                'Great Valley (South)']
    elif x == "status": 
        sort = ["30x30-conserved","other-conserved","unknown","non-conserved"]
        lineBreak = '-'

    # modify label names in bar chart to fit in frame
    label_transform = f"datum.{x}"  # default; no change 
    if x == "access_type":
        label_transform = f"replace(datum.{x}, ' Access', '')"  #omit 'access' from access_type 
    elif x == "ecoregion":
        label_transform = (
            "replace("
            "replace("
            "replace("
            "replace("
            "replace("
            "replace(datum.ecoregion, 'Northern California', 'NorCal'),"
            "'Southern California', 'SoCal'),"
            "'Southeastern', 'SE.'),"
            "'Northwestern', 'NW.'),"
            "'and', '&'),"
            "'California', 'CA')"
        )
    y_titles = {
        'mean_richness': 'Richness (Mean)',
        'mean_rsr': 'Range-Size Rarity (Mean)',
        'mean_irrecoverable_carbon': 'Irrecoverable Carbon (Mean)',
        'mean_manageable_carbon': 'Manageable Carbon (Mean)',
        'mean_disadvantaged': 'Disadvantaged (Mean)',
        'mean_svi': 'SVI (Mean)',
        'mean_fire': 'Fire (Mean)',
        'mean_rxburn': 'Rx Fire (Mean)'
    }
    ytitle = y_titles.get(y, y)  # Default to `y` if not in the dictionary

    x_title = next(key for key, value in select_column.items() if value == x)
    chart = alt.Chart(df).mark_bar(stroke = 'black', strokeWidth = .5).transform_calculate(
            label=label_transform
        ).encode(
        x=alt.X("label:N",
                axis=alt.Axis(labelAngle=angle, title=x_title, labelLimit = 200),
                        sort=sort), 
        y=alt.Y(y, axis=alt.Axis(title = ytitle)),
        color=alt.Color('color').scale(None),
        ).configure(lineBreak = lineBreak)
    
    chart = chart.properties(width="container", height=height, title = title
                            ).configure_title(fontSize=18, align = "center",anchor='middle')
    return chart



def sync_checkboxes(source):
    # gap 1 and gap 2 on -> 30x30-conserved on
    if source in ["gap_code1", "gap_code2"]:
        st.session_state['status30x30-conserved'] = st.session_state.gap_code1 and st.session_state.gap_code2

    # 30x30-conserved on -> gap 1 and gap 2 on
    elif source == "status30x30-conserved":
        st.session_state.gap_code1 = st.session_state['status30x30-conserved']
        st.session_state.gap_code2 = st.session_state['status30x30-conserved']

    # other-conserved on <-> gap 3 on
    elif source == "gap_code3":
        st.session_state["statusother-conserved"] = st.session_state.gap_code3
    elif source == "statusother-conserved":
        if "gap_code3" in st.session_state and st.session_state["statusother-conserved"] != st.session_state.gap_code3:
            st.session_state.gap_code3 = st.session_state["statusother-conserved"]

    # unknown on <-> gap 4 on
    elif source == "gap_code4":
        st.session_state.statusunknown = st.session_state.gap_code4

    elif source == "statusunknown":
        if "gap_code4" in st.session_state and st.session_state.statusunknown != st.session_state.gap_code4:
            st.session_state.gap_code4 = st.session_state.statusunknown

    # non-conserved on <-> gap 0 
    elif source == "gap_code0":
        st.session_state['statusnon-conserved'] = st.session_state.gap_code0

    elif source == "statusnon-conserved":
        if "gap_code0" in st.session_state and st.session_state['statusnon-conserved'] != st.session_state.gap_code0:
            st.session_state.gap_code0 = st.session_state['statusnon-conserved']


def getButtons(style_options, style_choice, default_boxes=None):
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]
    default_boxes = default_boxes or {}
    buttons = {}
    for name in opts:
        key = column + str(name)
        buttons[name] = st.checkbox(f"{name}", value=st.session_state[key], key=key, on_change = sync_checkboxes, args = (key,))
    filter_choice = [key for key, value in buttons.items() if value]
    return {column: filter_choice}
    


def getColorVals(style_options, style_choice): 
    #df_tab only includes filters selected, we need to manually add "color_by" column (if it's not already a filter). 
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]   
    d = {}
    d[column] = opts
    return d


def getLegend(style_options, color_choice):
    legend = {cat: color for cat, color in  style_options[color_choice]['stops']}
    position = 'bottom-left'
    fontsize = 15
    bg_color = 'white'
    # shorten legend for ecoregions 
    if color_choice == "Ecoregion":
        legend = {key.replace("Northern California", "NorCal"): value for key, value in legend.items()} 
        legend = {key.replace("Southern California", "SoCal"): value for key, value in legend.items()} 
        legend = {key.replace("Southeastern", "SE."): value for key, value in legend.items()} 
        legend = {key.replace("and", "&"): value for key, value in legend.items()} 
        legend = {key.replace("California", "CA"): value for key, value in legend.items()} 
        legend = {key.replace("Northwestern", "NW."): value for key, value in legend.items()} 
        bg_color = 'rgba(255, 255, 255, 0.6)'
        fontsize = 12
    return legend, position, bg_color, fontsize



def get_pmtiles_style(paint, alpha, filter_cols, filter_vals):
    filters = []
    for col, val in zip(filter_cols, filter_vals):
        filters.append(["match", ["get", col], val, True, False])
    combined_filters = ["all"] + filters
    if "non-conserved" in list(chain.from_iterable(filter_vals)):
       combined_filters = ["any", combined_filters, ["match", ["get", "status"], ["non-conserved"],True, False]]
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
                "source-layer": "ca30x30",
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
                "source-layer": "ca30x30",
                "type": "fill",
                "filter": combined_filters,
                "paint": {
                    "fill-color": paint,
                    "fill-opacity": 1,
                }
            }
        ]
    }
    return style

