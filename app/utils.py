import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import leafmap.maplibregl as leafmap
import altair as alt
import ibis
from ibis import _
import ibis.selectors as s
import os
from shapely import wkb  
from typing import Optional
from functools import reduce
from itertools import chain
import re
from variables import *


######################## UI FUNCTIONS 
def get_buttons(style_options, style_choice, default_boxes=None):
    """
    Creates Streamlit checkboxes based on style options and returns the selected filters.
    """
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]
    default_boxes = default_boxes or {}

    buttons = {}
    for name in opts:
        key = column + str(name)
        buttons[name] = st.checkbox(f"{name}", value=st.session_state[key], key=key, on_change = sync_checkboxes, args = (key,))
    filter_choice = [key for key, value in buttons.items() if value]
    return {column: filter_choice}


def sync_checkboxes(source):
    """
    Synchronizes checkbox selections in Streamlit based on 30x30 status and GAP codes. 
    """
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


def color_table(select_colors, color_choice, column):
    """
    Converts selected color mapping into a DataFrame.
    """
    return ibis.memtable(select_colors[color_choice], columns=[column, "color"]).to_pandas()

def get_color_vals(style_options, style_choice):
    """
    Extracts available color values for a selected style option.
    """
    column = style_options[style_choice]['property']
    return {column: [style[0] for style in style_options[style_choice]['stops']]}



######################## SUMMARY & DATA FUNCTIONS 
def get_summary(ca, combined_filter, column, main_group, colors = None):
    """
    Computes summary statistics for the filtered dataset.
    """
    df = ca.filter(combined_filter)    
    #total acres for each group 
    group_totals = df.group_by(main_group).aggregate(total_acres=_.acres.sum())
    df = (df.group_by(*column)
          .aggregate(percent_CA=(_.acres.sum() / ca_area_acres),
                     acres=_.acres.sum(),
                     percent_amph_richness =(_.ACE_amphibian_richness * _.acres).sum() / _.acres.sum(),
                     percent_reptile_richness=(_.ACE_reptile_richness * _.acres).sum() / _.acres.sum(),
                     percent_bird_richness=(_.ACE_bird_richness * _.acres).sum() / _.acres.sum(),
                     percent_mammal_richness=(_.ACE_mammal_richness * _.acres).sum() / _.acres.sum(),
                     percent_rare_amph_richness =(_.ACE_rare_amphibian_richness * _.acres).sum() / _.acres.sum(),
                     percent_rare_reptile_richness=(_.ACE_rare_reptile_richness * _.acres).sum() / _.acres.sum(),
                     percent_rare_bird_richness=(_.ACE_rare_bird_richness * _.acres).sum() / _.acres.sum(),
                     percent_rare_mammal_richness=(_.ACE_rare_mammal_richness * _.acres).sum() / _.acres.sum(),
                     percent_end_amph_richness =(_.ACE_endemic_amphibian_richness * _.acres).sum() / _.acres.sum(),
                     percent_end_reptile_richness=(_.ACE_endemic_reptile_richness * _.acres).sum() / _.acres.sum(),
                     percent_end_bird_richness=(_.ACE_endemic_bird_richness * _.acres).sum() / _.acres.sum(),
                     percent_end_mammal_richness=(_.ACE_endemic_mammal_richness * _.acres).sum() / _.acres.sum(),
                     percent_plant_richness=(_.plant_richness * _.acres).sum()/_.acres.sum(),
                     percent_rarityweight_endemic_plant_richness=(_.rarityweighted_endemic_plant_richness * _.acres).sum()/_.acres.sum(),
                     percent_wetlands=(_.wetlands * _.acres).sum()/_.acres.sum(),
                     percent_fire=(_.fire * _.acres).sum() / _.acres.sum(),
                     percent_farmland=(_.farmland * _.acres).sum() / _.acres.sum(),
                     percent_grazing=(_.grazing * _.acres).sum() / _.acres.sum(),
                     percent_disadvantaged=(_.DAC * _.acres).sum() / _.acres.sum(),
                     percent_low_income=(_.low_income * _.acres).sum() / _.acres.sum()
                    )
          .mutate(percent_CA=_.percent_CA.round(5), acres=_.acres.round(0))
         )
    df = df.inner_join(group_totals, main_group).mutate(percent_group=( _.acres / _.total_acres).round(3))
    if colors is not None and not colors.empty:
        df = df.inner_join(colors, column[-1])
    return df.cast({col: "string" for col in column}).execute()

def get_summary_table(ca, column, select_colors, color_choice, filter_cols, filter_vals, colorby_vals):
    """
    Generates summary tables for visualization and reporting.
    """
    colors = color_table(select_colors, color_choice, column)
    
    #if a filter is selected, add to list of filters 
    filters = [getattr(_, col).isin(vals) for col, vals in zip(filter_cols, filter_vals) if vals]
    
    #show color_by column in table by adding it as a filter (if it's not already a filter)
    if column not in filter_cols:
        filter_cols.append(column)
        filters.append(getattr(_, column).isin(colorby_vals[column]))

    #combining all the filters into ibis filter expression 
    combined_filter = reduce(lambda x, y: x & y, filters)
    only_conserved = combined_filter & (_.status.isin(['30x30-conserved']))

    # df used for percentage, excludes non-conserved. 
    df_percent = get_summary(ca, only_conserved, [column], column, colors)

    #df used for printed table
    df_tab = get_summary(ca, combined_filter, filter_cols, column, colors=None)
    if "non-conserved" in chain.from_iterable(filter_vals):
        combined_filter = combined_filter | (_.status.isin(['non-conserved']))

    # df used for charts 
    df = get_summary(ca, combined_filter, [column], column, colors)

    # df for stacked 30x30 status bar chart 
    df_bar_30x30 = None if column in ["status", "gap_code"] else get_summary(ca, combined_filter, [column, 'status'], column, color_table(select_colors, "30x30 Status", 'status'))
    return df, df_tab, df_percent, df_bar_30x30


def get_summary_table_sql(ca, column, colors, ids):
    """
    Generates a summary table using specific IDs as filters.
    """
    combined_filter = _.id.isin(ids)
    return get_summary(ca, combined_filter, [column], column, colors)


######################## MAP STYLING FUNCTIONS 
def get_pmtiles_style(paint, alpha, filter_cols, filter_vals):
    """
    Generates a MapLibre GL style for PMTiles with specified filters.
    """
    filters = [["match", ["get", col], val, True, False] for col, val in zip(filter_cols, filter_vals)]
    combined_filters = ["all", *filters]
    
    if "non-conserved" in chain.from_iterable(filter_vals):
        combined_filters = ["any", combined_filters, ["match", ["get", "status"], ["non-conserved"], True, False]]
    source_layer_name = re.sub(r'\W+', '', os.path.splitext(os.path.basename(ca_pmtiles))[0]) #stripping hyphens to get layer name 
    return {
        "version": 8,
        "sources": {"ca": {"type": "vector", "url": f"pmtiles://{ca_pmtiles}"}},
        "layers": [
            {
                "id": "ca30x30",
                "source": "ca",
                # "source-layer": "ca30x30",
                "source-layer": source_layer_name,
                "type": "fill",
                "filter": combined_filters,
                "paint": {"fill-color": paint, "fill-opacity": alpha},
            }
        ],
    }
    
def get_url(folder, file, base_folder = 'CBN'):
    """
    Get url for minio hosted data
    """
    minio = 'https://minio.carlboettiger.info/'
    bucket = 'public-ca30x30'
    if base_folder is None:
        path = os.path.join(bucket,folder,file)
    else:
        path = os.path.join(bucket,base_folder,folder,file)
    url = minio+path
    return url
    
def get_pmtiles_style_llm(paint, ids):
    """
    Generates a MapLibre GL style for PMTiles using specific IDs as filters.
    """
    source_layer_name = re.sub(r'\W+', '', os.path.splitext(os.path.basename(ca_pmtiles))[0]) #stripping hyphens to get layer name 
    return {
        "version": 8,
        "sources": {"ca": {"type": "vector", "url": f"pmtiles://{ca_pmtiles}"}},
        "layers": [
            {
                "id": "ca30x30",
                "source": "ca",
                # "source-layer": "ca30x30",
                 "source-layer": source_layer_name,
                "type": "fill",
                "filter": ["in", ["get", "id"], ["literal", ids]],
                # "filter": ["all", ["match", ["get", "id"], ids, True, False]],
                "paint": {"fill-color": paint, "fill-opacity": 1},
            }
        ],
    }    

def get_pmtiles_layer(layer,url):
    """
    Generates a MapLibre GL style for PMTiles file
    """
    return {
        "version": 8,
        "sources": {"ca": {"type": "vector", "url": f"pmtiles://{url}"}},
        "layers": [
            {
                "id": layer,
                "source": "ca",
                "source-layer": layer,
                "type": "fill",
                "paint": {"fill-color": "#702963"},
            }
        ],
    }

def get_legend(style_options, color_choice):
    """
    Generates a legend dictionary with color mapping and formatting adjustments.
    """
    legend = {cat: color for cat, color in style_options[color_choice]['stops']}
    position, fontsize, bg_color = 'bottom-left', 15, 'white'
    
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




######################## CHART FUNCTIONS 
def area_chart(df, column):
    """
    Generates an Altair pie chart representing the percentage of protected areas.
    """
    base = alt.Chart(df).encode(alt.Theta("percent_CA:Q").stack(True))
    pie = (
        base.mark_arc(innerRadius=40, outerRadius=100, stroke="black", strokeWidth=0.1)
        .encode(
            alt.Color("color:N").scale(None).legend(None),
            tooltip=[
                alt.Tooltip(column, type="nominal"),
                alt.Tooltip("percent_CA", type="quantitative", format=",.1%"),
                alt.Tooltip("acres", type="quantitative", format=",.0f"),
            ]
        )
    )
    return pie.properties(width="container", height=290)


def bar_chart(df, x, y, title):
    """Creates a simple bar chart."""
    return create_bar_chart(df, x, y, title)

def stacked_bar(df, x, y, color, title, colors):
    """Creates a stacked bar chart."""
    return create_bar_chart(df, x, y, title, color=color, stacked=True, colors=colors)


def get_chart_settings(x, y, stacked):
    """
    Returns sorting, axis settings, and y-axis title mappings.
    """
    sort_options = {
        "established": "-x",
        "access_type": ["Open", "Restricted", "No Public", "Unknown"],
        "easement": ["True", "False"],
        "manager_type": ["Federal", "Tribal", "State", "Special District", "County", "City",
                         "HOA", "Joint", "Non Profit", "Private", "Unknown"],
        "status": ["30x30-conserved", "other-conserved", "unknown", "non-conserved"],
        "ecoregion": ['SE. Great Basin', 'Mojave Desert', 'Sonoran Desert', 'Sierra Nevada',
                      'SoCal Mountains & Valleys', 'Mono', 'Central CA Coast', 'Klamath Mountains',
                      'NorCal Coast', 'NorCal Coast Ranges', 'NW. Basin & Range', 'Colorado Desert',
                      'Central Valley Coast Ranges', 'SoCal Coast', 'Sierra Nevada Foothills',
                      'Southern Cascades', 'Modoc Plateau', 'Great Valley (North)',
                      'NorCal Interior Coast Ranges', 'Great Valley (South)']
    }
    y_titles = {
            "ecoregion": "Ecoregion (%)", "established": "Year (%)",
            "manager_type": "Manager Type (%)", "easement": "Easement (%)",
            "access_type": "Access (%)", "climate_zone": "Climate Zone (%)",
            "habitat_type": "Habitat Type (%)", "resilient_connected_network": "Resilient & Connected Network (%)",
        
            # "percent_amph_richness":"Amphibian Richness (%)", "percent_reptile_richness":"Reptile Richness (%)",
            # "percent_bird_richness":"Bird Richness (%)", "percent_mammal_richness":"Mammal Richness (%)",
        
            # "percent_rare_amph_richness":"Rare Amphibian Richness (%)", "percent_rare_reptile_richness":"Rare Reptile Richness (%)",
            # "percent_rare_bird_richness":"Rare Bird Richness (%)", "percent_rare_mammal_richness":"Rare Mammal Richness (%)",
        
            # "percent_end_amph_richness":"Endemic Amphibian Richness (%)", "percent_end_reptile_richness":"Endemic Reptile Richness (%)",
            # "percent_end_bird_richness":"Endemic Bird Richness (%)", "percent_end_mammal_richness":"Endemic Mammal Richness (%)",
            
            # "percent_plant_richness":"Plant Richness (%)",
            # "percent_rarityweight_endemic_plant_richness":"Rarity-Weighted Endemic Plant Richness (%)",
            "percent_amph_richness":"Richness (%)", "percent_reptile_richness":"Richness (%)",
            "percent_bird_richness":"Richness (%)", "percent_mammal_richness":"Richness (%)",
        
            "percent_rare_amph_richness":"Richness (%)", "percent_rare_reptile_richness":"Richness (%)",
            "percent_rare_bird_richness":"Richness (%)", "percent_rare_mammal_richness":"Richness (%)",
        
            "percent_end_amph_richness":"Richness (%)", "percent_end_reptile_richness":"Richness (%)",
            "percent_end_bird_richness":"Richness (%)", "percent_end_mammal_richness":"Richness (%)",
            
            "percent_plant_richness":"Richness (%)",
            "percent_rarityweight_endemic_plant_richness":"Richness (%)",
        
            "percent_wetlands":"Wetlands (%)",
            "percent_farmland":"Farmland (%)",
            "percent_grazing":"Grazing Land (%)",
            "percent_disadvantaged":"Disadvantaged Communities (%)",
            "percent_low_income":"Low-Income Communities (%)",
            "percent_fire": "Fire (%)",

    }
    if stacked:
        y_titles = y_titles.get(x,x)
    else: 
        y_titles = y_titles.get(y,y)

    angle = 270 if x in ["manager_type", "ecoregion", "status", "habitat_type", "resilient_connected_network"] else 0
    height = 470 if y == "percent_rarityweight_endemic_plant_richness" else 250 if stacked else 400 if x == "ecoregion" else 350 if x == "manager_type" else 300

    return sort_options.get(x, "x"), angle, height, y_titles

    
def get_label_transform(x, label=None):
    """
    Returns label transformation logic for Altair expressions and manual label conversion.
    """
    transformations = {
        "access_type": ("replace(datum.access_type, ' Access', '')", lambda lbl: lbl.replace(" Access", "")),
        "ecoregion": (
            "replace(replace(replace(replace(replace("
            "replace(datum.ecoregion, 'Northern California', 'NorCal'),"
            "'Southern California', 'SoCal'),"
            "'Southeastern', 'SE.'),"
            "'Northwestern', 'NW.'),"
            "'and', '&'),"
            "'California', 'CA')",
            lambda lbl: (lbl.replace("Northern California", "NorCal")
                         .replace("Southern California", "SoCal")
                         .replace("Southeastern", "SE.")
                         .replace("Northwestern", "NW.")
                         .replace("and", "&")
                         .replace("California", "CA"))
        )
    }
    if label is not None:
        return transformations.get(x, (None, lambda lbl: lbl))[1](label)
    
    return transformations.get(x, (f"datum.{x}", None))[0]

def get_hex(df, color, order):
    """
    Returns a list of hex color codes and categories sorted based on `sort_order`.
    """
    return (df.drop_duplicates(subset=color, keep="first")
                .set_index(color)
                .reindex(order)
                .dropna()
                .reset_index()).T.values.tolist()


def create_bar_chart(df, x, y, title, color=None, stacked=False, colors=None):
    """
    Generalized function to create a bar chart, supporting both standard and stacked bars.
    """
    # helper functions 
    sort, angle, height, y_title = get_chart_settings(x, y, stacked)
    label_transform = get_label_transform(x)

    # create base chart 
    chart = (
        alt.Chart(df)
        .mark_bar(stroke="black", strokeWidth=0.1)
        .transform_calculate(xlabel=label_transform)  
        .encode(
            x=alt.X("xlabel:N", sort=sort,
                    axis=alt.Axis(labelAngle=angle, title=None, labelLimit=200)),
            y=alt.Y(y, axis=alt.Axis(title=y_title, offset = -5)),
            tooltip=[alt.Tooltip(x, type="nominal"), alt.Tooltip(y, type="quantitative")]
        )
        .properties(width="container", height=height)  

    )

    if stacked:
        # order stacks 
        order = ["30x30-conserved", "other-conserved", "unknown", "non-conserved"]
        sort_order ,color_hex = get_hex(df[[color, "color"]], color, order)

        df["stack_order"] = df[color].apply(lambda val: sort_order.index(val) if val in sort_order else len(sort_order))

        # build chart  
        chart = chart.encode(
            x=alt.X("xlabel:N", sort=sort, title=None, axis=alt.Axis(labels=False)),
            y=alt.Y(y, axis=alt.Axis(title=y_title, offset = -5),scale = alt.Scale(domain = [0,1])),

            color=alt.Color(color, sort=sort_order, scale=alt.Scale(domain=sort_order, range=color_hex)) ,
            order=alt.Order("stack_order:Q", sort="ascending"),
            tooltip=[
                alt.Tooltip(x, type="nominal"),
                alt.Tooltip(color, type="nominal"),
                alt.Tooltip("percent_group", type="quantitative", format=",.1%"),
                alt.Tooltip("acres", type="quantitative", format=",.0f"),
            ],
        )
        
        # use shorter label names (to save space)
        labels_df = colors.copy()
        labels_df["xlabel"] = [get_label_transform(x, str(lab)) for lab in colors[x]]
        
        # create symbols/label below chart; dots match map colors. 
        symbol_layer = (
            alt.Chart(labels_df)
            .mark_point(filled=True, shape="circle", size=100, tooltip=False, yOffset=5)
            .encode(
            x=alt.X("xlabel:N", sort=sort,
                    axis=alt.Axis(labelAngle=angle, title=None, labelLimit=200)),
                color=alt.Color("color:N", scale=None),
            )
            .properties(height=1, width="container")
        )

        # append symbols below base chart
        final_chart = alt.vconcat(chart, symbol_layer, spacing=8).resolve_scale(x="shared")


    else: #if not stacked, do single chart 
        final_chart = chart.encode(
            color=alt.Color("color").scale(None)
        )

    # customize chart
    final_chart = final_chart.properties(
        title=title.split("\n") if "\n" in title else title
    ).configure_legend(
        symbolStrokeWidth=0.1, direction="horizontal", orient="top",
        columns=2, title=None, labelOffset=2, offset=5,
        symbolType="square", labelFontSize=13,
    ).configure_title(
        fontSize=18, align="center", anchor="middle", offset = 10
    )

    return final_chart
